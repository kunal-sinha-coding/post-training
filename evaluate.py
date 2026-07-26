"""Evaluation helpers for MBPP code-generation checkpoints."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sandbox import execute_code, extract_code


def aggregate_results(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate execution outcomes into stable evaluation metrics."""
    total = len(results)
    counts = {status: sum(result["status"] == status for result in results) for status in {result["status"] for result in results}}
    return {
        "examples": total,
        "pass_at_1": sum(bool(result["passed"]) for result in results) / total if total else 0.0,
        "average_reward": sum(float(result["reward"]) for result in results) / total if total else 0.0,
        "status_counts": counts,
    }


def evaluate_texts(completions: list[str], records: list[dict[str, Any]], timeout_seconds: float = 3.0) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Execute one generated completion per record and aggregate its results."""
    details = []
    for completion, record in zip(completions, records):
        result = execute_code(extract_code(completion), record["test_code"], timeout_seconds)
        details.append({"task_id": record.get("task_id"), "completion": completion, "reward": float(result.passed), **result.to_dict()})
    return aggregate_results(details), details


def save_evaluation(output_dir: str | Path, name: str, metrics: dict[str, Any], details: list[dict[str, Any]]) -> None:
    """Persist evaluation metrics and per-example details as JSON."""
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{name}-metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    (directory / f"{name}-details.json").write_text(json.dumps(details, indent=2), encoding="utf-8")


def evaluate_model(model: Any, tokenizer: Any, dataset: Any, config: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Generate completions from a model and evaluate them in the sandbox."""
    import torch

    records = [dataset[index] for index in range(len(dataset))]
    completions: list[str] = []
    for record in records:
        inputs = tokenizer(record["prompt"], return_tensors="pt", truncation=True, max_length=int(config.get("max_prompt_length", 512)))
        inputs = {key: value.to(model.device) for key, value in inputs.items()}
        with torch.no_grad():
            output = model.generate(**inputs, max_new_tokens=int(config.get("max_completion_length", 512)), do_sample=False)
        completions.append(tokenizer.decode(output[0][inputs["input_ids"].shape[-1]:], skip_special_tokens=True))
    return evaluate_texts(completions, records, float(config.get("sandbox_timeout_seconds", 3)))
