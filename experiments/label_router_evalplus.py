# This script runs the base Qwen model on all canonical EvalPlus MBPP tasks and saves per-task binary success labels.
# It generates one greedy completion per task with the repository's Qwen EvalPlus prompt and decode settings.
# It runs the canonical EvalPlus evaluator on both base and extended tests.
# It saves prompts, completions, task outcomes, and benchmark summaries for router evaluation.

from __future__ import annotations

import argparse
import json
import os
import time
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from typing import Any

from evalplus.data import get_mbpp_plus
from evalplus.evaluate import evaluate

from experiments.run_qwen_official_greedy_eval import generate_evalplus_samples, load_tasks


# Generate one canonical EvalPlus sample for every task and score each sample with EvalPlus.
def main() -> None:
    # Parse the checkpoint path and directory for persistent prompts, outputs, and labels.
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, default=Path("outputs/evalplus-pass16-mbpphard10x1009-seed42-20261011/base-model"))
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/router-evalplus-greedy-20261013"))
    parser.add_argument("--gpu-memory-utilization", type=float, default=0.85)
    args = parser.parse_args()

    # Generate and save one temperature-zero completion per canonical EvalPlus task.
    args.output_dir.mkdir(parents=True, exist_ok=True)
    from dotenv import load_dotenv
    import wandb

    root = Path(__file__).resolve().parents[1]
    load_dotenv(root / ".env")
    if not os.getenv("WANDB_API_KEY"):
        raise RuntimeError("WANDB_API_KEY is required to log router EvalPlus labeling.")
    task_rows = load_tasks()
    run = wandb.init(
        entity="kunal-personal",
        project="grpo-mbpp",
        name="router-evalplus-dual-labels-one-shot-20261013",
        job_type="router-label-generation",
        config={
            "model": "Qwen/Qwen2.5-Coder-0.5B-Instruct",
            "checkpoint_path": str(args.model),
            "dataset": "canonical EvalPlus MBPP",
            "task_count": len(task_rows),
            "candidate_policy": "one temperature-zero completion per task, scored against both test sets",
            "targets": ["all MBPP base tests", "all MBPP+ base and extra tests"],
            "max_tokens": 2048,
            "output_dir": str(args.output_dir),
        },
    )
    run.log({"labeling/task_count": len(task_rows), "labeling/generation_started": 1})
    generation_started = time.time()
    samples = generate_evalplus_samples(args.model, args.output_dir / "evalplus", args.gpu_memory_utilization)
    generation_seconds = time.time() - generation_started
    run.log({
        "labeling/generation_completed": 1,
        "labeling/generation_seconds": generation_seconds,
        "labeling/completions_per_second": len(task_rows) / max(generation_seconds, 1e-9),
    })
    evaluator_output = StringIO()
    with redirect_stdout(evaluator_output):
        evaluate(
            dataset="mbpp",
            samples=str(samples),
            base_only=False,
            parallel=8,
            i_just_wanna_run=False,
            test_details=True,
            min_time_limit=1,
            gt_time_limit_factor=4.0,
            mini=False,
            noextreme=False,
        )
    result_text = evaluator_output.getvalue()
    (args.output_dir / "evalplus_results.txt").write_text(result_text, encoding="utf-8")

    # Join saved completions to the canonical base and extended test outcomes by task ID.
    eval_data = json.loads((samples / "eval_results.json").read_text(encoding="utf-8"))["eval"]
    problems = get_mbpp_plus()
    expected_ids = {task["task_id"] for task in task_rows}
    if set(eval_data) != expected_ids:
        raise ValueError(f"EvalPlus returned {len(eval_data)} results for {len(expected_ids)} tasks.")
    labeled_rows: list[dict[str, Any]] = []
    for task in task_rows:
        task_id = task["task_id"]
        result = eval_data[task_id][0]
        completion_path = samples / task_id.replace("/", "_") / "0.py"
        completion = completion_path.read_text(encoding="utf-8")
        labeled_rows.append({
            "task_id": task_id,
            "prompt": task["prompt"],
            "completion": completion,
            "label": int(result["plus_status"] == "pass"),
            "label_base": int(result["base_status"] == "pass"),
            "label_mbpp": int(result["base_status"] == "pass"),
            "label_mbpp_plus": int(result["plus_status"] == "pass"),
            "base_status": result["base_status"],
            "plus_status": result["plus_status"],
            "base_fail_tests": result.get("base_fail_tests", []),
            "plus_fail_tests": result.get("plus_fail_tests", []),
            "base_test_count": len(problems[task_id]["base_input"]),
            "plus_test_count": len(problems[task_id]["base_input"]) + len(problems[task_id]["plus_input"]),
        })

    # Save every prompt, generated program, binary label, and official failure record.
    args.output_dir.mkdir(parents=True, exist_ok=True)
    labels_path = args.output_dir / "router_evalplus_labels.jsonl"
    with labels_path.open("w", encoding="utf-8") as handle:
        for row in labeled_rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    summary = {
        "experiment": "qwen05-evalplus-single-greedy-router-labels",
        "model": "Qwen/Qwen2.5-Coder-0.5B-Instruct",
        "checkpoint_path": str(args.model),
        "dataset": "canonical EvalPlus MBPP",
        "task_count": len(labeled_rows),
        "decoding": {"temperature": 0.0, "top_p": 1.0, "max_tokens": 2048},
        "candidate_policy": "exactly one greedy completion per task, generated before official test scoring",
        "label_mbpp_plus_rule": "1 when the single completion passes every base and extra MBPP+ test; otherwise 0",
        "label_mbpp_rule": "1 when the single completion passes every original MBPP base test; otherwise 0",
        "plus_solved": sum(row["label"] for row in labeled_rows),
        "plus_unsolved": sum(1 - row["label"] for row in labeled_rows),
        "base_solved": sum(row["label_base"] for row in labeled_rows),
        "base_unsolved": sum(1 - row["label_base"] for row in labeled_rows),
        "artifacts": {
            "samples": str(samples),
            "labels": str(labels_path),
            "results_text": str(args.output_dir / "evalplus_results.txt"),
        },
    }
    (args.output_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    run.log({
        "labeling/mbpp_positive_count": summary["base_solved"],
        "labeling/mbpp_negative_count": summary["base_unsolved"],
        "labeling/mbpp_plus_positive_count": summary["plus_solved"],
        "labeling/mbpp_plus_negative_count": summary["plus_unsolved"],
        "labeling/scoring_completed": 1,
    })
    artifact = wandb.Artifact("router-evalplus-dual-labels-one-shot-20261013", type="dataset")
    for artifact_path in (labels_path, args.output_dir / "summary.json", args.output_dir / "evalplus_results.txt"):
        artifact.add_file(str(artifact_path))
    artifact.add_dir(str(samples))
    run.log_artifact(artifact)
    run.finish()
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == "__main__":
    # Start full EvalPlus generation and labeling before router training.
    main()
