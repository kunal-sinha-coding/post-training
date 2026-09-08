"""Prepare the original MBPP validation tasks for fixed verifier ranking evaluation.

The flow loads the official MBPP validation split, preserves each task's prompt, tests,
and reference implementation, and writes one JSONL task record per validation example.
The labeling script then adds ten generated candidates and sandbox labels without changing
the task set used for verifier training.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from data import load_mbpp


def prepare_tasks(dataset_name: str, dataset_config: str | None, output: Path) -> None:
    """Write normalized original MBPP validation records for candidate generation."""
    # Load the complete official validation split so ranking metrics cover every validation task.
    records = load_mbpp(dataset_name, dataset_config, "validation")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as handle:
        for record in records:
            # Keep references as positive audit rows while excluding them from candidate ranking.
            item: dict[str, Any] = {
                "task_id": str(record["task_id"]),
                "task": str(record["prompt"]).split("Task:\n", 1)[-1].split("\n\nTests:", 1)[0].strip(),
                "prompt": str(record["prompt"]),
                "test_code": str(record["test_code"]),
                "reference_code": str(record["reference_code"]),
            }
            handle.write(json.dumps(item, ensure_ascii=False) + "\n")
    print(f"Saved {len(records)} MBPP validation tasks to {output}.", flush=True)


def parse_args() -> argparse.Namespace:
    """Parse the ranking artifact configuration."""
    # Keep dataset and output choices explicit for reproducible evaluation preparation.
    parser = argparse.ArgumentParser(description="Prepare MBPP validation tasks for verifier Pass@K ranking evaluation.")
    parser.add_argument("--dataset-name", default="google-research-datasets/mbpp")
    parser.add_argument("--dataset-config", default=None)
    parser.add_argument("--output", default="outputs/ranking-eval/tasks.jsonl")
    return parser.parse_args()


if __name__ == "__main__":
    # Prepare the fixed task artifact when invoked as a module.
    arguments = parse_args()
    prepare_tasks(arguments.dataset_name, arguments.dataset_config, Path(arguments.output))
