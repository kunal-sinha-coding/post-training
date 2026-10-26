"""Continue the best Qwen action adapter on labeled BFCL Live examples.

The flow loads the overlap-filtered BFCL corpus and fixed split, continues a selected LoRA adapter,
records loss at every optimizer step, evaluates training, held-out BFCL, and aggregate-only test metrics
at each epoch, and selects a checkpoint by held-out BFCL validation accuracy.
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
    score_rows,
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
    # Score the active adapter and discard every per-example prediction after aggregate reduction.
    rows = prepare_test_rows(load_official_rows())
    predictions = []
    model.eval()
    with torch.no_grad():
        for start in range(0, len(rows), batch_size):
            scores = score_rows(model, tokenizer, rows[start:start + batch_size], label_ids, device, max_length)
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
    parser.add_argument("--initial-checkpoint", type=Path, default=Path("outputs/qwen-when2call-qwen25-15b-pref-full-glaive500-toolcall-seed20261035"))
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/qwen-best-sft-bfcl-live-continue-seed20261048"))
    parser.add_argument("--seed", type=int, default=20261048)
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
    model, tokenizer = load_model(args.model, device, 0, str(args.initial_checkpoint))
    label_ids = label_token_ids(tokenizer)
    # Measure the starting adapter on all three splits before training.
    write_heartbeat(heartbeat, "baseline_black_box_evaluation")
    baseline_train = evaluate(model, tokenizer, train_rows, label_ids, device, args.max_length, args.eval_batch_size, heartbeat)
    baseline_validation = evaluate(model, tokenizer, validation_rows, label_ids, device, args.max_length, args.eval_batch_size, heartbeat)
    baseline_test = evaluate_black_box(model, tokenizer, label_ids, device, args.max_length, args.eval_batch_size)
    run.log({"baseline/training_accuracy": baseline_train["accuracy"], "baseline/training_macro_f1": baseline_train["macro_f1"], "baseline/heldout_validation_accuracy": baseline_validation["accuracy"], "baseline/heldout_validation_macro_f1": baseline_validation["macro_f1"], "test/base_accuracy": baseline_test["accuracy"], "test/base_macro_f1": baseline_test["macro_f1"]}, step=0)
    # Continue the selected adapter using only the BFCL training partition.
    optimizer = torch.optim.AdamW((parameter for parameter in model.parameters() if parameter.requires_grad), lr=args.learning_rate, weight_decay=args.weight_decay)
    def log_step(step: int, loss: float) -> bool:
        # Log the scalar loss after every completed optimizer update.
        run.log({"training/optimizer_step_loss": loss}, step=step)
        return False
    losses = []
    epoch_records = []
    best_validation_accuracy = float("-inf")
    best_checkpoint = None
    for epoch in range(args.epochs):
        epoch_loss = train_epoch(model, tokenizer, train_rows, label_ids, "sft", device, optimizer, args.max_length, args.batch_size, 0.1, args.seed + epoch, heartbeat, log_step)
        losses.append(epoch_loss)
        # Evaluate both BFCL partitions only after the complete epoch, as requested.
        train_metrics = evaluate(model, tokenizer, train_rows, label_ids, device, args.max_length, args.eval_batch_size, heartbeat)
        validation_metrics = evaluate(model, tokenizer, validation_rows, label_ids, device, args.max_length, args.eval_batch_size, heartbeat)
        write_heartbeat(heartbeat, "black_box_evaluation", epoch + 1)
        test_metrics = evaluate_black_box(model, tokenizer, label_ids, device, args.max_length, args.eval_batch_size)
        epoch_step = len(train_rows) * (epoch + 1)
        run.log({"epoch": epoch + 1, "training/epoch_loss": epoch_loss, "training/accuracy": train_metrics["accuracy"], "training/macro_f1": train_metrics["macro_f1"], "heldout_validation/accuracy": validation_metrics["accuracy"], "heldout_validation/macro_f1": validation_metrics["macro_f1"], "test/accuracy": test_metrics["accuracy"], "test/macro_f1": test_metrics["macro_f1"]}, step=epoch_step)
        checkpoint_dir = args.output_dir / f"epoch-{epoch + 1:02d}"
        model.save_pretrained(checkpoint_dir)
        tokenizer.save_pretrained(checkpoint_dir)
        epoch_records.append({"epoch": epoch + 1, "loss": epoch_loss, "training_metrics": train_metrics, "heldout_validation_metrics": validation_metrics, "black_box_test_metrics": test_metrics, "checkpoint": str(checkpoint_dir)})
        if validation_metrics["accuracy"] > best_validation_accuracy:
            best_validation_accuracy = validation_metrics["accuracy"]
            best_checkpoint = str(checkpoint_dir)
    train_metrics = epoch_records[-1]["training_metrics"]
    validation_metrics = epoch_records[-1]["heldout_validation_metrics"]
    final_test = epoch_records[-1]["black_box_test_metrics"]
    # Save reproduction details and aggregate-only test metrics after every epoch is complete.
    result = {
        "experiment": "qwen25_1p5b_best_adapter_bfcl_live_continuation",
        "purpose": "Test whether non-overlapping BFCL Live action labels improve the highest historical Qwen 1.5B checkpoint.",
        "config": config,
        "initial_checkpoint": str(args.initial_checkpoint),
        "data_path": str(args.data),
        "data_metadata": label_metadata,
        "candidate_selection": "The initial checkpoint was selected by the user's requested historical aggregate test accuracy. Within this run, the best epoch is selected by held-out BFCL validation accuracy only.",
        "test_label_use": "Aggregate-only measurements at baseline and after each epoch. Test labels and individual predictions are not used for checkpoint selection.",
        "train_examples": len(train_rows),
        "heldout_validation_examples": len(validation_rows),
        "baseline_training_metrics": baseline_train,
        "baseline_heldout_validation_metrics": baseline_validation,
        "baseline_black_box_test_metrics": baseline_test,
        "epoch_records": epoch_records,
        "best_validation_checkpoint": best_checkpoint,
        "best_validation_accuracy": best_validation_accuracy,
        "training_loss_by_epoch": losses,
        "training_metrics": train_metrics,
        "heldout_validation_metrics": validation_metrics,
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
