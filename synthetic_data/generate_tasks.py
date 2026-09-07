"""Generate executable synthetic Python tasks and track GPT-5.4 Mini generation cost.

The flow asks GPT-5.4 Mini for one structured task, validates its reference and tests
in the local sandbox, rejects invalid or duplicate tasks, writes accepted tasks immediately,
and updates a durable token and cost ledger after every API response.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from sandbox import execute_code

MODEL_INPUT_PRICE = 0.75 / 1_000_000
MODEL_OUTPUT_PRICE = 4.50 / 1_000_000
SYSTEM_PROMPT = """You create self-contained Python programming benchmark tasks. Return exactly one JSON object with keys task, function_name, reference_code, and test_code. The task must specify a single callable function and its behavior precisely. reference_code must define that function without Markdown fences. test_code must contain executable Python assertions that import or call the function defined by reference_code. Include at least five meaningful assertions covering normal, boundary, and invalid or empty inputs when applicable. Do not use external packages, filesystem access, network access, randomness, or time. Make the task distinct from common MBPP and HumanEval tasks."""


def task_key(task: dict[str, Any]) -> str:
    """Return a stable key for duplicate detection."""
    # Normalize the task description and signature before hashing its identity.
    normalized = f"{task['task'].strip().lower()}\n{task['function_name'].strip().lower()}"
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def validate_task(task: dict[str, Any]) -> tuple[bool, str]:
    """Validate the required schema and execute the reference against every test."""
    # Require all generated fields before attempting sandbox execution.
    required = {"task", "function_name", "reference_code", "test_code"}
    if set(task) != required or any(not isinstance(task[key], str) or not task[key].strip() for key in required):
        return False, "schema"
    # Reject malformed or non-Python reference and test programs.
    result = execute_code(task["reference_code"], task["test_code"], timeout_seconds=5.0)
    if not result.passed:
        return False, result.status
    # Confirm that the declared function is actually defined by the reference.
    if f"def {task['function_name']}" not in task["reference_code"]:
        return False, "missing_function"
    return True, "passed"


def load_existing_keys(path: Path) -> set[str]:
    """Load task identity keys from an existing JSONL artifact."""
    # Reuse prior accepted tasks so interrupted runs do not create duplicates.
    if not path.exists():
        return set()
    keys = set()
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                keys.add(task_key(json.loads(line)))
    return keys


def update_cost(path: Path, stats: dict[str, Any]) -> None:
    """Persist cumulative token usage, request counts, and estimated spend."""
    # Write the ledger after every request so cost remains visible during long runs.
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(stats, indent=2) + "\n", encoding="utf-8")


def request_task(client: Any, model: str) -> tuple[dict[str, Any], dict[str, int]]:
    """Request one structured programming task and return its usage counters."""
    # Use structured JSON output so malformed outer responses are minimized.
    response = client.responses.create(
        model=model,
        input=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": "Generate one new Python benchmark task."}],
        text={"format": {"type": "json_object"}},
    )
    usage = response.usage
    tokens = {"input_tokens": int(getattr(usage, "input_tokens", 0) or 0), "output_tokens": int(getattr(usage, "output_tokens", 0) or 0)}
    return json.loads(response.output_text), tokens


def generate_tasks(config: dict[str, Any]) -> dict[str, Any]:
    """Generate, validate, persist, and cost-account synthetic tasks."""
    # Load the repository dotenv file before checking the API credential.
    load_dotenv()
    # Fail early when the API credential is unavailable.
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is required for synthetic task generation.")
    from openai import OpenAI

    output_path = Path(config["output"])
    cost_path = Path(config["cost_log"])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    stats = {"model": config["model"], "accepted": 0, "rejected": 0, "requests": 0, "retries": 0, "input_tokens": 0, "output_tokens": 0, "estimated_cost_usd": 0.0}
    if cost_path.exists():
        stats.update(json.loads(cost_path.read_text(encoding="utf-8")))
    existing_keys = load_existing_keys(output_path)
    client = OpenAI()
    target = int(config["preview_count"] or config["num_tasks"])

    # Generate until the preview or full target count of accepted tasks is reached.
    while stats["accepted"] < target:
        stats["requests"] += 1
        try:
            task, tokens = request_task(client, config["model"])
            stats["input_tokens"] += tokens["input_tokens"]
            stats["output_tokens"] += tokens["output_tokens"]
            stats["estimated_cost_usd"] = stats["input_tokens"] * MODEL_INPUT_PRICE + stats["output_tokens"] * MODEL_OUTPUT_PRICE
            valid, reason = validate_task(task)
            key = task_key(task) if valid else ""
            if not valid or key in existing_keys:
                stats["rejected"] += 1
                if key in existing_keys:
                    reason = "duplicate"
                print(f"Rejected task {stats['requests']}: {reason}.", flush=True)
            else:
                task["task_id"] = f"synthetic-{stats['accepted'] + 1:05d}"
                with output_path.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(task, ensure_ascii=False) + "\n")
                existing_keys.add(key)
                stats["accepted"] += 1
                print(json.dumps({"accepted": stats["accepted"], "task": task, "estimated_cost_usd": stats["estimated_cost_usd"]}, ensure_ascii=False), flush=True)
        except Exception as exc:
            stats["rejected"] += 1
            stats["retries"] += 1
            print(f"Request failed and will retry: {type(exc).__name__}: {exc}", flush=True)
            time.sleep(float(config["retry_seconds"]))
        finally:
            # Persist usage even when validation or parsing rejects the response.
            update_cost(cost_path, stats)
    print(json.dumps(stats, indent=2), flush=True)
    return stats


def parse_args() -> dict[str, Any]:
    """Parse task count, preview, output, and cost configuration."""
    # Keep the preview count separate so the first run can stop before the full target.
    parser = argparse.ArgumentParser(description="Generate executable synthetic Python tasks with GPT-5.4 Mini.")
    parser.add_argument("--num-tasks", type=int, default=1000)
    parser.add_argument("--preview-count", type=int, default=None)
    parser.add_argument("--model", default="gpt-5.4-mini")
    parser.add_argument("--output", default="outputs/synthetic-tasks/tasks.jsonl")
    parser.add_argument("--cost-log", default="outputs/synthetic-tasks/cost.json")
    parser.add_argument("--retry-seconds", type=float, default=2.0)
    return vars(parser.parse_args())


if __name__ == "__main__":
    # Start the configured generation run from the command line.
    generate_tasks(parse_args())
