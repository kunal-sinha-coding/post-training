"""Evaluate When2Call checkpoints across fixed development partitions.

The flow builds three deterministic train preference splits, adds the same argument cues, loads
each saved checkpoint, evaluates every checkpoint on every partition, and saves the cross matrix
without loading official test data or fitting any new parameters.
"""
from __future__ import annotations

import json
from pathlib import Path

import torch

from experiments.calibrate_clean_validation import collect_logits, load_checkpoint
from experiments.clean_validation_baseline import add_argument_cues, load_training_rows, split_examples
from experiments.train_when2call_jina import LABELS, metric_values, prepare_train_examples


def prepare_partition(seed: int, tokenizer: object) -> list:
    """Build and tokenize one deterministic argument cue development partition."""
    # Recreate the exact split procedure used by the training experiments.
    _, development = split_examples(prepare_train_examples(load_training_rows()), 0.2, seed)
    add_argument_cues(development)
    for item in development:
        item.token_ids = tokenizer(item.text, add_special_tokens=True, truncation=False, verbose=False)["input_ids"]
    return development


def main() -> int:
    """Evaluate all available argument cue checkpoints on all development partitions."""
    # Keep checkpoint and split order explicit so the output is easy to compare.
    checkpoints = {
        "seed20": Path("outputs/clean-validation-argument-cues"),
        "seed21": Path("outputs/clean-validation-argument-cues-seed21"),
        "seed22": Path("outputs/clean-validation-argument-cues-seed22"),
    }
    split_seeds = {"split20": 20261020, "split21": 20261021, "split22": 20261022}
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    result = {"test_loaded": False, "metrics": {}}
    for checkpoint_name, checkpoint in checkpoints.items():
        model, tokenizer = load_checkpoint(checkpoint, device)
        for split_name, split_seed in split_seeds.items():
            development = prepare_partition(split_seed, tokenizer)
            logits, labels = collect_logits(model, tokenizer, development, device)
            predictions = logits.argmax(dim=1).tolist()
            result["metrics"][f"{checkpoint_name}_on_{split_name}"] = metric_values(labels.tolist(), predictions, list(range(len(LABELS))))
    output = Path("outputs/clean-validation-split-stability.json")
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: {"accuracy": value["accuracy"], "macro_f1": value["macro_f1"]} for key, value in result["metrics"].items()}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
