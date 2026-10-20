"""Train a MiniLM When2Call classifier and score it through aggregate-only test output.

The flow loads cached train preferences, creates a stratified development split for diagnostics,
fine-tunes a locally cached MiniLM encoder, evaluates the frozen candidate on official inputs, and
logs only aggregate test accuracy and macro F1 to W&B and the output artifact.
"""
from __future__ import annotations

import argparse
import atexit
import json
import os
import random
from pathlib import Path

import torch
from datasets import Dataset
from transformers import AutoModel, AutoTokenizer

from experiments.clean_validation_baseline import split_examples
from experiments.train_when2call_jina import LABELS, JinaSequenceClassifier, batch_metrics, collate, metric_values, prepare_test_examples, prepare_train_examples

MINILM_MODEL = "nreimers/MiniLM-L6-H384-uncased"


def load_cached_rows(path: Path) -> object:
    """Load one local Arrow artifact without contacting remote dataset metadata."""
    # Keep the candidate data sources explicit and reproducible.
    return Dataset.from_file(str(path))


def train_epoch(model: torch.nn.Module, tokenizer: object, examples: list, device: torch.device, optimizer: object, seed: int) -> float:
    """Run one shuffled MiniLM training epoch and return its mean loss."""
    # Use small batches to fit the locally available accelerator.
    model.train()
    order = list(examples)
    random.Random(seed).shuffle(order)
    losses = []
    for start in range(0, len(order), 16):
        batch = collate(order[start:start + 16], tokenizer)
        labels = batch.pop("labels").to(device)
        batch.pop("rejected_labels")
        batch.pop("source_ids")
        inputs = {key: value.to(device) for key, value in batch.items()}
        optimizer.zero_grad(set_to_none=True)
        logits = model(**inputs).logits
        loss = torch.nn.functional.cross_entropy(logits, labels)
        loss.backward()
        optimizer.step()
        losses.append(float(loss.detach().cpu()))
    return sum(losses) / max(1, len(losses))


def main() -> int:
    """Train the MiniLM candidate and return aggregate black-box test metrics."""
    # Parse the fixed architecture and training controls before opening the tracker.
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--learning-rate", type=float, default=2e-5)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    # Open W&B before data or model loading so failures are tracked.
    import wandb
    if not os.getenv("WANDB_API_KEY"):
        raise RuntimeError("WANDB_API_KEY is required for MiniLM experiments.")
    run = wandb.init(project=os.getenv("WANDB_PROJECT", "when2call-research"), entity=os.getenv("WANDB_ENTITY"), name="when2call-minilm-blackbox", job_type="black-box-test-candidate", config=vars(args))
    atexit.register(run.finish)
    random.seed(20261022)
    torch.manual_seed(20261022)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    # Load only cached training and official input artifacts.
    train_path = Path("/workspace/.cache/huggingface/datasets/nvidia___when2_call/train_pref/0.0.0/0582f7749df63a96fdc3070932e83e72396ace53/when2_call-train.arrow")
    test_path = Path("/workspace/.cache/huggingface/datasets/nvidia___when2_call/test/0.0.0/0582f7749df63a96fdc3070932e83e72396ace53/when2_call-mcq.arrow")
    examples = prepare_train_examples(load_cached_rows(train_path))
    train, development = split_examples(examples, 0.2, 20261021)
    tokenizer = AutoTokenizer.from_pretrained(MINILM_MODEL, trust_remote_code=True, force_download=True)
    tokenizer.model_max_length = 512
    model = JinaSequenceClassifier(AutoModel.from_pretrained(MINILM_MODEL, trust_remote_code=True, force_download=True), len(LABELS)).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate)
    losses = []
    for epoch in range(args.epochs):
        losses.append(train_epoch(model, tokenizer, train, device, optimizer, 20261022 + epoch))
    dev_metrics = batch_metrics(model, tokenizer, development, device, list(range(len(LABELS))))
    test_examples = prepare_test_examples(load_cached_rows(test_path))
    test_metrics = batch_metrics(model, tokenizer, test_examples, device, list(range(len(LABELS))))
    aggregate = {"accuracy": test_metrics["accuracy"], "macro_f1": test_metrics["macro_f1"]}
    result = {"model": "nreimers/MiniLM-L6-H384-uncased", "epochs": args.epochs, "learning_rate": args.learning_rate, "development": {"accuracy": dev_metrics["accuracy"], "macro_f1": dev_metrics["macro_f1"]}, "black_box": True, "metrics": aggregate, "wandb_run_id": run.id, "wandb_run_url": run.url}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    # Log only aggregate test metrics while retaining training diagnostics in W&B.
    run.log({"training/loss": sum(losses) / max(1, len(losses)), "development/accuracy": dev_metrics["accuracy"], "development/macro_f1": dev_metrics["macro_f1"], "test/accuracy": aggregate["accuracy"], "test/macro_f1": aggregate["macro_f1"]})
    run.summary.update({"test_accuracy": aggregate["accuracy"], "test_macro_f1": aggregate["macro_f1"], "black_box": True})
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    # Run the MiniLM experiment as a module entry point.
    raise SystemExit(main())
