"""Train base Qwen on every When2Call preference row and report each epoch.

The flow loads the complete `train_pref` dataset, formats all 9,000 rows without a held-out split,
trains a fresh LoRA adapter for a fixed number of epochs, and reports train and aggregate-only test
metrics after every epoch without selecting checkpoints from test scores.
"""
from __future__ import annotations

import argparse
import atexit
import hashlib
import json
import os
import random
from collections import Counter
from pathlib import Path

import torch
import wandb

from experiments.train_qwen_bfcl_when2call import evaluate_black_box
from experiments.train_qwen_when2call import (
    DATASET_NAME,
    evaluate,
    label_token_ids,
    load_model,
    load_rows,
    prepare_rows,
    train_epoch,
    write_heartbeat,
)


def fingerprint_rows(rows: list[object]) -> str:
    """Hash formatted prompts and chosen labels without storing examples."""
    # Sort per-row hashes so the fingerprint does not depend on data iteration order.
    row_hashes = sorted(hashlib.sha256((row.prompt + "\n" + str(row.label)).encode()).hexdigest() for row in rows)
    return hashlib.sha256("\n".join(row_hashes).encode()).hexdigest()


def main() -> int:
    """Train on all preference rows and record fixed-epoch results."""
    # Parse fixed model, training, evaluation, and output controls.
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="Qwen/Qwen2.5-1.5B-Instruct")
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/qwen-when2call-fullpool-base-seed20261050"))
    parser.add_argument("--seed", type=int, default=20261050)
    parser.add_argument("--epochs", type=int, default=2)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--eval-batch-size", type=int, default=4)
    parser.add_argument("--max-length", type=int, default=4096)
    parser.add_argument("--learning-rate", type=float, default=2e-5)
    parser.add_argument("--weight-decay", type=float, default=0.01)
    parser.add_argument("--lora-rank", type=int, default=16)
    parser.add_argument("--evaluate-baseline", action="store_true")
    args = parser.parse_args()
    # Require online W&B before loading the model or benchmark data.
    if not os.getenv("WANDB_API_KEY"):
        raise RuntimeError("WANDB_API_KEY is required for Qwen experiments.")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    config = {key: str(value) if isinstance(value, Path) else value for key, value in vars(args).items()}
    # Load every row from the preference training split and do not create a validation partition.
    all_rows = prepare_rows(load_rows())
    if len(all_rows) != 9000:
        raise RuntimeError(f"Expected 9,000 When2Call preference rows but found {len(all_rows)}.")
    label_counts = dict(sorted(Counter(row.label for row in all_rows).items()))
    data_fingerprint = fingerprint_rows(all_rows)
    run = wandb.init(project=os.getenv("WANDB_PROJECT", "when2call-research"), entity=os.getenv("WANDB_ENTITY"), name=args.output_dir.name, job_type="when2call-fullpool-sft", config=config | {"dataset": DATASET_NAME + ":train_pref", "train_examples": len(all_rows), "validation_examples": 0, "official_test_selection": False})
    atexit.register(run.finish)
    # Fix random sources before initializing the base model and fresh LoRA adapter.
    random.seed(args.seed)
    torch.manual_seed(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    heartbeat = args.output_dir / "heartbeat.json"
    write_heartbeat(heartbeat, "loading")
    model, tokenizer = load_model(args.model, device, args.lora_rank)
    label_ids = label_token_ids(tokenizer)
    optimizer = torch.optim.AdamW((parameter for parameter in model.parameters() if parameter.requires_grad), lr=args.learning_rate, weight_decay=args.weight_decay)
    baseline_test = None
    if args.evaluate_baseline:
        baseline_test = evaluate_black_box(model, tokenizer, label_ids, device, args.max_length, args.eval_batch_size)
        run.log({"baseline/test_accuracy": baseline_test["accuracy"], "baseline/test_macro_f1": baseline_test["macro_f1"]}, step=0)
    total_steps = len(all_rows) * args.epochs
    epoch_records = []
    losses = []
    for epoch in range(args.epochs):
        # Log every optimizer-step loss while using every preference row in each epoch.
        def log_step_loss(step: int, loss: float) -> bool:
            # Keep the test metric out of the training callback and checkpoint decisions.
            run.log({"training/optimizer_step_loss": loss}, step=step)
            return False
        epoch_loss = train_epoch(model, tokenizer, all_rows, label_ids, "sft", device, optimizer, args.max_length, args.batch_size, 0.1, args.seed + epoch, heartbeat, log_step_loss, epoch * len(all_rows))
        losses.append(epoch_loss)
        global_step = (epoch + 1) * len(all_rows)
        checkpoint_dir = args.output_dir / f"epoch-{epoch + 1:02d}"
        model.save_pretrained(checkpoint_dir)
        tokenizer.save_pretrained(checkpoint_dir)
        # Measure training fit and aggregate-only test performance after this fixed epoch.
        write_heartbeat(heartbeat, "epoch_evaluation", global_step)
        training_metrics = evaluate(model, tokenizer, all_rows, label_ids, device, args.max_length, args.eval_batch_size, heartbeat)
        test_metrics = evaluate_black_box(model, tokenizer, label_ids, device, args.max_length, args.eval_batch_size)
        record = {"epoch": epoch + 1, "step": global_step, "training_loss": epoch_loss, "training_metrics": training_metrics, "heldout_validation_metrics": None, "black_box_test_metrics": test_metrics, "checkpoint": str(checkpoint_dir)}
        epoch_records.append(record)
        run.log({"epoch": epoch + 1, "training/epoch_loss": epoch_loss, "training/accuracy": training_metrics["accuracy"], "training/macro_f1": training_metrics["macro_f1"], "test/accuracy": test_metrics["accuracy"], "test/macro_f1": test_metrics["macro_f1"]}, step=global_step)
    # Save complete provenance and aggregate metrics without per-example test outputs.
    result = {
        "experiment": "qwen25_1p5b_all_when2call_trainpref_sft",
        "purpose": "Train on all When2Call preference rows without a held-out validation split and report each fixed epoch.",
        "config": config,
        "base_model": args.model,
        "base_model_checkpoint": "Qwen/Qwen2.5-1.5B-Instruct before any task adapter training",
        "data": {"dataset": DATASET_NAME, "split": "train_pref", "examples": len(all_rows), "label_counts": label_counts, "prompt_label_fingerprint": data_fingerprint},
        "validation_metrics": None,
        "validation_omission_reason": "The user requested training on every preference row and no held-out validation split.",
        "selection_procedure": "No epoch or checkpoint was selected. The run trained a fixed number of epochs decided before test evaluation. Aggregate black-box test metrics are report-only.",
        "test_label_use": "Test labels were used only inside the evaluator to compute aggregate accuracy and macro F1. No individual test rows or predictions were saved, and test metrics did not select or stop training.",
        "baseline_black_box_test_metrics": baseline_test,
        "training_loss_by_epoch": losses,
        "epoch_records": epoch_records,
        "wandb_run_id": run.id,
        "wandb_run_url": run.url,
        "device": str(device),
        "optimizer_steps": total_steps,
    }
    (args.output_dir / "metrics.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    run.summary.update({"final_test_accuracy": epoch_records[-1]["black_box_test_metrics"]["accuracy"], "final_test_macro_f1": epoch_records[-1]["black_box_test_metrics"]["macro_f1"], "validation_used": False, "test_selection_used": False})
    write_heartbeat(heartbeat, "completed", total_steps)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    # Return a nonzero exit status when any required experiment stage fails.
    raise SystemExit(main())
