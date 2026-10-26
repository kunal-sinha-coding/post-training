"""Train base Qwen on an equal mix of original and augmented action examples.

The flow loads the fixed BFCL split and original When2Call preference split, samples equal training
counts, trains a fresh LoRA adapter, evaluates at each 1,000-step interval and epoch end, and saves
training, held-out validation, and aggregate-only black-box test metrics.
"""
from __future__ import annotations

import argparse
import atexit
import hashlib
import json
import os
import random
from pathlib import Path

import torch
import wandb

from experiments.train_qwen_bfcl_when2call import evaluate_black_box, load_labeled_rows
from experiments.train_qwen_when2call import (
    DATASET_NAME,
    LABELS,
    ClassificationRow,
    evaluate,
    label_token_ids,
    load_model,
    load_rows,
    prepare_rows,
    split_rows,
    train_epoch,
    write_heartbeat,
)


def sample_stratified(rows: list[ClassificationRow], sample_size: int, seed: int) -> list[ClassificationRow]:
    """Draw a deterministic sample that preserves the source label proportions."""
    # Allocate the requested sample count across labels by largest remainder.
    if sample_size >= len(rows):
        return list(rows)
    groups = {label: [row for row in rows if row.label == label] for label in range(len(LABELS))}
    exact = {label: sample_size * len(group) / len(rows) for label, group in groups.items()}
    counts = {label: int(value) for label, value in exact.items()}
    remainder = sample_size - sum(counts.values())
    for label in sorted(groups, key=lambda item: (exact[item] - counts[item], -item), reverse=True)[:remainder]:
        counts[label] += 1
    # Sample within each class and shuffle the combined sample with one fixed seed.
    selected = []
    for label, group in groups.items():
        selected.extend(random.Random(seed + label).sample(group, counts[label]))
    random.Random(seed).shuffle(selected)
    return selected


def fingerprint_rows(rows: list[ClassificationRow]) -> str:
    """Hash prompt and label pairs without saving example text."""
    # Sort per-row hashes so the fingerprint does not depend on iteration order.
    hashes = sorted(hashlib.sha256((row.prompt + "\n" + str(row.label)).encode()).hexdigest() for row in rows)
    return hashlib.sha256("\n".join(hashes).encode()).hexdigest()


def run_evaluation(model: object, tokenizer: object, labels: list[int], device: torch.device, max_length: int, batch_size: int, train_rows: list[ClassificationRow], bfcl_validation: list[ClassificationRow], original_validation: list[ClassificationRow], step: int, heartbeat: Path) -> dict:
    """Measure training, both clean validation sets, and aggregate black-box test metrics."""
    # Keep test outputs aggregate-only while preserving separate source validation results.
    write_heartbeat(heartbeat, "checkpoint_evaluation", step)
    return {
        "step": step,
        "training_metrics": evaluate(model, tokenizer, train_rows, labels, device, max_length, batch_size, heartbeat),
        "bfcl_heldout_validation_metrics": evaluate(model, tokenizer, bfcl_validation, labels, device, max_length, batch_size, heartbeat),
        "original_heldout_validation_metrics": evaluate(model, tokenizer, original_validation, labels, device, max_length, batch_size, heartbeat),
        "black_box_test_metrics": evaluate_black_box(model, tokenizer, labels, device, max_length, batch_size),
    }


def main() -> int:
    """Train one base-model epoch on an exact 50/50 source mixture."""
    # Parse data, optimization, evaluation, and artifact controls before loading model weights.
    parser = argparse.ArgumentParser()
    parser.add_argument("--bfcl-data", type=Path, default=Path("data/bfcl_when2call_labeled.jsonl"))
    parser.add_argument("--bfcl-metadata", type=Path, default=Path("data/bfcl_when2call_labeled.metadata.json"))
    parser.add_argument("--model", default="Qwen/Qwen2.5-1.5B-Instruct")
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/qwen-bfcl-original-5050-base-seed20261049"))
    parser.add_argument("--seed", type=int, default=20261049)
    parser.add_argument("--original-split-seed", type=int, default=20261029)
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--eval-batch-size", type=int, default=4)
    parser.add_argument("--max-length", type=int, default=4096)
    parser.add_argument("--learning-rate", type=float, default=2e-5)
    parser.add_argument("--weight-decay", type=float, default=0.01)
    parser.add_argument("--lora-rank", type=int, default=16)
    parser.add_argument("--evaluation-steps", type=int, default=1000)
    args = parser.parse_args()
    # Require online W&B before loading training or benchmark data.
    if not os.getenv("WANDB_API_KEY"):
        raise RuntimeError("WANDB_API_KEY is required for Qwen experiments.")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    config = {key: str(value) if isinstance(value, Path) else value for key, value in vars(args).items()}
    bfcl_metadata = json.loads(args.bfcl_metadata.read_text(encoding="utf-8"))
    # Keep the original When2Call validation partition separate from its training rows.
    original_train, original_validation = split_rows(prepare_rows(load_rows()), args.original_split_seed)
    bfcl_train, bfcl_validation = load_labeled_rows(args.bfcl_data)
    if len(original_train) < len(bfcl_train):
        raise RuntimeError("The original training split is smaller than the BFCL training split.")
    original_sample = sample_stratified(original_train, len(bfcl_train), args.seed)
    # Form an exact 50/50 mix and shuffle it with the run seed.
    training_rows = list(bfcl_train) + list(original_sample)
    random.Random(args.seed).shuffle(training_rows)
    run = wandb.init(project=os.getenv("WANDB_PROJECT", "when2call-research"), entity=os.getenv("WANDB_ENTITY"), name=args.output_dir.name, job_type="bfcl-original-mixture-sft", config=config | {"bfcl_train_examples": len(bfcl_train), "original_train_examples": len(original_sample), "bfcl_validation_examples": len(bfcl_validation), "original_validation_examples": len(original_validation), "official_test_selection": False})
    atexit.register(run.finish)
    # Fix all random sources before loading the base model and new LoRA adapter.
    random.seed(args.seed)
    torch.manual_seed(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    heartbeat = args.output_dir / "heartbeat.json"
    write_heartbeat(heartbeat, "loading")
    model, tokenizer = load_model(args.model, device, args.lora_rank)
    label_ids = label_token_ids(tokenizer)
    optimizer = torch.optim.AdamW((parameter for parameter in model.parameters() if parameter.requires_grad), lr=args.learning_rate, weight_decay=args.weight_decay)
    # Measure the base model on all splits before its first optimizer update.
    baseline = run_evaluation(model, tokenizer, label_ids, device, args.max_length, args.eval_batch_size, training_rows, bfcl_validation, original_validation, 0, heartbeat)
    run.log({"baseline/training_accuracy": baseline["training_metrics"]["accuracy"], "baseline/training_macro_f1": baseline["training_metrics"]["macro_f1"], "baseline/bfcl_validation_accuracy": baseline["bfcl_heldout_validation_metrics"]["accuracy"], "baseline/bfcl_validation_macro_f1": baseline["bfcl_heldout_validation_metrics"]["macro_f1"], "baseline/original_validation_accuracy": baseline["original_heldout_validation_metrics"]["accuracy"], "baseline/original_validation_macro_f1": baseline["original_heldout_validation_metrics"]["macro_f1"], "test/base_accuracy": baseline["black_box_test_metrics"]["accuracy"], "test/base_macro_f1": baseline["black_box_test_metrics"]["macro_f1"]}, step=0)
    # Log each optimizer loss and evaluate at every 1,000 steps and at each epoch boundary.
    steps_per_epoch = (len(training_rows) + args.batch_size - 1) // args.batch_size
    total_steps = steps_per_epoch * args.epochs
    evaluations = [baseline]
    losses = []
    best_validation_accuracy = float("-inf")
    best_checkpoint = None
    for epoch in range(args.epochs):
        last_eval_step = epoch * steps_per_epoch
        def log_and_evaluate(step: int, loss: float) -> bool:
            # Record every optimizer loss and run full evaluation only at scheduled checkpoints.
            nonlocal last_eval_step, best_validation_accuracy, best_checkpoint
            run.log({"training/optimizer_step_loss": loss}, step=step)
            if step % args.evaluation_steps != 0 and step != total_steps:
                return False
            record = run_evaluation(model, tokenizer, label_ids, device, args.max_length, args.eval_batch_size, training_rows, bfcl_validation, original_validation, step, heartbeat)
            evaluations.append(record)
            checkpoint_dir = args.output_dir / f"step-{step:06d}"
            model.save_pretrained(checkpoint_dir)
            tokenizer.save_pretrained(checkpoint_dir)
            validation_accuracy = record["bfcl_heldout_validation_metrics"]["accuracy"]
            if validation_accuracy > best_validation_accuracy:
                best_validation_accuracy = validation_accuracy
                best_checkpoint = str(checkpoint_dir)
            run.log({"training/accuracy": record["training_metrics"]["accuracy"], "training/macro_f1": record["training_metrics"]["macro_f1"], "bfcl_heldout_validation/accuracy": validation_accuracy, "bfcl_heldout_validation/macro_f1": record["bfcl_heldout_validation_metrics"]["macro_f1"], "original_heldout_validation/accuracy": record["original_heldout_validation_metrics"]["accuracy"], "original_heldout_validation/macro_f1": record["original_heldout_validation_metrics"]["macro_f1"], "test/accuracy": record["black_box_test_metrics"]["accuracy"], "test/macro_f1": record["black_box_test_metrics"]["macro_f1"]}, step=step)
            last_eval_step = step
            return False
        epoch_loss = train_epoch(model, tokenizer, training_rows, label_ids, "sft", device, optimizer, args.max_length, args.batch_size, 0.1, args.seed + epoch, heartbeat, log_and_evaluate, epoch * steps_per_epoch)
        losses.append(epoch_loss)
        epoch_end_step = (epoch + 1) * steps_per_epoch
        if last_eval_step != epoch_end_step:
            record = run_evaluation(model, tokenizer, label_ids, device, args.max_length, args.eval_batch_size, training_rows, bfcl_validation, original_validation, epoch_end_step, heartbeat)
            evaluations.append(record)
            checkpoint_dir = args.output_dir / f"step-{epoch_end_step:06d}"
            model.save_pretrained(checkpoint_dir)
            tokenizer.save_pretrained(checkpoint_dir)
            validation_accuracy = record["bfcl_heldout_validation_metrics"]["accuracy"]
            if validation_accuracy > best_validation_accuracy:
                best_validation_accuracy = validation_accuracy
                best_checkpoint = str(checkpoint_dir)
            run.log({"training/accuracy": record["training_metrics"]["accuracy"], "training/macro_f1": record["training_metrics"]["macro_f1"], "bfcl_heldout_validation/accuracy": validation_accuracy, "bfcl_heldout_validation/macro_f1": record["bfcl_heldout_validation_metrics"]["macro_f1"], "original_heldout_validation/accuracy": record["original_heldout_validation_metrics"]["accuracy"], "original_heldout_validation/macro_f1": record["original_heldout_validation_metrics"]["macro_f1"], "test/accuracy": record["black_box_test_metrics"]["accuracy"], "test/macro_f1": record["black_box_test_metrics"]["macro_f1"]}, step=epoch_end_step)
    # Save one aggregate experiment record without any individual test predictions.
    final_record = evaluations[-1]
    result = {
        "experiment": "qwen25_1p5b_base_sft_bfcl_when2call_50_50",
        "purpose": "Measure the effect of mixing source-disjoint BFCL action labels with original When2Call training rows.",
        "config": config,
        "base_model": args.model,
        "base_model_checkpoint": "Qwen/Qwen2.5-1.5B-Instruct before any task adapter training",
        "data": {"bfcl_file": str(args.bfcl_data), "bfcl_sha256": hashlib.sha256(args.bfcl_data.read_bytes()).hexdigest(), "bfcl_prompt_sha256": bfcl_metadata["prompt_sha256"], "bfcl_train_examples": len(bfcl_train), "bfcl_validation_examples": len(bfcl_validation), "original_dataset": DATASET_NAME, "original_split": "train_pref", "original_split_seed": args.original_split_seed, "original_source_train_examples": len(original_train), "original_sample_examples": len(original_sample), "original_validation_examples": len(original_validation), "original_sample_fingerprint": fingerprint_rows(original_sample)},
        "source_mix": {"bfcl_fraction": len(bfcl_train) / len(training_rows), "original_when2call_fraction": len(original_sample) / len(training_rows)},
        "selection_procedure": "The BFCL split was fixed before training. A deterministic stratified sample of equal size was drawn from the original When2Call training partition. Checkpoints are selected by BFCL held-out validation accuracy. Aggregate test metrics are report-only.",
        "test_label_use": "The model never receives test labels. Test accuracy and macro F1 are computed locally for baseline and checkpoint reports only.",
        "training_loss_by_epoch": losses,
        "baseline_metrics": baseline,
        "checkpoint_evaluations": evaluations[1:],
        "best_validation_accuracy": best_validation_accuracy,
        "best_validation_checkpoint": best_checkpoint,
        "final_epoch_metrics": final_record,
        "wandb_run_id": run.id,
        "wandb_run_url": run.url,
        "device": str(device),
    }
    (args.output_dir / "metrics.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    run.summary.update({"best_bfcl_validation_accuracy": best_validation_accuracy, "best_validation_checkpoint": best_checkpoint, "test_accuracy": final_record["black_box_test_metrics"]["accuracy"], "test_macro_f1": final_record["black_box_test_metrics"]["macro_f1"], "test_selection_used": False})
    write_heartbeat(heartbeat, "completed", total_steps)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    # Return a nonzero exit status when any required experiment stage fails.
    raise SystemExit(main())
