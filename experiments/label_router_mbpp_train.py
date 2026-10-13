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

from experiments.run_qwen_official_greedy_eval import generate_completions
from experiments.incremental_rejection_sampling_sft import load_config, load_training_tasks
from sandbox import score_completion_batch, wrap_qwen_continuation


# Run one greedy completion for every repository training task and save the binary targets.
def main() -> None:
    # Parse the base checkpoint and output directory for the complete labeling run.
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path("configs/router-one-shot-labels-20261013.yaml"))
    parser.add_argument("--model", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--gpu-memory-utilization", type=float)
    args = parser.parse_args()

    # Load the configured original and synthetic task pool before sampling any completions.
    root = Path(__file__).resolve().parents[1]
    config_path = args.config if args.config.is_absolute() else root / args.config
    config = load_config(config_path)
    model_path = args.model or Path(config["model_name_or_path"])
    if not model_path.is_absolute():
        model_path = root / model_path
    output_dir = args.output_dir or Path(config["output_dir"])
    if not output_dir.is_absolute():
        output_dir = root / output_dir
    gpu_memory_utilization = args.gpu_memory_utilization or float(config.get("gpu_memory_utilization", 0.85))
    rows = load_training_tasks(config)
    prompts = [str(row["prompt"]) for row in rows]
    completions = generate_completions(str(model_path), prompts, gpu_memory_utilization)

    # Save exactly one raw completion per task before any test-based label is computed.
    output_dir.mkdir(parents=True, exist_ok=True)
    completion_path = output_dir / "completions.json"
    completion_path.write_text(json.dumps({
        "model": "Qwen/Qwen2.5-Coder-0.5B-Instruct",
        "checkpoint_path": str(model_path),
        "split": "original MBPP training pool plus easy synthetic tasks",
        "decoding": {"temperature": 0.0, "top_p": 1.0, "max_tokens": 2048},
        "task_ids": [str(row["task_id"]) for row in rows],
        "completions": completions,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # Score the already-saved single completion against every available task assertion.
    scored = score_completion_batch(
        [wrap_qwen_continuation(completion) for completion in completions],
        [str(row["test_code"]) for row in rows],
        timeout_seconds=3.0,
        reward_scoring_workers=8,
    )
    labeled_rows = []
    for row, completion, (_, metrics) in zip(rows, completions, scored, strict=True):
        mbpp_label = int(metrics["status"] == "passed")
        labeled_rows.append({
            "task_id": str(row["task_id"]),
            "task_text": row["task_text"],
            "prompt": row["prompt"],
            "completion": completion,
            "label": mbpp_label,
            "label_mbpp": mbpp_label,
            "label_mbpp_plus": None,
            "status": metrics["status"],
            "passed_tests": metrics["passed_tests"],
            "total_tests": metrics["total_tests"],
            "interface_valid": metrics["interface_valid"],
        })

    # Write one router record per task and summarize the available MBPP-style label balance.
    dataset_path = output_dir / "router_dataset.jsonl"
    with dataset_path.open("w", encoding="utf-8") as handle:
        for row in labeled_rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    config_hash = hashlib.sha256((model_path / "config.json").read_bytes()).hexdigest()
    source_counts = {
        "original": sum(not str(row["task_id"]).startswith("synthetic-") for row in rows),
        "easy": sum(str(row["task_id"]).startswith("synthetic-easy-") for row in rows),
        "hard": sum(str(row["task_id"]).startswith("synthetic-hard-") for row in rows),
    }
    summary = {
        "experiment": "qwen05-original-easy-one-shot-router-labels",
        "model": "Qwen/Qwen2.5-Coder-0.5B-Instruct",
        "checkpoint_path": str(model_path),
        "checkpoint_config_sha256": config_hash,
        "source_dataset": "google-research-datasets/mbpp",
        "source_splits": ["train", "validation", "test"],
        "task_counts_by_source": source_counts,
        "evalplus_task_count": 378,
        "filtered_training_task_count": len(labeled_rows),
        "filter": "exclude EvalPlus IDs and normalized task descriptions, matching repository training",
        "decode": {"temperature": 0.0, "top_p": 1.0, "max_tokens": 2048},
        "candidate_policy": "exactly one greedy completion per task, generated and saved before test scoring",
        "label_mbpp_rule": "1 if the single completion passes every available assertion for the task; otherwise 0",
        "label_mbpp_plus_rule": "not available for training tasks because they have no separate EvalPlus extension tests",
        "class_counts": {
            "solved": sum(row["label_mbpp"] for row in labeled_rows),
            "unsolved": sum(1 - row["label_mbpp"] for row in labeled_rows),
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
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == "__main__":
    # Start the complete training-pool labeling run.
    main()
