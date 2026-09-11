"""Measure GPT answer-prediction accuracy by candidate correctness cohort.

The script groups EvalPlus tasks by how many of their ten saved candidates pass
the standard base tests, then reports cached GPT-5 mini output-prediction
accuracy separately for mixed, all-correct, and all-incorrect groups.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path


# Classify a task using saved candidate correctness labels after prediction.
def cohort(task_id: str, evaluations: dict) -> str:
    passed = sum(row["base_status"] == "pass" for row in evaluations[task_id])
    return "all_correct" if passed == 10 else "all_incorrect" if passed == 0 else "mixed"


# Aggregate per-test and whole-task prediction accuracy for one cohort.
def summarize(rows: list[dict]) -> dict:
    test_correct = sum(row["test_correct"] for row in rows)
    test_total = sum(row["test_total"] for row in rows)
    task_correct = sum(row["all_tests_correct"] for row in rows)
    return {
        "tasks": len(rows),
        "test_correct": test_correct,
        "test_total": test_total,
        "test_accuracy": test_correct / test_total if test_total else 0.0,
        "tasks_all_correct": task_correct,
        "task_accuracy": task_correct / len(rows) if rows else 0.0,
    }


# Group cached prediction metrics and save the cohort comparison.
def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--predictions", type=Path, default=Path("outputs/qwen-evalplus-full-10-temp02/llm-test-answer-predictions-399.json"))
    parser.add_argument("--evaluations", type=Path, default=Path("outputs/qwen-evalplus-full-10-temp02/mbpp/qwen2_chat_temp_0.2/eval_results.json"))
    parser.add_argument("--output", type=Path, default=Path("outputs/qwen-evalplus-full-10-temp02/answer-prediction-cohorts.json"))
    args = parser.parse_args()
    predictions = json.loads(args.predictions.read_text())
    evaluations = json.loads(args.evaluations.read_text())["eval"]
    grouped = defaultdict(list)
    for task_id in predictions["tasks"]:
        grouped[cohort(task_id, evaluations)].append(predictions["metrics"]["per_task"][task_id])
    report = {
        "prediction_artifact": str(args.predictions),
        "evaluation_artifact": str(args.evaluations),
        "cohorts": {name: summarize(grouped[name]) for name in ("mixed", "all_correct", "all_incorrect")},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report["cohorts"], indent=2))


if __name__ == "__main__":
    main()
