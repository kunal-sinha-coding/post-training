"""Train Qwen on When2Call preference rows or continue a saved adapter on synthetic rows.

The flow loads the requested training rows, initializes or continues a Qwen LoRA adapter, evaluates
fixed training and clean-validation samples, reports aggregate-only test metrics, and saves provenance.
Optional early stopping uses clean-validation accuracy only.
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

from experiments.clean_validation_baseline import load_sft_training_rows
from experiments.train_qwen_bfcl_original_mixture import sample_stratified
from experiments.train_qwen_bfcl_when2call import evaluate_black_box, load_labeled_rows
from experiments.train_qwen_when2call import (
    DATASET_NAME,
    ClassificationRow,
    evaluate,
    label_token_ids,
    load_model,
    load_rows,
    make_prompt,
    prepare_rows,
    response_label,
    train_epoch,
    write_heartbeat,
)
from experiments.train_when2call_jina import LABELS


def fingerprint_rows(rows: list[object]) -> str:
    """Hash formatted prompts and chosen labels without storing examples."""
    # Sort per-row hashes so the fingerprint does not depend on data iteration order.
    row_hashes = sorted(hashlib.sha256((row.prompt + "\n" + str(row.label)).encode()).hexdigest() for row in rows)
    return hashlib.sha256("\n".join(row_hashes).encode()).hexdigest()


def reorder_schema_keys(value: object, rng: random.Random) -> object:
    """Reorder JSON object keys recursively without changing schema meaning."""
    # Rebuild each object in a deterministic random key order and preserve list order.
    if isinstance(value, dict):
        keys = list(value)
        rng.shuffle(keys)
        return {key: reorder_schema_keys(value[key], rng) for key in keys}
    # Apply the same key-order transform to every schema in an array.
    if isinstance(value, list):
        return [reorder_schema_keys(item, rng) for item in value]
    # Leave scalar values unchanged.
    return value


def augment_preference_rows(rows: list[ClassificationRow], mode: str, seed: int) -> list[ClassificationRow]:
    """Create label-preserving prompt variants for the requested augmentation."""
    # Use one fixed random stream so each saved run can recreate the same variants.
    rng = random.Random(seed)
    augmented = []
    for row in rows:
        prompt = row.prompt
        # Find the serialized tool section while keeping the action instruction fixed.
        marker = "\nAvailable tools:\n"
        if marker not in prompt:
            continue
        prefix, tool_section = prompt.split(marker, 1)
        tool_text, label_suffix = tool_section.rsplit("\nAction label:", 1)
        tools = tool_text.splitlines()
        # Shuffle available tools to reduce dependence on their presentation order.
        if mode == "tool_order" and len(tools) > 1:
            original = list(tools)
            rng.shuffle(tools)
            if tools == original:
                tools = tools[1:] + tools[:1]
        # Reorder JSON schema keys while preserving all names, descriptions, and values.
        elif mode == "schema_key_order":
            reordered = []
            for tool in tools:
                try:
                    schema = json.loads(tool)
                    reordered.append(json.dumps(reorder_schema_keys(schema, rng), separators=(",", ":")))
                except (json.JSONDecodeError, TypeError):
                    reordered.append(tool)
            tools = reordered
        # Add a short neutral wrapper to vary the user-request surface form.
        elif mode == "request_context":
            question_marker = "Question: "
            if question_marker in prefix:
                prefix = prefix.replace(question_marker, "Question: The user asks for help with this request: ", 1)
        # Keep only variants that changed the model input.
        augmented_prompt = prefix + marker + "\n".join(tools) + "\nAction label:" + label_suffix
        if augmented_prompt != row.prompt:
            augmented.append(ClassificationRow(augmented_prompt, row.label, row.rejected_label))
    return augmented


def main() -> int:
    """Train on all preference rows and record fixed-epoch results."""
    # Parse fixed model, training, evaluation, and output controls.
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="Qwen/Qwen2.5-1.5B-Instruct")
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/qwen-when2call-fullpool-base-seed20261050"))
    parser.add_argument("--bfcl-data", type=Path, default=Path("data/bfcl_when2call_labeled.jsonl"))
    parser.add_argument("--include-full-bfcl", action="store_true")
    parser.add_argument("--validation-source", choices=("bfcl", "sft", "none"), default="bfcl")
    parser.add_argument("--validation-sample-size", type=int, default=500)
    parser.add_argument("--validation-seed", type=int, default=20261053)
    parser.add_argument("--training-eval-sample-size", type=int, default=500)
    parser.add_argument("--training-eval-seed", type=int, default=20261059)
    parser.add_argument("--stop-on-validation-non-improvement", action="store_true")
    parser.add_argument("--seed", type=int, default=20261050)
    parser.add_argument("--epochs", type=int, default=2)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--eval-batch-size", type=int, default=4)
    parser.add_argument("--max-length", type=int, default=4096)
    parser.add_argument("--learning-rate", type=float, default=2e-5)
    parser.add_argument("--weight-decay", type=float, default=0.01)
    parser.add_argument("--lora-rank", type=int, default=16)
    parser.add_argument("--evaluate-baseline", action="store_true")
    parser.add_argument("--test-sample-size", type=int)
    parser.add_argument("--test-sample-seed", type=int, default=20261070)
    parser.add_argument("--augmentation-mode", choices=("none", "tool_order", "schema_key_order", "request_context"), default="none")
    parser.add_argument("--augmentation-seed", type=int, default=20261066)
    parser.add_argument("--augmentation-jsonl", type=Path)
    parser.add_argument("--adapter-checkpoint", type=Path)
    parser.add_argument("--synthetic-only", action="store_true")
    args = parser.parse_args()
    # Require online W&B before loading the model or benchmark data.
    if not os.getenv("WANDB_API_KEY"):
        raise RuntimeError("WANDB_API_KEY is required for Qwen experiments.")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    config = {key: str(value) if isinstance(value, Path) else value for key, value in vars(args).items()}
    # Load only the chosen source rows so synthetic continuation pilots do not replay the 9,000 originals.
    # Avoid loading the original corpus during a synthetic-only continuation.
    preference_rows = [] if args.synthetic_only else prepare_rows(load_rows())
    if not args.synthetic_only and len(preference_rows) != 9000:
        raise RuntimeError(f"Expected 9,000 When2Call preference rows but found {len(preference_rows)}.")
    # Require both the trained adapter and one explicit synthetic pilot for this mode.
    if args.synthetic_only and (not args.adapter_checkpoint or not args.augmentation_jsonl):
        raise ValueError("Synthetic-only continuation requires --adapter-checkpoint and --augmentation-jsonl.")
    # Keep BFCL data out of the pilot path entirely.
    bfcl_train, bfcl_validation = ([], []) if args.synthetic_only else load_labeled_rows(args.bfcl_data)
    bfcl_rows = bfcl_train + bfcl_validation
    augmented_rows = augment_preference_rows(preference_rows, args.augmentation_mode, args.augmentation_seed) if args.augmentation_mode != "none" else []
    # Load cached generated prompts without changing their inherited source labels.
    if args.augmentation_jsonl:
        with args.augmentation_jsonl.open(encoding="utf-8") as handle:
            generated_rows = [json.loads(line) for line in handle if line.strip()]
        augmented_rows.extend(ClassificationRow(item["prompt"], int(item["label"]), None) for item in generated_rows)
    training_rows = (augmented_rows if args.synthetic_only else preference_rows + augmented_rows) + (bfcl_rows if args.include_full_bfcl else [])
    if not training_rows:
        raise ValueError("The selected training sources produced no rows.")
    if args.validation_source == "bfcl":
        validation_rows = bfcl_validation
    elif args.validation_source == "sft":
        # Build a fixed stratified holdout from the separate supervised training configuration.
        sft_examples = []
        for row in load_sft_training_rows():
            assistant = [message for message in row["messages"] if message["role"] == "assistant"]
            if assistant:
                label = response_label(assistant[-1]["content"])
                sft_examples.append(ClassificationRow(make_prompt(row), LABELS.index(label), None))
        validation_rows = sample_stratified(sft_examples, min(args.validation_sample_size, len(sft_examples)), args.validation_seed)
        # Retain at least one example from every class present in the source sample.
        for label in sorted({row.label for row in sft_examples} - {row.label for row in validation_rows}):
            replacement = random.Random(args.validation_seed + label).choice([row for row in sft_examples if row.label == label])
            counts = Counter(row.label for row in validation_rows)
            replace_index = max((index for index, row in enumerate(validation_rows) if counts[row.label] > 1), key=lambda index: counts[validation_rows[index].label])
            validation_rows[replace_index] = replacement
    else:
        validation_rows = []
    if args.validation_source != "none" and not validation_rows:
        raise RuntimeError("A non-empty clean validation source is required.")
    if args.stop_on_validation_non_improvement and args.validation_source == "none":
        raise ValueError("Validation-based early stopping requires a held-out validation source.")
    if args.training_eval_sample_size < 1 or args.training_eval_sample_size > 500:
        raise ValueError("Training evaluation samples must contain between 1 and 500 examples.")
    if args.validation_sample_size < 1 or args.validation_sample_size > 500:
        raise ValueError("Validation evaluation samples must contain between 1 and 500 examples.")
    training_eval_rows = sample_stratified(training_rows, min(args.training_eval_sample_size, len(training_rows)), args.training_eval_seed)
    label_counts = dict(sorted(Counter(row.label for row in training_rows).items()))
    data_fingerprint = fingerprint_rows(training_rows)
    run = wandb.init(project=os.getenv("WANDB_PROJECT", "when2call-research"), entity=os.getenv("WANDB_ENTITY"), name=args.output_dir.name, job_type="when2call-synthetic-continuation" if args.synthetic_only else "when2call-fullpool-sft-augmentation", config=config | {"dataset": "synthetic-only continuation" if args.synthetic_only else DATASET_NAME + ":train_pref" + (" + augmented preference prompts" if augmented_rows else "") + (" + BFCL" if args.include_full_bfcl else ""), "train_examples": len(training_rows), "preference_train_examples": len(preference_rows), "augmentation_mode": args.augmentation_mode if not args.augmentation_jsonl else "synthetic_pilot", "augmentation_jsonl": str(args.augmentation_jsonl) if args.augmentation_jsonl else None, "augmented_examples": len(augmented_rows), "adapter_checkpoint": str(args.adapter_checkpoint) if args.adapter_checkpoint else None, "bfcl_train_examples": len(training_rows) - len(preference_rows) - len(augmented_rows), "validation_source": args.validation_source, "validation_examples": len(validation_rows), "official_test_selection": False})
    atexit.register(run.finish)
    # Fix random sources before initializing the base model and fresh LoRA adapter.
    random.seed(args.seed)
    torch.manual_seed(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    heartbeat = args.output_dir / "heartbeat.json"
    write_heartbeat(heartbeat, "loading")
    model, tokenizer = load_model(args.model, device, args.lora_rank, str(args.adapter_checkpoint) if args.adapter_checkpoint else None)
    label_ids = label_token_ids(tokenizer)
    optimizer = torch.optim.AdamW((parameter for parameter in model.parameters() if parameter.requires_grad), lr=args.learning_rate, weight_decay=args.weight_decay)
    baseline_test = None
    baseline_validation = None
    if args.evaluate_baseline:
        baseline_validation = evaluate(model, tokenizer, validation_rows, label_ids, device, args.max_length, args.eval_batch_size, heartbeat) if validation_rows else None
        baseline_test = evaluate_black_box(model, tokenizer, label_ids, device, args.max_length, args.eval_batch_size, args.test_sample_size, args.test_sample_seed)
        run.log({"baseline/test_accuracy": baseline_test["accuracy"], "baseline/test_macro_f1": baseline_test["macro_f1"], **({"baseline/validation_accuracy": baseline_validation["accuracy"], "baseline/validation_macro_f1": baseline_validation["macro_f1"]} if baseline_validation else {})}, step=0)
    total_steps = len(training_rows) * args.epochs
    epoch_records = []
    losses = []
    best_validation_accuracy = baseline_validation["accuracy"] if baseline_validation else None
    for epoch in range(args.epochs):
        # Log every optimizer-step loss while using every preference row in each epoch.
        def log_step_loss(step: int, loss: float) -> bool:
            # Keep the test metric out of the training callback and checkpoint decisions.
            run.log({"training/optimizer_step_loss": loss}, step=step)
            return False
        epoch_loss = train_epoch(model, tokenizer, training_rows, label_ids, "sft", device, optimizer, args.max_length, args.batch_size, 0.1, args.seed + epoch, heartbeat, log_step_loss, epoch * len(training_rows))
        losses.append(epoch_loss)
        global_step = (epoch + 1) * len(training_rows)
        checkpoint_dir = args.output_dir / f"epoch-{epoch + 1:02d}"
        model.save_pretrained(checkpoint_dir)
        tokenizer.save_pretrained(checkpoint_dir)
        # Measure training and clean validation before the aggregate-only test report.
        write_heartbeat(heartbeat, "epoch_evaluation", global_step)
        training_metrics = evaluate(model, tokenizer, training_eval_rows, label_ids, device, args.max_length, args.eval_batch_size, heartbeat)
        validation_metrics = evaluate(model, tokenizer, validation_rows, label_ids, device, args.max_length, args.eval_batch_size, heartbeat) if validation_rows else None
        test_metrics = evaluate_black_box(model, tokenizer, label_ids, device, args.max_length, args.eval_batch_size, args.test_sample_size, args.test_sample_seed)
        record = {"epoch": epoch + 1, "step": global_step, "training_loss": epoch_loss, "training_metrics": training_metrics, "training_evaluation_examples": len(training_eval_rows), "training_evaluation_fingerprint": fingerprint_rows(training_eval_rows), "heldout_validation_metrics": validation_metrics, "validation_source": args.validation_source, "validation_examples": len(validation_rows), "black_box_test_metrics": test_metrics, "checkpoint": str(checkpoint_dir)}
        epoch_records.append(record)
        log_metrics = {"epoch": epoch + 1, "training/epoch_loss": epoch_loss, "training/accuracy": training_metrics["accuracy"], "training/macro_f1": training_metrics["macro_f1"], "test/accuracy": test_metrics["accuracy"], "test/macro_f1": test_metrics["macro_f1"]}
        if validation_metrics is not None:
            log_metrics.update({"validation/accuracy": validation_metrics["accuracy"], "validation/macro_f1": validation_metrics["macro_f1"]})
        run.log(log_metrics, step=global_step)
        if validation_metrics is not None and (best_validation_accuracy is None or validation_metrics["accuracy"] > best_validation_accuracy):
            best_validation_accuracy = validation_metrics["accuracy"]
        elif validation_metrics is not None and args.stop_on_validation_non_improvement:
            record["stop_reason"] = "held-out validation accuracy did not improve"
            break
    # Save complete provenance and aggregate metrics without per-example test outputs.
    result = {
        "experiment": "qwen25_1p5b_synthetic_only_continuation" if args.synthetic_only else "qwen25_1p5b_all_when2call_trainpref_sft",
        "purpose": "Continue the saved When2Call adapter using only a small synthetic pilot set." if args.synthetic_only else "Train on all When2Call preference rows, optionally with BFCL, and report each epoch.",
        "config": config,
        "base_model": args.model,
        "base_model_checkpoint": str(args.adapter_checkpoint) if args.adapter_checkpoint else "Qwen/Qwen2.5-1.5B-Instruct before any task adapter training",
        "data": {"dataset": "synthetic pilot only" if args.synthetic_only else DATASET_NAME, "split": "synthetic_pilot" if args.synthetic_only else "train_pref", "preference_examples": len(preference_rows), "augmentation_mode": args.augmentation_mode if not args.augmentation_jsonl else "synthetic_pilot", "augmentation_seed": args.augmentation_seed, "augmentation_jsonl": str(args.augmentation_jsonl) if args.augmentation_jsonl else None, "augmentation_jsonl_sha256": hashlib.sha256(args.augmentation_jsonl.read_bytes()).hexdigest() if args.augmentation_jsonl else None, "augmented_examples": len(augmented_rows), "bfcl_train_examples": len(training_rows) - len(preference_rows) - len(augmented_rows), "bfcl_file": str(args.bfcl_data), "bfcl_sha256": hashlib.sha256(args.bfcl_data.read_bytes()).hexdigest(), "label_counts": label_counts, "prompt_label_fingerprint": data_fingerprint},
        "validation_source": args.validation_source,
        "validation_examples": len(validation_rows),
        "best_validation_accuracy": best_validation_accuracy,
        "training_evaluation_examples_per_epoch": len(training_eval_rows),
        "selection_procedure": "When validation is enabled, clean held-out validation accuracy controls optional early stopping. Aggregate black-box test metrics are report-only and do not select or stop training.",
        "test_label_use": "Test labels were used only inside the evaluator to compute aggregate accuracy and macro F1. No individual test rows or predictions were saved, and test metrics did not select or stop training.",
        "baseline_black_box_test_metrics": baseline_test,
        "baseline_clean_validation_metrics": baseline_validation,
        "training_loss_by_epoch": losses,
        "epoch_records": epoch_records,
        "wandb_run_id": run.id,
        "wandb_run_url": run.url,
        "device": str(device),
        "optimizer_steps": total_steps,
    }
    (args.output_dir / "metrics.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    run.summary.update({"final_test_accuracy": epoch_records[-1]["black_box_test_metrics"]["accuracy"], "final_test_macro_f1": epoch_records[-1]["black_box_test_metrics"]["macro_f1"], "best_validation_accuracy": best_validation_accuracy, "validation_used": True, "test_selection_used": False})
    write_heartbeat(heartbeat, "completed", total_steps)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    # Return a nonzero exit status when any required experiment stage fails.
    raise SystemExit(main())
