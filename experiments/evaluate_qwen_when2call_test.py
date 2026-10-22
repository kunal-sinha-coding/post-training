"""Evaluate one frozen Qwen When2Call adapter on the official test split.

The flow initializes W&B before loading official data, builds the same prompts used by the
Qwen trainer, scores one frozen adapter, reduces hidden labels to aggregate metrics, and saves
only the aggregate result and non-sensitive run metadata.
"""
from __future__ import annotations

import argparse
import atexit
import json
import os
from pathlib import Path

import torch
from datasets import Dataset, load_dataset

from experiments.train_qwen_when2call import (
    DATASET_NAME,
    LABELS,
    LABEL_TO_ID,
    ClassificationRow,
    load_model,
    make_prompt,
    score_rows,
)


TEST_CACHE_PATH = Path("/workspace/.cache/huggingface/datasets/nvidia___when2_call/test/0.0.0/0582f7749df63a96fdc3070932e83e72396ace53/when2_call-mcq.arrow")


def load_official_rows() -> object:
    """Load the immutable official MCQ artifact or the remote test split."""
    # Use the local artifact when available because remote metadata does not expose the MCQ configuration.
    if TEST_CACHE_PATH.exists():
        return Dataset.from_file(str(TEST_CACHE_PATH))
    return load_dataset(DATASET_NAME, "test", split="mcq")


def prepare_test_rows(rows: object) -> list[ClassificationRow]:
    """Build Qwen prompts and retain labels only inside the evaluator."""
    # Convert official labels to the trainer's class order without writing them to any result artifact.
    return [ClassificationRow(make_prompt({"messages": [{"role": "user", "content": row["question"]}], "tools": row["tools"]}), LABEL_TO_ID[str(row["correct_answer"])], None) for row in rows]


def aggregate_metrics(labels: list[int], predictions: list[int]) -> dict[str, float]:
    """Reduce hidden test labels to accuracy and macro F1 only."""
    # Calculate class scores internally and discard all per-example and per-class details immediately.
    matrix = [[0 for _ in LABELS] for _ in LABELS]
    for label, prediction in zip(labels, predictions, strict=True):
        matrix[label][prediction] += 1
    f1_values = []
    for label in range(len(LABELS)):
        true_positive = matrix[label][label]
        predicted = sum(matrix[source][label] for source in range(len(LABELS)))
        support = sum(matrix[label])
        precision = true_positive / predicted if predicted else 0.0
        recall = true_positive / support if support else 0.0
        f1_values.append(2 * precision * recall / (precision + recall) if precision + recall else 0.0)
    return {"accuracy": sum(label == prediction for label, prediction in zip(labels, predictions, strict=True)) / max(1, len(labels)), "macro_f1": sum(f1_values) / len(f1_values)}


def main() -> int:
    """Run one aggregate-only test measurement for a frozen Qwen adapter."""
    # Parse the frozen adapter and reproducibility settings before opening the official split.
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", default="Qwen/Qwen2.5-0.5B-Instruct")
    parser.add_argument("--lora-rank", type=int, default=16)
    parser.add_argument("--max-length", type=int, default=4096)
    parser.add_argument("--batch-size", type=int, default=1)
    args = parser.parse_args()
    # Require W&B before loading any official test rows or model weights.
    import wandb
    if not os.getenv("WANDB_API_KEY"):
        raise RuntimeError("WANDB_API_KEY is required for the official test measurement.")
    run = wandb.init(project=os.getenv("WANDB_PROJECT", "when2call-research"), entity=os.getenv("WANDB_ENTITY"), name=f"qwen-when2call-test-{args.checkpoint.name}", job_type="official-test-measurement", config={"checkpoint": str(args.checkpoint), "base_model": args.model, "dataset": f"{DATASET_NAME}:test/mcq", "black_box": True, "selection_complete": True, "max_length": args.max_length})
    atexit.register(run.finish)
    # Load the frozen adapter and official examples only after the measurement run is registered.
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model, tokenizer = load_model(args.model, device, args.lora_rank)
    # Load the frozen adapter beside the empty training adapter and activate only the frozen weights.
    if not hasattr(model, "load_adapter"):
        raise TypeError("The Qwen checkpoint did not produce a PEFT model.")
    model.load_adapter(str(args.checkpoint), adapter_name="frozen")
    model.set_adapter("frozen")
    rows = prepare_test_rows(load_official_rows())
    label_ids = [tokenizer.encode(f" {letter}", add_special_tokens=False)[0] for letter in "ABCD"]
    predictions = []
    model.eval()
    # Score the test rows in small batches and retain predictions only until aggregate reduction completes.
    with torch.no_grad():
        for start in range(0, len(rows), args.batch_size):
            scores = score_rows(model, tokenizer, rows[start:start + args.batch_size], label_ids, device, args.max_length)
            predictions.extend(scores.argmax(dim=-1).cpu().tolist())
    labels = [row.label for row in rows]
    metrics = aggregate_metrics(labels, predictions)
    # Log and save only the permitted aggregate metrics and non-label operational metadata.
    run.log({"test/accuracy": metrics["accuracy"], "test/macro_f1": metrics["macro_f1"]})
    run.summary.update({"test_accuracy": metrics["accuracy"], "test_macro_f1": metrics["macro_f1"], "black_box": True, "selection_complete": True})
    result = {"dataset": DATASET_NAME, "split": "test/mcq", "test_loaded": True, "test_measurement_only": True, "black_box": True, "checkpoint": str(args.checkpoint), "base_model": args.model, "examples": len(rows), "metrics": metrics, "wandb_run_id": run.id, "wandb_run_url": run.url}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(metrics, indent=2))
    return 0


if __name__ == "__main__":
    # Return a nonzero status when the official measurement fails so the supervisor records the failure.
    raise SystemExit(main())
