"""Train Qwen SFT on preference data with optional filtered Glaive and When2Call SFT examples.

The flow samples each training source deterministically, creates separate source validation
partitions, trains a fresh LoRA adapter, and records training and clean validation metrics.
The official test split is never loaded here.
"""
from __future__ import annotations

import argparse
import atexit
import json
import os
import random
import re
import subprocess
import sys
from pathlib import Path

import torch
from datasets import load_dataset

from experiments.clean_validation_glaive import sample_glaive_examples
from experiments.clean_validation_baseline import load_sft_training_rows
from experiments.train_qwen_when2call import (
    ClassificationRow,
    DATASET_NAME,
    evaluate,
    label_token_ids,
    load_model,
    load_rows,
    make_prompt,
    prepare_rows,
    split_rows,
    train_epoch,
    write_heartbeat,
)
from experiments.train_when2call_jina import LABELS, LABEL_TO_ID, response_label


def sample_rows(rows: list[ClassificationRow], sample_size: int, seed: int) -> list[ClassificationRow]:
    # Select a reproducible training diagnostic or validation subset without changing source labels.
    if sample_size <= 0 or sample_size >= len(rows):
        return list(rows)
    return random.Random(seed).sample(rows, sample_size)


def combine_metrics(metrics: list[dict]) -> dict:
    # Merge source-specific confusion matrices into one declared aggregate validation result.
    matrix = [[0 for _ in LABELS] for _ in LABELS]
    examples = 0
    correct = 0
    for item in metrics:
        examples += item["examples"]
        correct += round(item["accuracy"] * item["examples"])
        for row_index, row in enumerate(item["confusion_matrix"]):
            for column_index, value in enumerate(row):
                matrix[row_index][column_index] += value
    f1_values = []
    for label in range(len(LABELS)):
        true_positive = matrix[label][label]
        false_positive = sum(matrix[index][label] for index in range(len(LABELS)) if index != label)
        false_negative = sum(matrix[label][index] for index in range(len(LABELS)) if index != label)
        precision = true_positive / max(1, true_positive + false_positive)
        recall = true_positive / max(1, true_positive + false_negative)
        f1_values.append(2 * precision * recall / max(1e-12, precision + recall))
    return {"accuracy": correct / max(1, examples), "macro_f1": sum(f1_values) / len(f1_values), "confusion_matrix": matrix, "examples": examples}


def prepare_glaive_rows(sample_size: int, seed: int, label_filter: str) -> list[ClassificationRow]:
    # Convert sampled Glaive decisions to the existing Qwen action prompt.
    examples = sample_glaive_examples(sample_size, seed)
    # Keep only the requested label when the experiment tests a cleaner source subset.
    if label_filter != "all":
        examples = [item for item in examples if LABELS[item.label] == label_filter]
    return [ClassificationRow(make_prompt({"messages": [{"role": "user", "content": item.text}], "tools": []}), item.label, None) for item in examples]


def prepare_sft_rows(sample_size: int, seed: int) -> list[ClassificationRow]:
    # Convert a deterministic sample of in-domain SFT responses to Qwen action rows.
    if sample_size <= 0:
        return []
    rows = load_sft_training_rows()
    examples = []
    for row in rows:
        assistant_messages = [message for message in row["messages"] if message["role"] == "assistant"]
        if not assistant_messages:
            continue
        label = LABEL_TO_ID[response_label(assistant_messages[-1]["content"])]
        if label != LABEL_TO_ID["direct"]:
            examples.append(ClassificationRow(make_prompt(row), label, None))
    random.Random(seed).shuffle(examples)
    return examples[:sample_size]


def external_message_role(message: dict) -> str:
    # Normalize common chat dataset roles before extracting the first assistant decision.
    role = str(message.get("from", message.get("role", ""))).lower()
    return {"human": "user", "user": "user", "gpt": "assistant", "assistant": "assistant", "tool": "tool", "function": "tool"}.get(role, role)


def external_message_text(message: dict) -> str:
    # Read the message text from either common conversation field without retaining source metadata.
    return str(message.get("value", message.get("content", ""))).strip()


def external_decision_label(response: str) -> str:
    # Detect common textual tool-call formats before applying the shared response label heuristic.
    if re.search(r"(?is)<(?:tool_call|function_call|functioncall)|functioncall|function_call|tool_call|^\s*\[[^\]\n]+\([^\n]*\)\]|\"name\"\s*:", response):
        return "tool_call"
    return response_label(response)


def external_prompt(row: dict, question: str) -> str:
    # Preserve dataset instructions and tool schemas while asking for the benchmark action label.
    system = str(row.get("system", "")).strip()
    tools = str(row.get("tools", "")).strip()
    return "Classify the required assistant action. Return exactly one label: A, B, C, or D.\nA = direct answer.\nB = tool call.\nC = request for more information.\nD = cannot answer.\n\n" + ("Task instructions:\n" + system + "\n\n" if system else "") + ("Available tools:\n" + tools + "\n\n" if tools else "Available tools: none\n\n") + "Question: " + question + "\nAction label:"


def external_conversation_example(row: dict, source_id: str) -> ClassificationRow | None:
    # Convert the first user turn and its first assistant action into one conservative decision example.
    if source_id.startswith("xlam_irr-"):
        # Treat an empty answer list as no usable tool answer and record it as cannot_answer.
        answers = row.get("answers", "[]")
        try:
            answers = json.loads(answers) if isinstance(answers, str) else answers
        except json.JSONDecodeError:
            answers = []
        label_name = "cannot_answer" if not answers else "tool_call"
        return ClassificationRow(external_prompt({"tools": row.get("tools", "")}, str(row.get("query", ""))), LABEL_TO_ID[label_name], None)
    messages = row.get("conversations", row.get("messages", []))
    question = ""
    response_parts = []
    for message in messages:
        role = external_message_role(message)
        text = external_message_text(message)
        if role == "user":
            if question:
                break
            question = text
        elif role == "assistant" and question:
            response_parts.append(text)
        elif role == "tool" and question and response_parts:
            continue
    if not question or not response_parts:
        return None
    response = "\n".join(response_parts)
    label = LABEL_TO_ID[external_decision_label(response)]
    return ClassificationRow(external_prompt(row, question), label, None)


def load_external_rows(source: str, sample_size: int, seed: int) -> tuple[list[ClassificationRow], list[ClassificationRow]]:
    # Reservoir-sample source conversations, then split by conversation before extracting decision labels.
    source_config = {"apigen_mt": ("Salesforce/APIGen-MT-5k", "default"), "toolace": ("Team-ACE/ToolACE", "default"), "xlam_irr": ("MadeAgents/xlam-irrelevance-7.5k", "default"), "hermes_singleturn": ("NousResearch/hermes-function-calling-v1", "func_calling_singleturn"), "english100k": ("stindardlogic/tool-calling-english-100k", "default")}
    dataset_name, config = source_config[source]
    reservoir = []
    rng = random.Random(seed)
    seen = 0
    for row in load_dataset(dataset_name, config, split="train", streaming=True):
        seen += 1
        if len(reservoir) < sample_size:
            reservoir.append(dict(row))
        else:
            replacement = rng.randrange(seen)
            if replacement < sample_size:
                reservoir[replacement] = dict(row)
    rng.shuffle(reservoir)
    validation_count = max(1, round(len(reservoir) * 0.2)) if reservoir else 0
    validation_docs = reservoir[:validation_count]
    training_docs = reservoir[validation_count:]
    training_rows = [example for index, row in enumerate(training_docs) if (example := external_conversation_example(row, f"{source}-train-{index}")) is not None and LABELS[example.label] != "direct"]
    validation_rows = [example for index, row in enumerate(validation_docs) if (example := external_conversation_example(row, f"{source}-validation-{index}")) is not None]
    return training_rows, validation_rows


def main() -> int:
    # Freeze dataset, split, and optimization settings before initializing the tracked run.
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="Qwen/Qwen2.5-1.5B-Instruct")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--glaive-sample", type=int, default=1000)
    parser.add_argument("--sft-sample", type=int, default=0)
    parser.add_argument("--apigen-mt-sample", type=int, default=0)
    parser.add_argument("--toolace-sample", type=int, default=0)
    parser.add_argument("--xlam-irrelevance-sample", type=int, default=0)
    parser.add_argument("--hermes-singleturn-sample", type=int, default=0)
    parser.add_argument("--english100k-sample", type=int, default=0)
    parser.add_argument("--glaive-label", choices=("all", *LABELS), default="all")
    parser.add_argument("--seed", type=int, default=20261028)
    parser.add_argument("--split-seed", type=int, default=20261028)
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--max-length", type=int, default=4096)
    parser.add_argument("--learning-rate", type=float, default=2e-5)
    parser.add_argument("--weight-decay", type=float, default=0.01)
    parser.add_argument("--lora-rank", type=int, default=16)
    parser.add_argument("--checkpoint-eval-steps", type=int, default=0)
    parser.add_argument("--training-log-steps", type=int, default=1)
    parser.add_argument("--checkpoint-glaive-validation-size", type=int, default=1000)
    parser.add_argument("--train-metrics-sample-size", type=int, default=0)
    parser.add_argument("--checkpoint-test-evaluation", action="store_true")
    parser.add_argument("--final-test-evaluation", action="store_true")
    args = parser.parse_args()
    # Require a positive logging interval so the optimizer callback can schedule live loss points.
    if args.training_log_steps < 1:
        parser.error("--training-log-steps must be at least 1.")
    dataset_names = [DATASET_NAME + ":train_pref", "glaiveai/glaive-function-calling-v2"]
    if args.sft_sample > 0:
        dataset_names.append(DATASET_NAME + ":train_sft")
    if args.apigen_mt_sample > 0:
        dataset_names.append("Salesforce/APIGen-MT-5k")
    if args.toolace_sample > 0:
        dataset_names.append("Team-ACE/ToolACE")
    if args.xlam_irrelevance_sample > 0:
        dataset_names.append("MadeAgents/xlam-irrelevance-7.5k")
    if args.hermes_singleturn_sample > 0:
        dataset_names.append("NousResearch/hermes-function-calling-v1:func_calling_singleturn")
    # Register the source so its identity is recorded in the experiment metadata.
    if args.english100k_sample > 0:
        dataset_names.append("stindardlogic/tool-calling-english-100k")
    import wandb
    if not os.getenv("WANDB_API_KEY"):
        raise RuntimeError("WANDB_API_KEY is required for Qwen experiments.")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    run = wandb.init(
        project=os.getenv("WANDB_PROJECT", "when2call-research"),
        entity=os.getenv("WANDB_ENTITY"),
        name=f"qwen-glaive{args.glaive_sample}-pref-full-{args.output_dir.name}",
        job_type="qwen-when2call-clean-validation",
        config={**vars(args), "dataset": dataset_names, "glaive_direct_filtered": True, "official_test_loaded": False},
    )
    atexit.register(run.finish)
    random.seed(args.seed)
    torch.manual_seed(args.seed)
    try:
        # Split the full preference source and Glaive source independently to preserve source-specific validation.
        pref_train, pref_validation = split_rows(prepare_rows(load_rows()), args.split_seed)
        glaive_rows = prepare_glaive_rows(args.glaive_sample, args.seed + 1, args.glaive_label)
        glaive_train, glaive_validation = split_rows(glaive_rows, args.split_seed + 1)
        checkpoint_glaive_validation = sample_rows(glaive_validation, args.checkpoint_glaive_validation_size, args.split_seed + 3)
        sft_rows = prepare_sft_rows(args.sft_sample, args.seed + 2)
        sft_train, sft_validation = split_rows(sft_rows, args.split_seed + 2) if sft_rows else ([], [])
        external_training_rows = []
        external_validation_rows = {}
        source_offsets = {"apigen_mt": 10, "toolace": 11, "xlam_irr": 12, "hermes_singleturn": 13, "english100k": 14}
        for source, sample_size in (("apigen_mt", args.apigen_mt_sample), ("toolace", args.toolace_sample), ("xlam_irr", args.xlam_irrelevance_sample), ("hermes_singleturn", args.hermes_singleturn_sample), ("english100k", args.english100k_sample)):
            if sample_size > 0:
                source_train, source_validation = load_external_rows(source, sample_size, args.seed + source_offsets[source])
                external_training_rows.extend(source_train)
                external_validation_rows[source] = source_validation
        training_rows = pref_train + glaive_train + sft_train + external_training_rows
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        write_heartbeat(args.output_dir / "heartbeat.json", "model-loading")
        model, tokenizer = load_model(args.model, device, args.lora_rank)
        token_ids = label_token_ids(tokenizer)
        optimizer = torch.optim.AdamW((parameter for parameter in model.parameters() if parameter.requires_grad), lr=args.learning_rate, weight_decay=args.weight_decay)
        losses = []
        # Save and score each scheduled intermediate adapter on held-out source validation.
        checkpoint_history = args.output_dir / "checkpoint_validation.jsonl"
        checkpoint_training_rows = sample_rows(training_rows, args.train_metrics_sample_size, args.seed + 4)
        best_checkpoint = {"accuracy": -1.0, "path": None, "step": None}
        def checkpoint_callback(step: int, step_loss: float) -> None:
            # Log optimizer loss and evaluate scheduled checkpoints without using test scores for selection.
            checkpoint_due = args.checkpoint_eval_steps > 0 and step % args.checkpoint_eval_steps == 0
            if step % args.training_log_steps != 0 and not checkpoint_due:
                return
            checkpoint_log = {"training/step_loss": step_loss}
            if not checkpoint_due:
                run.log(checkpoint_log, step=step)
                return
            checkpoint_dir = args.output_dir / "checkpoints" / f"step-{step:08d}"
            checkpoint_dir.mkdir(parents=True, exist_ok=True)
            model.save_pretrained(checkpoint_dir)
            tokenizer.save_pretrained(checkpoint_dir)
            train_checkpoint_metrics = evaluate(model, tokenizer, checkpoint_training_rows, token_ids, device, args.max_length, args.batch_size, args.output_dir / "heartbeat.json")
            pref_checkpoint_metrics = evaluate(model, tokenizer, pref_validation, token_ids, device, args.max_length, args.batch_size, args.output_dir / "heartbeat.json")
            glaive_checkpoint_metrics = evaluate(model, tokenizer, checkpoint_glaive_validation, token_ids, device, args.max_length, args.batch_size, args.output_dir / "heartbeat.json")
            external_checkpoint_metrics = {source: evaluate(model, tokenizer, rows, token_ids, device, args.max_length, args.batch_size, args.output_dir / "heartbeat.json") for source, rows in external_validation_rows.items()}
            aggregate_checkpoint_metrics = combine_metrics([pref_checkpoint_metrics, glaive_checkpoint_metrics, *external_checkpoint_metrics.values()])
            checkpoint_test_metrics = None
            test_output_dir = args.output_dir / "checkpoint-tests" / f"step-{step:08d}"
            if args.checkpoint_test_evaluation:
                # Move training weights off the GPU while the isolated aggregate-only test evaluator runs.
                model.to("cpu")
                test_command = [sys.executable, "-u", "-m", "experiments.evaluate_qwen_when2call_test", "--model", args.model, "--checkpoint", str(checkpoint_dir), "--output-dir", str(test_output_dir), "--lora-rank", str(args.lora_rank), "--max-length", str(args.max_length), "--batch-size", "1"]
                subprocess.run(test_command, check=True)
                test_result = json.loads((test_output_dir / "metrics.json").read_text(encoding="utf-8"))
                checkpoint_test_metrics = test_result["official_test_metrics"]
                model.to(device)
            checkpoint_record = {"step": step, "checkpoint": str(checkpoint_dir), "validation_source": "When2Call train_pref plus fixed held-out Glaive and external source samples", "training_probe_metrics": train_checkpoint_metrics, "preference_validation_metrics": pref_checkpoint_metrics, "glaive_validation_metrics": glaive_checkpoint_metrics, "external_validation_metrics": external_checkpoint_metrics, "aggregate_validation_metrics": aggregate_checkpoint_metrics, "aggregate_black_box_test_metrics": checkpoint_test_metrics, "test_measurement_only": True, "official_test_labels_exposed": False}
            with checkpoint_history.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(checkpoint_record) + "\n")
            checkpoint_log.update({"checkpoint/step": step, "checkpoint/training_probe_accuracy": train_checkpoint_metrics["accuracy"], "checkpoint/training_probe_macro_f1": train_checkpoint_metrics["macro_f1"], "checkpoint/preference_validation_accuracy": pref_checkpoint_metrics["accuracy"], "checkpoint/preference_validation_macro_f1": pref_checkpoint_metrics["macro_f1"], "checkpoint/glaive_validation_accuracy": glaive_checkpoint_metrics["accuracy"], "checkpoint/glaive_validation_macro_f1": glaive_checkpoint_metrics["macro_f1"], "checkpoint/aggregate_validation_accuracy": aggregate_checkpoint_metrics["accuracy"], "checkpoint/aggregate_validation_macro_f1": aggregate_checkpoint_metrics["macro_f1"]})
            if checkpoint_test_metrics is not None:
                checkpoint_log.update({"checkpoint/aggregate_test_accuracy_report_only": checkpoint_test_metrics["accuracy"], "checkpoint/aggregate_test_macro_f1_report_only": checkpoint_test_metrics["macro_f1"]})
            for source, metrics in external_checkpoint_metrics.items():
                checkpoint_log.update({f"checkpoint/{source}_validation_accuracy": metrics["accuracy"], f"checkpoint/{source}_validation_macro_f1": metrics["macro_f1"]})
            run.log(checkpoint_log, step=step)
            if pref_checkpoint_metrics["accuracy"] > best_checkpoint["accuracy"]:
                best_checkpoint.update({"accuracy": pref_checkpoint_metrics["accuracy"], "selection_metric": "preference_validation_accuracy", "path": str(checkpoint_dir), "step": step})
                best_dir = args.output_dir / "best-validation-checkpoint"
                best_dir.mkdir(parents=True, exist_ok=True)
                model.save_pretrained(best_dir)
                tokenizer.save_pretrained(best_dir)
                (args.output_dir / "best-validation-checkpoint.json").write_text(json.dumps(best_checkpoint, indent=2) + "\n", encoding="utf-8")

        # Train a fresh adapter for the requested epochs over every selected source.
        for epoch in range(args.epochs):
            losses.append(train_epoch(model, tokenizer, training_rows, token_ids, "sft", device, optimizer, args.max_length, args.batch_size, 0.1, args.seed + epoch, args.output_dir / "heartbeat.json", checkpoint_callback, epoch * ((len(training_rows) + args.batch_size - 1) // args.batch_size)))
        total_optimizer_steps = args.epochs * ((len(training_rows) + args.batch_size - 1) // args.batch_size)
        if args.checkpoint_eval_steps > 0 and total_optimizer_steps % args.checkpoint_eval_steps:
            checkpoint_callback(total_optimizer_steps)
        # Measure training and each source-specific clean validation partition.
        training_metrics_rows = checkpoint_training_rows
        train_metrics = evaluate(model, tokenizer, training_metrics_rows, token_ids, device, args.max_length, args.batch_size, args.output_dir / "heartbeat.json")
        pref_metrics = evaluate(model, tokenizer, pref_validation, token_ids, device, args.max_length, args.batch_size, args.output_dir / "heartbeat.json")
        glaive_metrics = evaluate(model, tokenizer, checkpoint_glaive_validation, token_ids, device, args.max_length, args.batch_size, args.output_dir / "heartbeat.json")
        sft_metrics = evaluate(model, tokenizer, sft_validation, token_ids, device, args.max_length, args.batch_size, args.output_dir / "heartbeat.json") if sft_validation else None
        external_metrics = {source: evaluate(model, tokenizer, rows, token_ids, device, args.max_length, args.batch_size, args.output_dir / "heartbeat.json") for source, rows in external_validation_rows.items()}
        model.save_pretrained(args.output_dir)
        tokenizer.save_pretrained(args.output_dir)
        best_test_metrics = None
        if best_checkpoint["step"] is not None and args.checkpoint_test_evaluation:
            best_test_path = args.output_dir / "checkpoint-tests" / f"step-{best_checkpoint['step']:08d}" / "metrics.json"
            best_test_metrics = json.loads(best_test_path.read_text(encoding="utf-8"))["official_test_metrics"]
        if args.final_test_evaluation:
            # Evaluate the saved end-of-epoch adapter once after training and clean validation finish.
            model.to("cpu")
            final_test_dir = args.output_dir / "final-test"
            test_command = [sys.executable, "-u", "-m", "experiments.evaluate_qwen_when2call_test", "--model", args.model, "--checkpoint", str(args.output_dir), "--output-dir", str(final_test_dir), "--lora-rank", str(args.lora_rank), "--max-length", str(args.max_length), "--batch-size", "1"]
            subprocess.run(test_command, check=True)
            best_test_metrics = json.loads((final_test_dir / "metrics.json").read_text(encoding="utf-8"))["official_test_metrics"]
        # Persist source metrics, checkpoint history, and aggregate-only benchmark reports.
        config = {key: str(value) if isinstance(value, Path) else value for key, value in vars(args).items()}
        metadata = {
            "model": args.model,
            "objective": "sft",
            "dataset": dataset_names,
            "official_test_loaded": False,
            "glaive_direct_filtered": True,
            "glaive_label_filter": args.glaive_label,
            "preference_training_examples": len(pref_train),
            "preference_validation_examples": len(pref_validation),
            "glaive_training_examples": len(glaive_train),
            "glaive_validation_examples": len(glaive_validation),
            "glaive_validation_metrics_examples": len(checkpoint_glaive_validation),
            "glaive_sampled_decision_points": len(glaive_rows),
            "sft_training_examples": len(sft_train),
            "sft_validation_examples": len(sft_validation),
            "train_examples": len(training_rows),
            "train_metrics_examples": len(training_metrics_rows),
            "train_metrics": train_metrics,
            "preference_validation_metrics": pref_metrics,
            "glaive_validation_metrics": glaive_metrics,
            "sft_validation_metrics": sft_metrics,
            "external_validation_metrics": external_metrics,
            "external_training_examples": len(external_training_rows),
            "aggregate_validation_metrics": combine_metrics([pref_metrics, glaive_metrics] + ([sft_metrics] if sft_metrics else []) + list(external_metrics.values())),
            "checkpoint_validation_path": str(checkpoint_history) if checkpoint_history.exists() else None,
            "best_validation_checkpoint": best_checkpoint if best_checkpoint["path"] else None,
            "checkpoint_test_evaluation": args.checkpoint_test_evaluation,
            "official_test_loaded": args.checkpoint_test_evaluation or args.final_test_evaluation,
            "official_test_metrics": best_test_metrics or {},
            "official_test_metrics_checkpoint": best_checkpoint["path"] if args.checkpoint_test_evaluation and best_test_metrics else str(args.output_dir) if args.final_test_evaluation and best_test_metrics else None,
            "test_metrics_are_report_only": True,
            "losses": losses,
            "label_order": LABELS,
            "label_tokens": token_ids,
            "config": config,
            "device": str(device),
            "wandb_run_id": run.id,
            "wandb_run_url": run.url,
        }
        (args.output_dir / "metrics.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
        run.summary.update({"status": "completed", "train_accuracy": train_metrics["accuracy"], "pref_validation_accuracy": pref_metrics["accuracy"], "glaive_validation_accuracy": glaive_metrics["accuracy"], "sft_validation_accuracy": sft_metrics["accuracy"] if sft_metrics else None, "test_accuracy_report_only": best_test_metrics["accuracy"] if best_test_metrics else None, "test_macro_f1_report_only": best_test_metrics["macro_f1"] if best_test_metrics else None, "output_dir": str(args.output_dir)})
        write_heartbeat(args.output_dir / "heartbeat.json", "completed")
        print(json.dumps({"train": train_metrics, "preference_validation": pref_metrics, "glaive_validation": glaive_metrics, "sft_validation": sft_metrics}, indent=2))
    except BaseException as error:
        run.summary.update({"status": "failed", "error": repr(error)})
        write_heartbeat(args.output_dir / "heartbeat.json", "failed")
        raise
    finally:
        run.finish()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
