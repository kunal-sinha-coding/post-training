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
    write_heartbeat,
)


TEST_CACHE_PATH = Path("/workspace/.cache/huggingface/datasets/nvidia___when2_call/test/0.0.0/0582f7749df63a96fdc3070932e83e72396ace53/when2_call-mcq.arrow")


def load_official_rows() -> object:
    """Load the immutable official MCQ artifact or the remote test split."""
    # Use the local artifact when available because remote metadata does not expose the MCQ configuration.
    if TEST_CACHE_PATH.exists():
        return Dataset.from_file(str(TEST_CACHE_PATH))
    return load_dataset(DATASET_NAME, "test", split="mcq")


def prepare_test_rows(rows: object, corrected_label_order: bool = False) -> list[ClassificationRow]:
    """Build Qwen prompts and retain labels only inside the evaluator."""
    # Convert official labels to the trainer class order without saving any row-level label.
    prepared = []
    for row in rows:
        prompt = make_prompt({"messages": [{"role": "user", "content": row["question"]}], "tools": row["tools"]})
        # Match the learned output-token order used by the clean retrieval screen when requested.
        if corrected_label_order:
            prompt = prompt.replace(
                "A = direct answer.\nB = tool call.\nC = request for more information.\nD = cannot answer.",
                "A = cannot answer.\nB = request for more information.\nC = tool call.\nD = direct answer.",
            )
        prepared.append(ClassificationRow(prompt, LABEL_TO_ID[str(row["correct_answer"])], None))
    return prepared


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
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--model", default="Qwen/Qwen2.5-0.5B-Instruct")
    parser.add_argument("--training-metrics-source", type=Path)
    parser.add_argument("--lora-rank", type=int, default=16)
    parser.add_argument("--max-length", type=int, default=4096)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--corrected-learned-label-order", action="store_true")
    args = parser.parse_args()
    # Load training and clean-validation provenance from the exact checkpoint's experiment record.
    source_training_metrics = None
    source_validation_metrics = None
    if args.training_metrics_source:
        source_metrics = json.loads(args.training_metrics_source.read_text(encoding="utf-8"))
        checkpoint_name = str(args.checkpoint)
        source_epoch = next((item for item in source_metrics.get("epoch_records", []) if item.get("checkpoint") == checkpoint_name), None)
        if source_epoch:
            source_training_metrics = {key: source_epoch.get(key) for key in ("epoch", "step", "training_loss", "training_metrics", "training_evaluation_examples")}
            source_validation_metrics = {key: source_epoch.get(key) for key in ("heldout_validation_metrics", "validation_source", "validation_examples")}
    # Require a worker output directory so the watchdog can monitor test progress.
    output_dir = args.output_dir or (args.output.parent if args.output else None)
    if output_dir is None:
        raise ValueError("Either --output-dir or --output is required.")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "metrics.json"
    # Require W&B before loading any official test rows or model weights.
    from dotenv import load_dotenv
    load_dotenv(".env")
    import wandb
    if not os.getenv("WANDB_API_KEY"):
        raise RuntimeError("WANDB_API_KEY is required for the official test measurement.")
    run = wandb.init(project=os.getenv("WANDB_PROJECT", "when2call-research"), entity=os.getenv("WANDB_ENTITY"), name=f"qwen-when2call-test-{args.checkpoint.name}", job_type="official-test-measurement", config={"checkpoint": str(args.checkpoint), "base_model": args.model, "dataset": f"{DATASET_NAME}:test/mcq", "black_box": True, "selection_complete": True, "max_length": args.max_length, "corrected_learned_label_order": args.corrected_learned_label_order})
    atexit.register(run.finish)
    # Load the frozen adapter and official examples only after the measurement run is registered.
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    write_heartbeat(output_dir / "heartbeat.json", "loading")
    model, tokenizer = load_model(args.model, device, args.lora_rank)
    # Load the frozen adapter beside the empty training adapter and activate only the frozen weights.
    if not hasattr(model, "load_adapter"):
        raise TypeError("The Qwen checkpoint did not produce a PEFT model.")
    model.load_adapter(str(args.checkpoint), adapter_name="frozen")
    model.set_adapter("frozen")
    rows = prepare_test_rows(load_official_rows(), args.corrected_learned_label_order)
    label_ids = [tokenizer.encode(f" {letter}", add_special_tokens=False)[0] for letter in "ABCD"]
    predictions = []
    model.eval()
    # Score the test rows in small batches and retain predictions only until aggregate reduction completes.
    with torch.no_grad():
        for start in range(0, len(rows), args.batch_size):
            write_heartbeat(output_dir / "heartbeat.json", "evaluation", start)
            scores = score_rows(model, tokenizer, rows[start:start + args.batch_size], label_ids, device, args.max_length)
            predictions.extend(scores.argmax(dim=-1).cpu().tolist())
    labels = [row.label for row in rows]
    metrics = aggregate_metrics(labels, predictions)
    # Log and save only the permitted aggregate metrics and non-label operational metadata.
    run.log({"test/accuracy": metrics["accuracy"], "test/macro_f1": metrics["macro_f1"]})
    run.summary.update({"test_accuracy": metrics["accuracy"], "test_macro_f1": metrics["macro_f1"], "black_box": True, "selection_complete": True})
    result = {"dataset": DATASET_NAME, "split": "test/mcq", "test_loaded": True, "official_test_loaded": True, "test_measurement_only": True, "black_box": True, "checkpoint": str(args.checkpoint), "base_model": args.model, "prompt_label_order": "A=cannot_answer, B=request_for_info, C=tool_call, D=direct" if args.corrected_learned_label_order else "historical training prompt order", "training_metrics_source": str(args.training_metrics_source) if args.training_metrics_source else None, "training_metrics": source_training_metrics, "clean_validation_metrics_source": str(args.training_metrics_source) if args.training_metrics_source else None, "clean_validation_metrics": source_validation_metrics, "examples": len(rows), "official_test_metrics": metrics, "metrics": metrics, "wandb_run_id": run.id, "wandb_run_url": run.url}
    result["output_dir"] = str(output_dir)
    output_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    write_heartbeat(output_dir / "heartbeat.json", "completed")
    print(json.dumps(metrics, indent=2))
    return 0


if __name__ == "__main__":
    # Return a nonzero status when the official measurement fails so the supervisor records the failure.
    raise SystemExit(main())
