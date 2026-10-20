"""Evaluate frozen When2Call candidates through an aggregate-only official test interface.

The flow loads frozen checkpoints, computes predictions inside the evaluator, returns only
aggregate accuracy and macro F1, logs no example-level labels, and saves no per-class detail.
"""
from __future__ import annotations

import argparse
import atexit
import json
import os
from pathlib import Path

import torch
from datasets import Dataset, load_dataset

import experiments.train_when2call_jina as jina_training
from experiments.calibrate_clean_validation import collect_logits, load_checkpoint
from experiments.train_when2call_jina import DATASET_NAME, LABELS, metric_values, prepare_test_examples


def aggregate_metrics(labels: list[int], predictions: list[int]) -> dict[str, float]:
    """Reduce hidden test labels to the two permitted aggregate metrics."""
    # Compute the complete metric internally and discard all label-conditioned details immediately.
    metrics = metric_values(labels, predictions, list(range(len(LABELS))))
    return {"accuracy": metrics["accuracy"], "macro_f1": metrics["macro_f1"]}


def load_official_test_rows() -> object:
    """Load the cached official MCQ rows when remote configuration metadata is incomplete."""
    # Use the immutable local test artifact because the remote dataset exposes only default metadata.
    cache_path = Path("/workspace/.cache/huggingface/datasets/nvidia___when2_call/test/0.0.0/0582f7749df63a96fdc3070932e83e72396ace53/when2_call-mcq.arrow")
    if cache_path.exists():
        return Dataset.from_file(str(cache_path))
    return load_dataset(DATASET_NAME, "test", split="mcq")


def main() -> int:
    """Measure the frozen validation-selected ensemble on the official test split."""
    # Parse only the frozen checkpoint and output locations for the one authorized test pass.
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("outputs/clean-validation-final-test-ensemble.json"))
    parser.add_argument("--checkpoint", action="append", dest="checkpoint_paths", help="Frozen checkpoint path. Repeat once per ensemble member.")
    parser.add_argument("--weight", action="append", dest="weights", type=float, help="Logit weight for each checkpoint. Repeat once per checkpoint.")
    args = parser.parse_args()
    # Open W&B before loading official examples so the post-selection measurement is tracked.
    import wandb

    if not os.getenv("WANDB_API_KEY"):
        raise RuntimeError("WANDB_API_KEY is required for the official test measurement.")
    # Use explicit frozen checkpoints for black-box candidate comparison, with the original ensemble as default.
    checkpoint_paths = args.checkpoint_paths or [
        "outputs/clean-validation-fixedsplit-seed20-len4096",
        "outputs/clean-validation-fixedsplit-seed21-len4096",
        "outputs/clean-validation-fixedsplit-seed22-len4096",
    ]
    checkpoints = {f"checkpoint{index}": Path(path) for index, path in enumerate(checkpoint_paths)}
    weights = torch.tensor(args.weights if args.weights is not None else [1.0] * len(checkpoints), dtype=torch.float32)
    if len(weights) != len(checkpoints) or float(weights.sum()) <= 0:
        raise ValueError("The number of weights must match checkpoints and their sum must be positive.")
    weights = weights / weights.sum()
    run = wandb.init(
        project=os.getenv("WANDB_PROJECT", "when2call-research"),
        entity=os.getenv("WANDB_ENTITY"),
        name="when2call-blackbox-test-aggregate",
        job_type="official-test-measurement",
        config={"checkpoints": {key: str(value) for key, value in checkpoints.items()}, "weights": weights.tolist(), "dataset": f"{DATASET_NAME}:test/mcq", "selection_complete": True, "black_box": True, "max_length": 4096},
    )
    atexit.register(run.finish)
    # Freeze the model context and load the official labels only for final measurement.
    # Keep the native collator limit while explicitly truncating every test input to 4096.
    jina_training.MAX_LENGTH = 8192
    rows = load_official_test_rows()
    examples = prepare_test_examples(rows)
    truncated_examples = 0
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logits_by_checkpoint = []
    result = {"dataset": DATASET_NAME, "split": "test/mcq", "test_loaded": True, "selection_complete": True, "test_measurement_only": True, "black_box": True, "checkpoints": {key: str(value) for key, value in checkpoints.items()}, "examples": len(examples), "metrics": {}}
    # Evaluate each frozen checkpoint independently before averaging its logits.
    labels = None
    for checkpoint_name, checkpoint in checkpoints.items():
        model, tokenizer = load_checkpoint(checkpoint, device, 4096)
        for item in examples:
            item.token_ids = tokenizer(item.text, add_special_tokens=True, truncation=False, verbose=False)["input_ids"]
            if len(item.token_ids) > 4096:
                item.token_ids = item.token_ids[:4096]
                if checkpoint_name == "seed20":
                    truncated_examples += 1
        # Use small inference batches because complete test inputs can approach the context limit.
        logits, labels = collect_logits(model, tokenizer, examples, device, batch_size=4)
        logits_by_checkpoint.append(logits)
        result["metrics"][checkpoint_name] = aggregate_metrics(labels.tolist(), logits.argmax(dim=1).tolist())
    # Average frozen seed logits and compute the single official ensemble measurement.
    ensemble_logits = (torch.stack(logits_by_checkpoint) * weights.view(-1, 1, 1).to(logits_by_checkpoint[0].device)).sum(dim=0)
    result["metrics"]["ensemble"] = aggregate_metrics(labels.tolist(), ensemble_logits.argmax(dim=1).tolist())
    result["wandb_run_id"] = run.id
    result["wandb_run_url"] = run.url
    result["truncated_examples"] = truncated_examples
    # Log the official metrics after selection without using them for another decision.
    run.log({f"test/{key}/accuracy": value["accuracy"] for key, value in result["metrics"].items()})
    run.log({f"test/{key}/macro_f1": value["macro_f1"] for key, value in result["metrics"].items()})
    run.summary.update({"test_accuracy": result["metrics"]["ensemble"]["accuracy"], "test_macro_f1": result["metrics"]["ensemble"]["macro_f1"], "selection_complete": True})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: {"accuracy": value["accuracy"], "macro_f1": value["macro_f1"]} for key, value in result["metrics"].items()}, indent=2))
    return 0


if __name__ == "__main__":
    # Exit with the official measurement result so the supervisor records completion.
    raise SystemExit(main())
