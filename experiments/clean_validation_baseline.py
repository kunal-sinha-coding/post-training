"""Train and evaluate a leakage safe When2Call baseline on a deterministic development split.

The flow loads only the training preference split, infers labels from responses, assigns stable
train and development partitions, trains a Jina classifier, evaluates both partitions, and saves
metrics and the checkpoint without loading the official test split.
"""
from __future__ import annotations

import argparse
import atexit
import json
import os
import random
import re
from collections import Counter
from pathlib import Path

import torch
from datasets import load_dataset

from experiments.train_when2call_jina import (
    DATASET_NAME,
    LABEL_TO_ID,
    LABELS,
    Example,
    JinaSequenceClassifier,
    autocast_context,
    batch_metrics,
    collate,
    response_label,
    prepare_train_examples,
    tokenize_examples,
    tools_text,
)
import experiments.train_when2call_jina as jina_training
from transformers import AutoConfig, AutoModel, AutoTokenizer
from experiments.apply_when2call_candidate_validity import required_fields


def load_training_rows() -> object:
    """Load the cached train preference arrow file without contacting the test split."""
    # Prefer the repository cache because the public dataset currently exposes only default metadata remotely.
    cache_path = Path("/workspace/.cache/huggingface/datasets/nvidia___when2_call/train_pref/0.0.0/0582f7749df63a96fdc3070932e83e72396ace53/when2_call-train.arrow")
    if cache_path.exists():
        from datasets import Dataset
        return Dataset.from_file(str(cache_path))
    return load_dataset(DATASET_NAME, "train_pref", split="train")


def load_sft_training_rows() -> object:
    """Load the cached supervised fine tuning arrow file without contacting the test split."""
    # Prefer the immutable local SFT cache so auxiliary training never depends on test metadata.
    cache_path = Path("/workspace/.cache/huggingface/datasets/nvidia___when2_call/train_sft/0.0.0/0582f7749df63a96fdc3070932e83e72396ace53/when2_call-train.arrow")
    if cache_path.exists():
        from datasets import Dataset
        return Dataset.from_file(str(cache_path))
    return load_dataset(DATASET_NAME, "train_sft", split="train")


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


def remove_tool_schemas(examples: list) -> list:
    """Replace each tool schema with a stable absence marker while preserving the question."""
    # Keep the input length and prompt boundary comparable while removing schema identity cues.
    for example in examples:
        question = example.text.split("\nAvailable tools:", 1)[0]
        example.text = question + "\nAvailable tools:\nNo tools are available."
    return examples


def compact_tool_schemas(examples: list) -> list:
    """Keep tool names and required fields while removing verbose schema details."""
    # Preserve action-relevant structure while reducing reliance on long tool descriptions.
    for example in examples:
        parts = example.text.split("\nAvailable tools:\n", 1)
        if len(parts) != 2:
            continue
        compact = []
        for line in parts[1].splitlines():
            try:
                schema = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(schema, dict) and isinstance(schema.get("name"), str):
                compact.append(json.dumps({"name": schema["name"], "required": required_fields(schema)}, separators=(",", ":")))
        example.text = parts[0] + "\nAvailable tools:\n" + "\n".join(compact)
    return examples


def add_argument_cues(examples: list) -> list:
    """Append explicit required argument names extracted from each available tool schema."""
    # Give the encoder a short structured cue for completeness without removing any original schema text.
    for example in examples:
        parts = example.text.split("\nAvailable tools:\n", 1)
        if len(parts) != 2:
            continue
        names = []
        for line in parts[1].splitlines():
            try:
                schema = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(schema, dict) and isinstance(schema.get("name"), str):
                fields = required_fields(schema)
                names.append(schema["name"] + "(" + ",".join(fields) + ")")
        example.text = example.text + "\nRequired argument names: " + ("; ".join(names) if names else "none")
    return examples


def prepare_rejected_examples(rows: object) -> list[Example]:
    """Create training-only examples labeled from rejected response content."""
    # Reuse the same question and tool context while testing whether rejected labels repair direct-class sparsity.
    examples = []
    for index, row in enumerate(rows):
        user_text = "\n".join(message["content"] for message in row["messages"] if message["role"] == "user")
        label = LABEL_TO_ID[response_label(row["rejected_response"]["content"])]
        text = f"Question: {user_text}\nAvailable tools:\n{tools_text(row['tools'])}"
        examples.append(Example(text, label, f"rejected-{index}"))
    return examples


def load_model(device: torch.device, max_length: int) -> tuple[torch.nn.Module, object]:
    """Load the cached local Jina encoder with a fresh four class head."""
    # Recreate the compact encoder from the complete local checkpoint under the two billion parameter limit.
    checkpoint = Path("outputs/when2call-jina-v2-small/latest")
    tokenizer = AutoTokenizer.from_pretrained(checkpoint, trust_remote_code=True)
    tokenizer.model_max_length = max_length
    # Load the saved JSON directly because the artifact uses encoder_config.json instead of config.json.
    # Reconstruct the architecture from the saved model type and configuration fields.
    config_data = json.loads((checkpoint / "encoder_config.json").read_text(encoding="utf-8"))
    config_data.pop("attn_implementation", None)
    config = AutoConfig.for_model(config_data.pop("model_type"), **config_data)
    config._name_or_path = str(checkpoint.resolve())
    # Use the supported local attention implementation for the cached Jina configuration.
    config.attn_implementation = "eager"
    encoder = AutoModel.from_config(config, trust_remote_code=True)
    model = JinaSequenceClassifier(encoder, len(LABELS)).to(device)
    prior_state = torch.load(checkpoint / "model_state.pt", map_location="cpu")
    model.encoder.load_state_dict({key.removeprefix("encoder."): value for key, value in prior_state.items() if key.startswith("encoder.")})
    return model, tokenizer


def train_epoch(model: torch.nn.Module, tokenizer: object, examples: list, device: torch.device, optimizer: object, loss_function: str, seed: int, label_smoothing: float = 0.0, batch_size: int = 8) -> float:
    """Run one deterministic full batch training epoch and return mean loss."""
    # Shuffle only the training partition and use small batches for the available GPU memory.
    model.train()
    order = list(examples)
    random.Random(seed).shuffle(order)
    losses = []
    for start in range(0, len(order), batch_size):
        batch = collate(order[start:start + batch_size], tokenizer)
        labels = batch.pop("labels").to(device)
        rejected_labels = batch.pop("rejected_labels").to(device)
        batch.pop("source_ids")
        inputs = {key: value.to(device) for key, value in batch.items()}
        optimizer.zero_grad(set_to_none=True)
        with autocast_context(device):
            logits = model(**inputs).logits
            if loss_function == "pairwise_ranking":
                informative = (rejected_labels >= 0) & (labels != rejected_labels)
                if not informative.any():
                    continue
                rows = torch.arange(len(labels), device=device)[informative]
                loss = torch.nn.functional.softplus(-(logits[rows, labels[informative]] - logits[rows, rejected_labels[informative]])).mean()
            else:
                loss = torch.nn.functional.cross_entropy(logits, labels, label_smoothing=label_smoothing)
        loss.backward()
        optimizer.step()
        losses.append(float(loss.detach().cpu()))
    return sum(losses) / max(1, len(losses))


def main() -> int:
    """Run the clean baseline audit and persist reproducible artifacts."""
    # Parse only local output settings and keep the dataset split fixed in code and metadata.
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/clean-validation-baseline"))
    parser.add_argument("--loss-function", choices=("cross_entropy", "pairwise_ranking"), default="cross_entropy")
    parser.add_argument("--sft-loss-function", choices=("cross_entropy", "pairwise_ranking"), default="cross_entropy")
    parser.add_argument("--omit-tool-schemas", action="store_true")
    parser.add_argument("--compact-tool-schemas", action="store_true")
    parser.add_argument("--add-argument-cues", action="store_true")
    parser.add_argument("--seed", type=int, default=20261020)
    parser.add_argument("--split-seed", type=int, default=None)
    parser.add_argument("--max-length", type=int, default=8192)
    parser.add_argument("--include-rejected-examples", action="store_true")
    parser.add_argument("--rejected-direct-samples", type=int, default=0)
    parser.add_argument("--sft-aux-samples-per-class", type=int, default=0)
    parser.add_argument("--sft-pretrain-epochs", type=int, default=0)
    parser.add_argument("--pref-train-epochs", type=int, default=1)
    parser.add_argument("--label-smoothing", type=float, default=0.0)
    parser.add_argument("--learning-rate", type=float, default=5e-5)
    parser.add_argument("--weight-decay", type=float, default=0.01)
    parser.add_argument("--train-all", action="store_true")
    args = parser.parse_args()
    # Open a W&B run before loading data so failures and completed metrics are both tracked.
    import wandb

    if not os.getenv("WANDB_API_KEY"):
        raise RuntimeError("WANDB_API_KEY is required for clean validation experiments.")
    run = wandb.init(
        project=os.getenv("WANDB_PROJECT", "when2call-research"),
        entity=os.getenv("WANDB_ENTITY"),
        name=f"clean-validation-seed{args.seed}-split{args.split_seed or args.seed}-len{args.max_length}",
        job_type="clean-validation",
        config=vars(args),
    )
    atexit.register(run.finish)
    seed = args.seed
    random.seed(seed)
    torch.manual_seed(seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # Load train_pref only and infer labels from response text without loading official labels.
    rows = load_training_rows()
    examples = prepare_train_examples(rows)
    split_seed = seed if args.split_seed is None else args.split_seed
    train, development = split_examples(examples, 0.2, split_seed)
    # Use every labeled train_pref example when producing a frozen black-box test candidate.
    if args.train_all:
        train, development = examples, []
    # Add rejected-response supervision only to training after the development split is frozen.
    if args.include_rejected_examples:
        train.extend(prepare_rejected_examples(rows))
    # Add only a bounded direct subset when testing targeted label repair.
    if args.rejected_direct_samples > 0:
        rejected_direct = [item for item in prepare_rejected_examples(rows) if item.label == LABEL_TO_ID["direct"]]
        random.Random(seed).shuffle(rejected_direct)
        train.extend(rejected_direct[:args.rejected_direct_samples])
    # Add a bounded equal-count SFT sample only for labels present in that source.
    if args.sft_aux_samples_per_class > 0:
        sft_examples = prepare_train_examples(load_sft_training_rows())
        sft_by_label = {label: [] for label in range(len(LABELS))}
        for item in sft_examples:
            sft_by_label[item.label].append(item)
        for label in (LABEL_TO_ID["cannot_answer"], LABEL_TO_ID["request_for_info"], LABEL_TO_ID["direct"]):
            selected = list(sft_by_label[label])
            random.Random(seed + label).shuffle(selected)
            train.extend(selected[:args.sft_aux_samples_per_class])
    if args.omit_tool_schemas:
        remove_tool_schemas(train)
        remove_tool_schemas(development)
    if args.compact_tool_schemas:
        compact_tool_schemas(train)
        compact_tool_schemas(development)
    if args.add_argument_cues:
        add_argument_cues(train)
        add_argument_cues(development)
    # Use the selected context limit in both token validation and model padding.
    jina_training.MAX_LENGTH = args.max_length
    tokenizer_model, tokenizer = load_model(device, args.max_length)
    # Run optional SFT-context adaptation before the labeled preference objective.
    sft_pretrain_losses = []
    if args.sft_pretrain_epochs > 0:
        sft_pretrain = prepare_train_examples(load_sft_training_rows())
        if args.omit_tool_schemas:
            remove_tool_schemas(sft_pretrain)
        if args.compact_tool_schemas:
            compact_tool_schemas(sft_pretrain)
        if args.add_argument_cues:
            add_argument_cues(sft_pretrain)
        tokenize_examples(sft_pretrain, tokenizer)
        optimizer = torch.optim.AdamW(tokenizer_model.parameters(), lr=args.learning_rate, weight_decay=args.weight_decay)
        for epoch in range(args.sft_pretrain_epochs):
            sft_pretrain_losses.append(train_epoch(tokenizer_model, tokenizer, sft_pretrain, device, optimizer, args.sft_loss_function, seed + epoch, args.label_smoothing))
    tokenize_examples(train, tokenizer)
    tokenize_examples(development, tokenizer)

    # Train the selected number of compact preference epochs and evaluate only the held out development partition.
    optimizer = torch.optim.AdamW(tokenizer_model.parameters(), lr=args.learning_rate, weight_decay=args.weight_decay)
    preference_losses = []
    for epoch in range(args.pref_train_epochs):
        preference_losses.append(train_epoch(tokenizer_model, tokenizer, train, device, optimizer, args.loss_function, seed + args.sft_pretrain_epochs + epoch, args.label_smoothing))
    loss = sum(preference_losses) / max(1, len(preference_losses))
    train_metrics = batch_metrics(tokenizer_model, tokenizer, train, device, list(range(len(LABELS))))
    dev_metrics = batch_metrics(tokenizer_model, tokenizer, development, device, list(range(len(LABELS))) if development else []) if development else None

    # Save metrics, split provenance, and model weights for later comparisons.
    args.output_dir.mkdir(parents=True, exist_ok=True)
    tokenizer_model.save_pretrained(args.output_dir)
    metadata = {
        "dataset": DATASET_NAME,
        "source_split": "train_pref",
        "official_test_loaded": False,
        "label_source": "inferred from chosen response content",
        "seed": seed,
        "split_seed": split_seed,
        "dev_fraction": 0.2,
        "train_examples": len(train),
        "development_examples": len(development),
        "train_label_counts": dict(Counter(LABELS[item.label] for item in train)),
        "development_label_counts": dict(Counter(LABELS[item.label] for item in development)),
        "loss": loss,
        "sft_pretrain_losses": sft_pretrain_losses,
        "preference_losses": preference_losses,
        "train_metrics": train_metrics,
        "development_metrics": dev_metrics,
        "model": "jinaai/jina-embeddings-v2-small-en",
        "loss_function": args.loss_function,
        "sft_loss_function": args.sft_loss_function,
        "omit_tool_schemas": args.omit_tool_schemas,
        "compact_tool_schemas": args.compact_tool_schemas,
        "add_argument_cues": args.add_argument_cues,
        "include_rejected_examples": args.include_rejected_examples,
        "rejected_direct_samples": args.rejected_direct_samples,
        "sft_pretrain_epochs": args.sft_pretrain_epochs,
        "pref_train_epochs": args.pref_train_epochs,
        "label_smoothing": args.label_smoothing,
        "learning_rate": args.learning_rate,
        "weight_decay": args.weight_decay,
        "train_all": args.train_all,
        "device": str(device),
    }
    (args.output_dir / "metrics.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    # Log the complete validation result and key training diagnostics to W&B.
    run.log({
        "train/accuracy": train_metrics["accuracy"],
        "train/macro_f1": train_metrics["macro_f1"],
        **({"development/accuracy": dev_metrics["accuracy"], "development/macro_f1": dev_metrics["macro_f1"]} if dev_metrics else {}),
        "training/loss": loss,
        "training/sft_pretrain_loss": sum(sft_pretrain_losses) / max(1, len(sft_pretrain_losses)),
        "training/preference_loss": loss,
        "data/train_examples": len(train),
        "data/development_examples": len(development),
    })
    run.summary.update({**({"development_accuracy": dev_metrics["accuracy"], "development_macro_f1": dev_metrics["macro_f1"]} if dev_metrics else {}), "output_dir": str(args.output_dir), "sft_pretrain_losses": sft_pretrain_losses, "preference_losses": preference_losses})
    print(json.dumps({"train": train_metrics, "development": dev_metrics, "loss": loss}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
