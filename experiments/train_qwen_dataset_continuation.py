"""Continue a saved When2Call preference adapter using only new external data.

The flow loads the fixed preference-trained LoRA adapter, samples and splits one external source,
trains only on that source, evaluates clean preference validation plus aggregate-only test metrics,
and stops after two consecutive evaluation points without a clean-validation accuracy gain.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import subprocess
import sys
from pathlib import Path

import torch

from experiments.train_qwen_glaive_mix import combine_metrics, load_external_rows, sample_rows
from experiments.train_qwen_when2call import (
    DATASET_NAME,
    evaluate,
    label_token_ids,
    load_model,
    load_rows,
    prepare_rows,
    split_rows,
    train_epoch,
    write_heartbeat,
)
from experiments.train_when2call_jina import LABELS


def main() -> int:
    """Train one external dataset continuation and record every scheduled checkpoint evaluation."""
    # Parse the starting adapter, candidate source mixture, and fixed training controls.
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="Qwen/Qwen2.5-1.5B-Instruct")
    parser.add_argument("--initial-checkpoint", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--apigen-mt-sample", type=int, default=0)
    parser.add_argument("--toolace-sample", type=int, default=0)
    parser.add_argument("--hermes-singleturn-sample", type=int, default=0)
    parser.add_argument("--english100k-sample", type=int, default=0)
    parser.add_argument("--toolbench-sample", type=int, default=0)
    parser.add_argument("--narrative-sample", type=int, default=0)
    parser.add_argument("--toolalpaca-sample", type=int, default=0)
    parser.add_argument("--apibank-sample", type=int, default=0)
    parser.add_argument("--seed", type=int, default=20261047)
    parser.add_argument("--split-seed", type=int, default=20261029)
    parser.add_argument("--max-epochs", type=int, default=20)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--max-length", type=int, default=4096)
    parser.add_argument("--learning-rate", type=float, default=2e-5)
    parser.add_argument("--weight-decay", type=float, default=0.01)
    parser.add_argument("--lora-rank", type=int, default=16)
    parser.add_argument("--evaluation-steps", type=int, default=1000)
    parser.add_argument("--first-eval-test-drop-threshold", type=float, default=0.02)
    args = parser.parse_args()
    # Require a declared external source and a readable adapter before opening a W&B run.
    source_sizes = {
        "apigen_mt": args.apigen_mt_sample,
        "toolace": args.toolace_sample,
        "hermes_singleturn": args.hermes_singleturn_sample,
        "english100k": args.english100k_sample,
        "toolbench": args.toolbench_sample,
        "narrative": args.narrative_sample,
        "toolalpaca": args.toolalpaca_sample,
        "apibank": args.apibank_sample,
    }
    source_sizes = {source: size for source, size in source_sizes.items() if size > 0}
    if not source_sizes:
        parser.error("Select at least one external source sample.")
    if not args.initial_checkpoint.is_dir():
        parser.error(f"Initial adapter directory does not exist: {args.initial_checkpoint}")
    # Keep the candidate run distinct and make step loss visible throughout training.
    import wandb
    if not os.getenv("WANDB_API_KEY"):
        raise RuntimeError("WANDB_API_KEY is required for Qwen experiments.")
    source_names = {
        "apigen_mt": "Salesforce/APIGen-MT-5k",
        "toolace": "Team-ACE/ToolACE",
        "hermes_singleturn": "NousResearch/hermes-function-calling-v1:func_calling_singleturn",
        "english100k": "stindardlogic/tool-calling-english-100k",
        "toolbench": "tuandunghcmut/toolbench-v1:default/train",
        "narrative": "narrative-io/narrative-function-calling-v1:default/train",
        "toolalpaca": "tangqiaoyu/ToolAlpaca:data/train_data.json (official upstream)",
        "apibank": "liminghao1630/API-Bank:training-data/lv1-api-train.json",
    }
    dataset_names = [source_names[source] for source in source_sizes]
    args.output_dir.mkdir(parents=True, exist_ok=True)
    run = wandb.init(
        project=os.getenv("WANDB_PROJECT", "when2call-research"),
        entity=os.getenv("WANDB_ENTITY"),
        name=f"qwen-adapter-continuation-{args.output_dir.name}",
        job_type="qwen-external-data-continuation",
        config={**vars(args), "dataset": dataset_names, "training_rows_only_from_candidate": True, "official_test_labels_exposed": False},
    )
    # Load the unchanged clean preference holdout and source-specific candidate partitions.
    pref_train, pref_validation = split_rows(prepare_rows(load_rows()), args.split_seed)
    external_training_rows = []
    external_validation_rows = {}
    source_offsets = {"apigen_mt": 10, "toolace": 11, "hermes_singleturn": 13, "english100k": 14, "toolbench": 15, "narrative": 16, "toolalpaca": 17, "apibank": 18}
    for source, sample_size in source_sizes.items():
        train_rows, validation_rows = load_external_rows(source, sample_size, args.seed + source_offsets[source])
        external_training_rows.extend(train_rows)
        external_validation_rows[source] = validation_rows
    if not external_training_rows:
        raise RuntimeError("The selected source samples produced no training examples after label filtering.")
    # Initialize a trainable copy of the preference adapter and create a fresh optimizer for this source trial.
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    write_heartbeat(args.output_dir / "heartbeat.json", "model-loading")
    model, tokenizer = load_model(args.model, device, args.lora_rank, str(args.initial_checkpoint))
    model.save_pretrained(args.output_dir)
    tokenizer.save_pretrained(args.output_dir)
    token_ids = label_token_ids(tokenizer)
    optimizer = torch.optim.AdamW((parameter for parameter in model.parameters() if parameter.requires_grad), lr=args.learning_rate, weight_decay=args.weight_decay)
    baseline_metrics = json.loads((args.initial_checkpoint / "metrics.json").read_text())
    baseline_accuracy = float(baseline_metrics["development_metrics"]["accuracy"])
    baseline_test_accuracy = 0.666210295728368
    best_accuracy = baseline_accuracy
    best_checkpoint = str(args.initial_checkpoint)
    best_step = 0
    best_test_metrics = {"accuracy": 0.666210295728368, "macro_f1": 0.4924675618502121}
    evaluation_count = 0
    previous_test_accuracy = baseline_test_accuracy
    stop_reason = None
    stop_training = False
    last_step = 0
    last_evaluation = None
    evaluated_steps = set()
    checkpoint_log = args.output_dir / "checkpoint_evaluations.jsonl"
    train_probe = sample_rows(external_training_rows, 1000, args.seed + 4)

    def evaluate_checkpoint(step: int) -> bool:
        # Measure all required evidence and apply the user's aggregate-test continuation rule.
        nonlocal best_accuracy, best_checkpoint, best_step, best_test_metrics, evaluation_count, previous_test_accuracy, last_evaluation, stop_training, stop_reason
        if step in evaluated_steps:
            return stop_training
        evaluated_steps.add(step)
        directory = args.output_dir / "checkpoints" / f"step-{step:08d}"
        directory.mkdir(parents=True, exist_ok=True)
        model.save_pretrained(directory)
        tokenizer.save_pretrained(directory)
        train_metrics = evaluate(model, tokenizer, train_probe, token_ids, device, args.max_length, args.batch_size, args.output_dir / "heartbeat.json")
        pref_metrics = evaluate(model, tokenizer, pref_validation, token_ids, device, args.max_length, args.batch_size, args.output_dir / "heartbeat.json")
        external_metrics = {source: evaluate(model, tokenizer, rows, token_ids, device, args.max_length, args.batch_size, args.output_dir / "heartbeat.json") for source, rows in external_validation_rows.items()}
        aggregate_validation = combine_metrics([pref_metrics, *external_metrics.values()])
        # Run the isolated aggregate-only test evaluator without loading labels into this training process.
        model.to("cpu")
        test_dir = args.output_dir / "checkpoint-tests" / f"step-{step:08d}"
        test_command = [sys.executable, "-u", "-m", "experiments.evaluate_qwen_when2call_test", "--model", args.model, "--checkpoint", str(directory), "--output-dir", str(test_dir), "--lora-rank", str(args.lora_rank), "--max-length", str(args.max_length), "--batch-size", "1"]
        subprocess.run(test_command, check=True)
        test_metrics = json.loads((test_dir / "metrics.json").read_text())["official_test_metrics"]
        model.to(device)
        current_test_accuracy = float(test_metrics["accuracy"])
        if evaluation_count == 0:
            test_delta = current_test_accuracy - baseline_test_accuracy
            stop_training = test_delta <= -args.first_eval_test_drop_threshold
            stop_reason = "first evaluation was at least the configured threshold below the starting checkpoint" if stop_training else None
        else:
            test_delta = current_test_accuracy - previous_test_accuracy
            stop_training = current_test_accuracy < previous_test_accuracy
            stop_reason = "aggregate test accuracy fell from the previous evaluation" if stop_training else None
        evaluation_count += 1
        previous_test_accuracy = current_test_accuracy
        record = {
            "step": step,
            "epoch": math.ceil(step / max(1, math.ceil(len(external_training_rows) / args.batch_size))),
            "checkpoint": str(directory),
            "training_metrics": train_metrics,
            "preference_validation_metrics": pref_metrics,
            "source_validation_metrics": external_metrics,
            "aggregate_validation_metrics": aggregate_validation,
            "aggregate_black_box_test_metrics_report_only": test_metrics,
            "test_accuracy_change_from_comparison_point": test_delta,
            "test_stopping_rule": "evaluation 1 stops at >= configured drop from starting checkpoint; evaluation 2 onward stops at any decrease from the prior evaluation",
            "test_stop_triggered": stop_training,
            "test_stop_reason": stop_reason,
            "test_labels_exposed": False,
        }
        with checkpoint_log.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record) + "\n")
        # Compare only clean preference-validation accuracy with the fixed starting checkpoint.
        improved = pref_metrics["accuracy"] > best_accuracy
        if improved:
            best_accuracy = pref_metrics["accuracy"]
            best_checkpoint = str(directory)
            best_step = step
            best_test_metrics = test_metrics
            shutil.copy2(directory / "adapter_config.json", args.output_dir / "adapter_config.json")
            shutil.copy2(directory / "adapter_model.safetensors", args.output_dir / "adapter_model.safetensors")
            shutil.copy2(directory / "README.md", args.output_dir / "README.md") if (directory / "README.md").exists() else None
            (args.output_dir / "best_validation_checkpoint.json").write_text(json.dumps({"step": step, "accuracy": best_accuracy, "checkpoint": best_checkpoint}, indent=2) + "\n")
        last_evaluation = record
        run.log({"evaluation/step": step, "training/accuracy": train_metrics["accuracy"], "training/macro_f1": train_metrics["macro_f1"], "validation/preference_accuracy": pref_metrics["accuracy"], "validation/preference_macro_f1": pref_metrics["macro_f1"], "validation/aggregate_accuracy": aggregate_validation["accuracy"], "validation/aggregate_macro_f1": aggregate_validation["macro_f1"], "test/aggregate_accuracy_report_only": test_metrics["accuracy"], "test/aggregate_macro_f1_report_only": test_metrics["macro_f1"], "stopping/test_accuracy_change": test_delta, "stopping/triggered": stop_training}, step=step)
        write_heartbeat(args.output_dir / "heartbeat.json", "evaluation", step)
        return stop_training

    def step_callback(step: int, loss: float) -> bool:
        # Log each optimizer loss and evaluate on every 1,000th update when it comes before epoch end.
        nonlocal last_step
        last_step = step
        run.log({"training/step_loss": loss}, step=step)
        if step % args.evaluation_steps == 0:
            return evaluate_checkpoint(step)
        return False

    # Train only candidate-source rows and stop when the aggregate-test continuation rule triggers.
    losses = []
    steps_per_epoch = math.ceil(len(external_training_rows) / args.batch_size)
    for epoch in range(args.max_epochs):
        start_step = epoch * steps_per_epoch
        losses.append(train_epoch(model, tokenizer, external_training_rows, token_ids, "sft", device, optimizer, args.max_length, args.batch_size, 0.1, args.seed + epoch, args.output_dir / "heartbeat.json", step_callback, start_step))
        if stop_training:
            break
        epoch_end = start_step + steps_per_epoch
        last_step = epoch_end
        if epoch_end not in evaluated_steps:
            if evaluate_checkpoint(epoch_end):
                break
    # Preserve full setup, selected clean-validation checkpoint, all evaluation evidence, and the stopping reason.
    final_metrics = {
        "model": args.model,
        "initial_checkpoint": str(args.initial_checkpoint),
        "training_sources": dataset_names,
        "training_rows_only_from_candidate": True,
        "training_examples": len(external_training_rows),
        "preference_validation_examples": len(pref_validation),
        "source_validation_metrics": last_evaluation["source_validation_metrics"] if last_evaluation else {},
        "train_metrics": last_evaluation["training_metrics"] if last_evaluation else {},
        "development_metrics": last_evaluation["preference_validation_metrics"] if last_evaluation else {},
        "aggregate_validation_metrics": last_evaluation["aggregate_validation_metrics"] if last_evaluation else {},
        "official_test_metrics": last_evaluation["aggregate_black_box_test_metrics_report_only"] if last_evaluation else {},
        "test_metrics_are_report_only": True,
        "test_labels_exposed": False,
        "best_validation_accuracy": best_accuracy,
        "best_validation_checkpoint": best_checkpoint,
        "best_validation_step": best_step,
        "baseline_validation_accuracy": baseline_accuracy,
        "baseline_test_metrics_report_only": {"accuracy": 0.666210295728368, "macro_f1": 0.4924675618502121},
        "optimizer_steps": last_step,
        "epochs_requested_maximum": args.max_epochs,
        "test_evaluation_count": evaluation_count,
        "stopped_by_test_accuracy_rule": stop_training,
        "test_stop_reason": stop_reason,
        "losses_by_epoch": losses,
        "checkpoint_evaluations_path": str(checkpoint_log),
        "wandb_run_id": run.id,
        "wandb_run_url": run.url,
    }
    (args.output_dir / "metrics.json").write_text(json.dumps(final_metrics, indent=2) + "\n")
    run.summary.update({"status": "completed", "training_examples": len(external_training_rows), "best_validation_accuracy": best_accuracy, "best_validation_step": best_step, "optimizer_steps": last_step, "test_accuracy_report_only": final_metrics["official_test_metrics"].get("accuracy")})
    write_heartbeat(args.output_dir / "heartbeat.json", "completed", last_step)
    run.finish()
    print(json.dumps(final_metrics, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
