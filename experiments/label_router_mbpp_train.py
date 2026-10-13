# This script builds the repository training pool, labels each task with one greedy Qwen completion, and saves prompts, outputs, and pass labels.
# It combines the MBPP train, validation, and test splits used by this repository.
# It removes every canonical EvalPlus task ID and every matching task description before generation.
# It runs one temperature-zero completion per remaining task, scores the original MBPP assertions, and writes a router dataset.

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from data import _normalize_task_text, _task_description_from_prompt, format_tests, load_mbpp
from experiments.run_qwen_official_greedy_eval import generate_completions
from sandbox import score_completion_batch, wrap_qwen_continuation


# Load all configured MBPP source splits and exclude the canonical EvalPlus task set.
def load_training_records() -> tuple[list[dict[str, Any]], int]:
    # Build the same combined source pool and overlap filters used by repository training.
    source_rows = [row for split in ("train", "validation", "test") for row in load_mbpp(split=split)]
    from evalplus.data import get_mbpp_plus

    evalplus_rows = get_mbpp_plus()
    evalplus_ids = {str(int(task_id.split("/")[-1])) for task_id in evalplus_rows}
    evalplus_texts = {
        normalized_text
        for record in evalplus_rows.values()
        if (normalized_text := _normalize_task_text(_task_description_from_prompt(record.get("prompt", ""))))
    }
    training_rows = [
        row
        for row in source_rows
        if str(row["task_id"]) not in evalplus_ids
        and _normalize_task_text(row["task_text"]) not in evalplus_texts
    ]
    if len({str(row["task_id"]) for row in training_rows}) != len(training_rows):
        raise ValueError("The filtered MBPP training pool contains duplicate task IDs.")
    return training_rows, len(source_rows)


# Run one greedy completion for every repository training task and save the binary targets.
def main() -> None:
    # Parse the base checkpoint and output directory for the complete labeling run.
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, default=Path("outputs/evalplus-pass16-mbpphard10x1009-seed42-20261011/base-model"))
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/router-mbpp-train-greedy-20261013"))
    parser.add_argument("--gpu-memory-utilization", type=float, default=0.85)
    args = parser.parse_args()

    # Load the 591-task training pool and generate with the canonical greedy Qwen protocol.
    rows, source_count = load_training_records()
    prompts = [str(row["prompt"]) for row in rows]
    completions = generate_completions(str(args.model), prompts, args.gpu_memory_utilization)

    # Save all raw completions before running sandbox tests so generation results remain available.
    args.output_dir.mkdir(parents=True, exist_ok=True)
    completion_path = args.output_dir / "completions.json"
    completion_path.write_text(json.dumps({
        "model": "Qwen/Qwen2.5-Coder-0.5B-Instruct",
        "checkpoint_path": str(args.model),
        "split": "repository training pool from MBPP train, validation, and test",
        "decoding": {"temperature": 0.0, "top_p": 1.0, "max_tokens": 2048},
        "task_ids": [str(row["task_id"]) for row in rows],
        "completions": completions,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # Label a task as solved only when its first greedy output passes every original MBPP assertion.
    scored = score_completion_batch(
        [wrap_qwen_continuation(completion) for completion in completions],
        [format_tests(row) for row in rows],
        timeout_seconds=3.0,
        reward_scoring_workers=8,
    )
    labeled_rows = []
    for row, completion, (_, metrics) in zip(rows, completions, scored, strict=True):
        labeled_rows.append({
            "task_id": str(row["task_id"]),
            "task_text": row["task_text"],
            "prompt": row["prompt"],
            "completion": completion,
            "label": int(metrics["status"] == "passed"),
            "status": metrics["status"],
            "passed_tests": metrics["passed_tests"],
            "total_tests": metrics["total_tests"],
            "interface_valid": metrics["interface_valid"],
        })

    # Write one complete router record per filtered training task and summarize the class balance.
    dataset_path = args.output_dir / "router_dataset.jsonl"
    with dataset_path.open("w", encoding="utf-8") as handle:
        for row in labeled_rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    config_hash = hashlib.sha256((args.model / "config.json").read_bytes()).hexdigest()
    summary = {
        "experiment": "qwen05-repository-training-pool-single-greedy-router-labels",
        "model": "Qwen/Qwen2.5-Coder-0.5B-Instruct",
        "checkpoint_path": str(args.model),
        "checkpoint_config_sha256": config_hash,
        "source_dataset": "google-research-datasets/mbpp",
        "source_splits": ["train", "validation", "test"],
        "source_row_count": source_count,
        "evalplus_task_count": 378,
        "filtered_training_task_count": len(labeled_rows),
        "filter": "exclude EvalPlus IDs and normalized task descriptions, matching data.prepare_datasets",
        "decode": {"temperature": 0.0, "top_p": 1.0, "max_tokens": 2048},
        "label_rule": "1 if one greedy completion passes every original MBPP assertion; otherwise 0",
        "class_counts": {
            "solved": sum(row["label"] for row in labeled_rows),
            "unsolved": sum(1 - row["label"] for row in labeled_rows),
        },
        "status_counts": {
            status: sum(row["status"] == status for row in labeled_rows)
            for status in sorted({row["status"] for row in labeled_rows})
        },
        "artifacts": {
            "completions": str(completion_path),
            "router_dataset": str(dataset_path),
        },
    }
    (args.output_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == "__main__":
    # Start the complete training-pool labeling run.
    main()
