"""Evaluate When2Call checkpoints across fixed development partitions.

The flow builds three deterministic train preference splits, adds the same argument cues, loads
each saved checkpoint, evaluates every checkpoint on every partition, and saves the cross matrix
without loading official test data or fitting any new parameters.
"""
from __future__ import annotations

import json
import atexit
import os
import re
from pathlib import Path

import torch

from experiments.calibrate_clean_validation import collect_logits, load_checkpoint
from experiments.clean_validation_baseline import add_argument_cues, load_training_rows, split_examples
from experiments.train_when2call_jina import LABELS, metric_values, prepare_train_examples
import experiments.train_when2call_jina as jina_training


def prepare_partition(seed: int, tokenizer: object) -> list:
    """Build and tokenize one deterministic argument cue development partition."""
    # Recreate the exact split procedure used by the training experiments.
    _, development = split_examples(prepare_train_examples(load_training_rows()), 0.2, seed)
    add_argument_cues(development)
    for item in development:
        item.token_ids = tokenizer(item.text, add_special_tokens=True, truncation=False, verbose=False)["input_ids"]
    return development


def apply_direct_fallback(examples: list, predictions: list[int]) -> list[int]:
    """Convert clearly answerable tool-mismatch predictions to the direct class."""
    # Use only question text and tool names to test a semantic no-tool-match safeguard.
    direct_cues = re.compile(r"(?i)\b(find|calculate|compute|maximum|minimum|sum|average|count|sort|return)\b")
    updated = list(predictions)
    for index, example in enumerate(examples):
        question, _, tool_text = example.text.partition("\nAvailable tools:\n")
        question_tokens = set(re.findall(r"[a-z][a-z0-9_]+", question.lower()))
        tool_names = set(re.findall(r'"name"\s*:\s*"([^"]+)"', tool_text.lower()))
        if updated[index] == 2 and direct_cues.search(question) and not any(name in question_tokens for name in tool_names):
            updated[index] = 3
    return updated


def main() -> int:
    """Evaluate all available argument cue checkpoints on all development partitions."""
    # Keep checkpoint and split order explicit so the output is easy to compare.
    checkpoints = {
        "seed20": Path("outputs/clean-validation-fixedsplit-seed20-len4096"),
        "seed21": Path("outputs/clean-validation-fixedsplit-seed21-len4096"),
        "seed22": Path("outputs/clean-validation-fixedsplit-seed22-len4096"),
    }
    split_seeds = {"split21": 20261021}
    # Open W&B before loading checkpoints so the ensemble experiment is always tracked.
    import wandb

    if not os.getenv("WANDB_API_KEY"):
        raise RuntimeError("WANDB_API_KEY is required for split stability experiments.")
    run = wandb.init(
        project=os.getenv("WANDB_PROJECT", "when2call-research"),
        entity=os.getenv("WANDB_ENTITY"),
        name="clean-validation-fixedsplit-seed-ensemble-len4096",
        job_type="clean-validation-ensemble",
        config={"checkpoints": {key: str(value) for key, value in checkpoints.items()}, "split_seeds": split_seeds, "max_length": 4096, "test_loaded": False},
    )
    atexit.register(run.finish)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    jina_training.MAX_LENGTH = 4096
    result = {"test_loaded": False, "metrics": {}}
    for split_name, split_seed in split_seeds.items():
        ensemble_logits = []
        labels = None
        for checkpoint_name, checkpoint in checkpoints.items():
            model, tokenizer = load_checkpoint(checkpoint, device, 4096)
            development = prepare_partition(split_seed, tokenizer)
            logits, labels = collect_logits(model, tokenizer, development, device)
            predictions = logits.argmax(dim=1).tolist()
            metrics = metric_values(labels.tolist(), predictions, list(range(len(LABELS))))
            result["metrics"][f"{checkpoint_name}_on_{split_name}"] = metrics
            ensemble_logits.append(logits)
        # Average seed logits to test whether independent training noise cancels on validation.
        ensemble_predictions = torch.stack(ensemble_logits).mean(dim=0).argmax(dim=1).tolist()
        ensemble_metrics = metric_values(labels.tolist(), ensemble_predictions, list(range(len(LABELS))))
        result["metrics"][f"ensemble_on_{split_name}"] = ensemble_metrics
        direct_fallback = apply_direct_fallback(development, ensemble_predictions)
        result["metrics"][f"ensemble_direct_fallback_on_{split_name}"] = metric_values(labels.tolist(), direct_fallback, list(range(len(LABELS))))
        run.log({f"{key}/accuracy": value["accuracy"] for key, value in result["metrics"].items()})
        run.log({f"{key}/macro_f1": value["macro_f1"] for key, value in result["metrics"].items()})
    output = Path("outputs/clean-validation-split-stability.json")
    result["wandb_run_id"] = run.id
    result["wandb_run_url"] = run.url
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: {"accuracy": value["accuracy"], "macro_f1": value["macro_f1"]} for key, value in result["metrics"].items()}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
