"""Run one greedy Qwen 0.5B completion on each generated category task.

The script builds the repository's Qwen EvalPlus prompts, performs one temperature-zero
vLLM completion per task with the original base instruct model, scores the saved tests in
the repository sandbox, and writes per-task results plus aggregate pass@1 metrics.
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import sys
from pathlib import Path
from typing import Any

# Put the repository root on the import path when this file runs as a script.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["HF_HOME"] = "/tmp/mbpp-qwen05-hf-home"
os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "0"

from experiments.run_qwen_official_greedy_eval import build_prompt, generate_completions
from sandbox import score_completion, wrap_qwen_continuation


MODEL = "Qwen/Qwen2.5-Coder-0.5B-Instruct"


def load_tasks(path: Path) -> list[dict[str, Any]]:
    """Read the materialized synthetic-task JSONL rows."""
    # Load each saved task, reference, and assertion without changing their order.
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def build_task_prompt(task: dict[str, Any]) -> str:
    """Add the required function signature to the natural-language task."""
    # Reuse the reference function header so Qwen sees the exact entry-point contract.
    function = ast.parse(task["reference_solution"]).body[0]
    signature = ast.unparse(function).splitlines()[0]
    return f"{task['task_text'].strip()}\n\nImplement this function:\n{signature}"


def evaluate(tasks_path: Path, output_path: Path, timeout_seconds: float) -> dict[str, Any]:
    """Generate and sandbox-score one base-model completion per task."""
    # Load all task prompts and apply the repository's published Qwen ChatML wrapper.
    tasks = load_tasks(tasks_path)
    prompts = [build_prompt(build_task_prompt(task)) for task in tasks]
    # Load the base model from a clean Hub cache instead of the stale empty cache.
    completions = generate_completions(MODEL, prompts)
    rows = []
    # Score every completion against the three saved assertions in an isolated sandbox.
    for task, completion in zip(tasks, completions, strict=True):
        _, metrics = score_completion(wrap_qwen_continuation(completion), "\n".join(task["tests"]), timeout_seconds=timeout_seconds)
        rows.append({
            "prompt_id": task["prompt_id"],
            "category": task["category"],
            "entry_point": task["entry_point"],
            "completion": completion,
            "expected_tests": len(task["tests"]),
            **metrics,
        })
    total_tasks = len(rows)
    passed_tasks = sum(row["status"] == "passed" for row in rows)
    # Count every supplied assertion even when syntax errors prevent sandbox execution.
    total_assertions = sum(int(row["expected_tests"]) for row in rows)
    passed_assertions = sum(int(row["passed_tests"]) for row in rows)
    # Report task pass@1 and assertion fraction for this 13-task preview.
    result = {
        "model": MODEL,
        "checkpoint": "base model, no fine-tuned checkpoint or adapter",
        "decoding": {"temperature": 0.0, "top_p": 1.0, "max_tokens": 2048},
        "task_count": total_tasks,
        "task_pass_at_1": passed_tasks / total_tasks if total_tasks else 0.0,
        "task_passed": passed_tasks,
        "assertion_count": total_assertions,
        "assertion_pass_fraction": passed_assertions / total_assertions if total_assertions else 0.0,
        "assertions_passed": passed_assertions,
        "per_category": {
            category: {
                "tasks": sum(row["category"] == category for row in rows),
                "tasks_passed": sum(row["category"] == category and row["status"] == "passed" for row in rows),
                "assertions_passed": sum(int(row["passed_tests"]) for row in rows if row["category"] == category),
                "assertions_total": sum(int(row["expected_tests"]) for row in rows if row["category"] == category),
            }
            for category in dict.fromkeys(row["category"] for row in rows)
        },
        "tasks": rows,
    }
    # Save completions and all score details so every failure can be reviewed.
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def parse_args() -> argparse.Namespace:
    """Parse task input, result path, and sandbox timeout."""
    # Keep the requested preview files and scoring timeout as command-line defaults.
    parser = argparse.ArgumentParser(description="Evaluate base Qwen 0.5B on synthetic MBPP category tasks.")
    parser.add_argument("--tasks", type=Path, default=ROOT / "analysis" / "mbpp_category_synthetic_tasks_preview.jsonl")
    parser.add_argument("--output", type=Path, default=ROOT / "analysis" / "mbpp_category_synthetic_qwen05_eval.json")
    parser.add_argument("--timeout-seconds", type=float, default=3.0)
    return parser.parse_args()


if __name__ == "__main__":
    # Run the one-sample greedy evaluation and print its summary metrics.
    args = parse_args()
    result = evaluate(args.tasks, args.output, args.timeout_seconds)
    print(json.dumps({key: value for key, value in result.items() if key != "tasks"}, indent=2), flush=True)
