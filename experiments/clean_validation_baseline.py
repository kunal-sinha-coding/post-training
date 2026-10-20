"""Train and evaluate a leakage safe When2Call baseline on a deterministic development split.

The flow loads only the training preference split, infers labels from responses, assigns stable
train and development partitions, trains a Jina classifier, evaluates both partitions, and saves
metrics and the checkpoint without loading the official test split.
"""
from __future__ import annotations

import argparse
import json
import random
from collections import Counter
from pathlib import Path

import torch
from datasets import load_dataset

from experiments.train_when2call_jina import (
    DATASET_NAME,
    LABELS,
    JinaSequenceClassifier,
    autocast_context,
    batch_metrics,
    collate,
    infer_action_label,
    prepare_train_examples,
    tokenize_examples,
)
from transformers import AutoConfig, AutoModel, AutoTokenizer


def load_training_rows() -> object:
    """Load the cached train preference arrow file without contacting the test split."""
    # Prefer the repository cache because the public dataset currently exposes only default metadata remotely.
    cache_path = Path("/workspace/.cache/huggingface/datasets/nvidia___when2_call/train_pref/0.0.0/0582f7749df63a96fdc3070932e83e72396ace53/when2_call-train.arrow")
    if cache_path.exists():
        from datasets import Dataset
        return Dataset.from_file(str(cache_path))
    return load_dataset(DATASET_NAME, "train_pref", split="train")


def split_examples(examples: list, dev_fraction: float, seed: int) -> tuple[list, list]:
    """Create a deterministic stratified development split from inferred training labels."""
    # Group records by inferred label so the development set contains every observed class.
    grouped = {label: [] for label in range(len(LABELS))}
    for example in examples:
        grouped[example.label].append(example)
    rng = random.Random(seed)
    train, development = [], []
    for label, items in grouped.items():
        rng.shuffle(items)
        count = max(1, round(len(items) * dev_fraction)) if items else 0
        development.extend(items[:count])
        train.extend(items[count:])
    rng.shuffle(train)
    rng.shuffle(development)
    return train, development


def load_model(device: torch.device) -> tuple[torch.nn.Module, object]:
    """Load the cached local Jina encoder with a fresh four class head."""
    # Recreate the compact encoder from the complete local checkpoint under the two billion parameter limit.
    checkpoint = Path("outputs/when2call-jina-v2-small/latest")
    tokenizer = AutoTokenizer.from_pretrained(checkpoint, trust_remote_code=True)
    tokenizer.model_max_length = 8192
    config = AutoConfig.from_pretrained(checkpoint / "encoder_config.json", trust_remote_code=True)
    config._name_or_path = str(checkpoint.resolve())
    config.attn_implementation = "torch"
    encoder = AutoModel.from_config(config, trust_remote_code=True)
    model = JinaSequenceClassifier(encoder, len(LABELS)).to(device)
    prior_state = torch.load(checkpoint / "model_state.pt", map_location="cpu")
    model.encoder.load_state_dict({key.removeprefix("encoder."): value for key, value in prior_state.items() if key.startswith("encoder.")})
    return model, tokenizer


def train_epoch(model: torch.nn.Module, tokenizer: object, examples: list, device: torch.device, optimizer: object) -> float:
    """Run one deterministic full batch training epoch and return mean loss."""
    # Shuffle only the training partition and use small batches for the available GPU memory.
    model.train()
    order = list(examples)
    random.Random(20261020).shuffle(order)
    losses = []
    for start in range(0, len(order), 8):
        batch = collate(order[start:start + 8], tokenizer)
        labels = batch.pop("labels").to(device)
        batch.pop("rejected_labels")
        batch.pop("source_ids")
        inputs = {key: value.to(device) for key, value in batch.items()}
        optimizer.zero_grad(set_to_none=True)
        with autocast_context(device):
            loss = torch.nn.functional.cross_entropy(model(**inputs).logits, labels)
        loss.backward()
        optimizer.step()
        losses.append(float(loss.detach().cpu()))
    return sum(losses) / max(1, len(losses))


def main() -> int:
    """Run the clean baseline audit and persist reproducible artifacts."""
    # Parse only local output settings and keep the dataset split fixed in code and metadata.
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/clean-validation-baseline"))
    args = parser.parse_args()
    seed = 20261020
    random.seed(seed)
    torch.manual_seed(seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # Load train_pref only and infer labels from response text without loading official labels.
    rows = load_training_rows()
    examples = prepare_train_examples(rows)
    train, development = split_examples(examples, 0.2, seed)
    tokenizer_model, tokenizer = load_model(device)
    tokenize_examples(train, tokenizer)
    tokenize_examples(development, tokenizer)

    # Train one compact baseline epoch and evaluate only the held out development partition.
    optimizer = torch.optim.AdamW(tokenizer_model.parameters(), lr=5e-5)
    loss = train_epoch(tokenizer_model, tokenizer, train, device, optimizer)
    train_metrics = batch_metrics(tokenizer_model, tokenizer, train, device, list(range(len(LABELS))))
    dev_metrics = batch_metrics(tokenizer_model, tokenizer, development, device, list(range(len(LABELS))))

    # Save metrics, split provenance, and model weights for later comparisons.
    args.output_dir.mkdir(parents=True, exist_ok=True)
    tokenizer_model.save_pretrained(args.output_dir)
    metadata = {
        "dataset": DATASET_NAME,
        "source_split": "train_pref",
        "official_test_loaded": False,
        "label_source": "inferred from chosen response content",
        "seed": seed,
        "dev_fraction": 0.2,
        "train_examples": len(train),
        "development_examples": len(development),
        "train_label_counts": dict(Counter(LABELS[item.label] for item in train)),
        "development_label_counts": dict(Counter(LABELS[item.label] for item in development)),
        "loss": loss,
        "train_metrics": train_metrics,
        "development_metrics": dev_metrics,
        "model": "jinaai/jina-embeddings-v2-small-en",
        "device": str(device),
    }
    (args.output_dir / "metrics.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"train": train_metrics, "development": dev_metrics, "loss": loss}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
