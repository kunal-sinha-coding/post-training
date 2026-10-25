"""Train a base Qwen action classifier on labeled BFCL Live examples for one epoch.

The flow loads the overlap-filtered BFCL corpus, uses its fixed seeded train and held-out split,
initializes a fresh LoRA adapter on the Qwen base model, records loss every optimizer step, evaluates
training and held-out BFCL rows at epoch end, and reports aggregate-only When2Call test metrics before
and after the single predetermined training epoch without using test metrics for selection.
"""
from __future__ import annotations

import argparse
import atexit
import json
import os
import random
from pathlib import Path

import torch
import wandb

from experiments.evaluate_qwen_when2call_test import aggregate_metrics, load_official_rows, prepare_test_rows
from experiments.train_qwen_when2call import (
    LABELS,
    ClassificationRow,
    evaluate,
    label_token_ids,
    load_model,
    reference_scores,
    train_epoch,
    write_heartbeat,
)


def load_labeled_rows(path: Path) -> tuple[list[ClassificationRow], list[ClassificationRow]]:
    """Load resolved labels and retain the fixed training and validation split."""
    # Exclude unresolved rows and preserve the split assigned before model training.
    train_rows, validation_rows = [], []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        item = json.loads(line)
        if item["label"] not in LABELS:
            continue
        row = ClassificationRow(item["prompt"], LABELS.index(item["label"]), None)
        if item["split"] == "train":
            train_rows.append(row)
        elif item["split"] == "validation":
            validation_rows.append(row)
    return train_rows, validation_rows


def evaluate_black_box(model: object, tokenizer: object, label_ids: list[int], device: torch.device, max_length: int, batch_size: int) -> dict:
    """Return aggregate accuracy and macro F1 for the report-only When2Call test measurement."""
    # Load test labels only inside this evaluator and discard predictions after aggregate reduction.
    rows = prepare_test_rows(load_official_rows())
    predictions = []
    model.eval()
    with torch.no_grad():
        for start in range(0, len(rows), batch_size):
            scores = reference_scores(model, tokenizer, rows[start:start + batch_size], label_ids, device, max_length)
            predictions.extend(scores.argmax(dim=-1).cpu().tolist())
    labels = [row.label for row in rows]
    return aggregate_metrics(labels, predictions) | {"examples": len(rows)}


def main() -> int:
    """Run one fixed base-model training epoch and save all required evidence."""
    # Parse the model, data, and one-epoch controls before loading the test split or model weights.
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=Path("data/bfcl_when2call_labeled.jsonl"))
    parser.add_argument("--metadata", type=Path, default=Path("data/bfcl_when2call_labeled.metadata.json"))
    parser.add_argument("--model", default="Qwen/Qwen2.5-1.5B-Instruct")
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/qwen-bfcl-when2call-base-1p5b-seed20261025"))
    parser.add_argument("--seed", type=int, default=20261025)
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--eval-batch-size", type=int, default=1)
    parser.add_argument("--max-length", type=int, default=4096)
    parser.add_argument("--learning-rate", type=float, default=2e-5)
    parser.add_argument("--weight-decay", type=float, default=0.01)
    parser.add_argument("--lora-rank", type=int, default=16)
    args = parser.parse_args()
    # Require experiment tracking before loading data and register the exact setup.
    if not os.getenv("WANDB_API_KEY"):
        raise RuntimeError("WANDB_API_KEY is required for Qwen experiments.")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    config = {key: str(value) if isinstance(value, Path) else value for key, value in vars(args).items()}
    label_metadata = json.loads(args.metadata.read_text(encoding="utf-8"))
    run = wandb.init(project=os.getenv("WANDB_PROJECT", "when2call-research"), entity=os.getenv("WANDB_ENTITY"), name=f"qwen-bfcl-base-{args.output_dir.name}", job_type="bfcl-when2call-sft", config=config | {"label_counts": label_metadata["label_counts"], "official_test_selection": False})
    atexit.register(run.finish)
    # Fix random sources before model construction and optimizer setup.
    random.seed(args.seed)
    torch.manual_seed(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    heartbeat = args.output_dir / "heartbeat.json"
    write_heartbeat(heartbeat, "loading")
    train_rows, validation_rows = load_labeled_rows(args.data)
    if not train_rows or not validation_rows:
        raise RuntimeError("The resolved BFCL corpus must contain training and held-out validation rows.")
    model, tokenizer = load_model(args.model, device, args.lora_rank)
    label_ids = label_token_ids(tokenizer)
    # Measure the untouched base model before training so the final report can show a report-only delta.
    write_heartbeat(heartbeat, "baseline_black_box_evaluation")
    baseline_test = evaluate_black_box(model, tokenizer, label_ids, device, args.max_length, args.eval_batch_size)
    run.log({"test/base_accuracy": baseline_test["accuracy"], "test/base_macro_f1": baseline_test["macro_f1"]}, step=0)
    # Train only the non-overlapping BFCL training partition with a fresh base-model adapter.
    optimizer = torch.optim.AdamW((parameter for parameter in model.parameters() if parameter.requires_grad), lr=args.learning_rate, weight_decay=args.weight_decay)
    def log_step(step: int, loss: float) -> bool:
        # Log the scalar loss after every completed optimizer update.
        run.log({"training/optimizer_step_loss": loss}, step=step)
        return False
    losses = []
    for epoch in range(args.epochs):
        epoch_loss = train_epoch(model, tokenizer, train_rows, label_ids, "sft", device, optimizer, args.max_length, args.batch_size, 0.1, args.seed + epoch, heartbeat, log_step)
        losses.append(epoch_loss)
        # Evaluate both BFCL partitions only after the complete epoch, as requested.
        train_metrics = evaluate(model, tokenizer, train_rows, label_ids, device, args.max_length, args.eval_batch_size, heartbeat)
        validation_metrics = evaluate(model, tokenizer, validation_rows, label_ids, device, args.max_length, args.eval_batch_size, heartbeat)
        run.log({"epoch": epoch + 1, "training/epoch_loss": epoch_loss, "training/accuracy": train_metrics["accuracy"], "training/macro_f1": train_metrics["macro_f1"], "heldout_validation/accuracy": validation_metrics["accuracy"], "heldout_validation/macro_f1": validation_metrics["macro_f1"]}, step=len(train_rows) * (epoch + 1))
    # Save the single predetermined epoch checkpoint before the report-only test measurement.
    model.save_pretrained(args.output_dir)
    tokenizer.save_pretrained(args.output_dir)
    write_heartbeat(heartbeat, "black_box_evaluation")
    final_test = evaluate_black_box(model, tokenizer, label_ids, device, args.max_length, args.eval_batch_size)
    run.log({"test/trained_accuracy": final_test["accuracy"], "test/trained_macro_f1": final_test["macro_f1"], "test/accuracy_delta": final_test["accuracy"] - baseline_test["accuracy"], "test/macro_f1_delta": final_test["macro_f1"] - baseline_test["macro_f1"]}, step=len(train_rows) * args.epochs + 1)
    # Save reproduction details and aggregate-only test metrics after all fixed evaluations finish.
    result = {
        "experiment": "qwen25_1p5b_base_lora_bfcl_live_nonoverlap_one_epoch",
        "purpose": "Test whether non-overlapping BFCL Live action labels improve When2Call action classification.",
        "config": config,
        "data_path": str(args.data),
        "data_metadata": label_metadata,
        "candidate_selection": "No checkpoint or run selection was performed. Training lasted the predeclared single epoch.",
        "test_label_use": "Aggregate-only black-box measurements before and after the fixed run. Test metrics were not used for selection.",
        "train_examples": len(train_rows),
        "heldout_validation_examples": len(validation_rows),
        "training_loss_by_epoch": losses,
        "training_metrics": train_metrics,
        "heldout_validation_metrics": validation_metrics,
        "black_box_test_base_metrics": baseline_test,
        "black_box_test_trained_metrics": final_test,
        "black_box_test_accuracy_delta": final_test["accuracy"] - baseline_test["accuracy"],
        "black_box_test_macro_f1_delta": final_test["macro_f1"] - baseline_test["macro_f1"],
        "wandb_run_id": run.id,
        "wandb_run_url": run.url,
        "device": str(device),
    }
    (args.output_dir / "metrics.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    run.summary.update({"training_accuracy": train_metrics["accuracy"], "training_macro_f1": train_metrics["macro_f1"], "heldout_validation_accuracy": validation_metrics["accuracy"], "heldout_validation_macro_f1": validation_metrics["macro_f1"], "test_accuracy": final_test["accuracy"], "test_macro_f1": final_test["macro_f1"], "test_selection_used": False})
    write_heartbeat(heartbeat, "completed", len(train_rows) * args.epochs)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    # Return a nonzero exit status when any required experiment stage fails.
    raise SystemExit(main())
