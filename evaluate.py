"""Evaluation helpers for MBPP code-generation checkpoints."""

from __future__ import annotations

import json
from zoneinfo import ZoneInfo
from datetime import datetime
from pathlib import Path
from typing import Any
from sandbox import ExecutionResult, execute_code, extract_code


def start_run_log(log_path: str | Path) -> None:
    """Append a clearly separated, human-readable run-start header."""
    path = Path(log_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    separator = "-" * 72
    prefix = "\n\n\n" if path.exists() and path.stat().st_size else ""
    timestamp = datetime.now(ZoneInfo("America/Los_Angeles")).strftime("%Y-%m-%d %H:%M:%S %Z")
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"{prefix}{separator}\nRUN STARTING\nTimestamp: {timestamp}\n{separator}\n")


def append_training_step_header(log_path: str | Path, step: int, total_steps: int) -> None:
    """Append a header that identifies one training step in the run log."""
    # Write the step header before the trainer generates that step's samples.
    path = Path(log_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"\nTraining Step {step}/{total_steps}\n")


def append_training_step_samples(log_path: str | Path, completions: list[object]) -> None:
    """Append the post-processed samples generated during one training step."""
    # Record exactly what the reward function sends to the execution sandbox.
    path = Path(log_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for completion in completions:
            if isinstance(completion, list):
                text = "".join(str(part.get("text", "")) if isinstance(part, dict) else str(part) for part in completion)
            elif isinstance(completion, dict):
                text = str(completion.get("content", completion.get("text", "")))
            else:
                text = str(completion)
            try:
                executed_code = extract_code(text)
                format_error = ""
            except ValueError as exc:
                executed_code = ""
                format_error = str(exc)
            handle.write(f"Generated code:\n{executed_code}\n")
            if format_error:
                handle.write(f"Format error: {format_error}\n")
            handle.write("\n")


def append_training_step_metrics(log_path: str | Path, metrics: dict[str, Any]) -> None:
    """Append scalar trainer metrics for one training step."""
    # Keep metrics structured so each step can be inspected without W&B.
    path = Path(log_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"Training metrics:\n{json.dumps(metrics, indent=2, default=str)}\n\n")



def append_evaluation_log(log_path: str | Path, evaluation_name: str, records: list[dict[str, Any]], details: list[dict[str, Any]]) -> None:
    """Append prompt, completion, execution result, and reward for every example."""
    path = Path(log_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for record, detail in zip(records, details):
            execution = {
                "status": detail.get("status"),
                "passed": detail.get("passed"),
                "returncode": detail.get("returncode"),
                "stdout": detail.get("stdout", ""),
                "stderr": detail.get("stderr", ""),
            }
            handle.write(
                f"Evaluation: {evaluation_name}\n"
                f"Task ID: {record.get('task_id')}\n\n"
                f"Prompt:\n{record.get('prompt', '')}\n\n"
                f"Code output:\n{detail.get('completion', '')}\n\n"
                f"Code execution result:\n{json.dumps(execution, indent=2)}\n\n"
                f"Award:\n{detail.get('reward', 0.0)}\n\n\n"
            )


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


def evaluate_texts(completions: list[str], records: list[dict[str, Any]], timeout_seconds: float = 3.0, log_path: str | Path = "logs/logs.txt", evaluation_name: str = "evaluation") -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Execute one generated completion per record and aggregate its results."""
    details = []
    for completion, record in zip(completions, records):
        # Execute and record only code extracted from the required output format.
        try:
            executed_completion = extract_code(completion)
            result = execute_code(executed_completion, record["test_code"], timeout_seconds)
        except ValueError as exc:
            executed_completion = ""
            result = ExecutionResult(False, "format_error", stderr=str(exc))
        details.append({"task_id": record.get("task_id"), "completion": executed_completion, "reward": float(result.passed), **result.to_dict()})
    append_evaluation_log(log_path, evaluation_name, records, details)
    return aggregate_results(details), details


def save_evaluation(output_dir: str | Path, name: str, metrics: dict[str, Any], details: list[dict[str, Any]]) -> None:
    """Persist evaluation metrics and per-example details as JSON."""
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{name}-metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    (directory / f"{name}-details.json").write_text(json.dumps(details, indent=2), encoding="utf-8")


def _prepare_generation_inputs(tokenizer: Any, prompt: str, max_length: int, torch: Any) -> dict[str, Any]:
    """Prepare a user-turn prompt with the tokenizer chat template when available."""
    # Preserve a raw-tokenizer fallback for models without a chat template.
    if not getattr(tokenizer, "chat_template", None):
        return tokenizer(prompt, return_tensors="pt", truncation=True, max_length=max_length)
    messages = [{"role": "user", "content": prompt}]
    input_ids = tokenizer.apply_chat_template(
        messages,
        tokenize=True,
        add_generation_prompt=True,
        return_tensors="pt",
        truncation=True,
        max_length=max_length,
    )
    if hasattr(input_ids, "input_ids"):
        return dict(input_ids)
    if isinstance(input_ids, dict):
        return input_ids
    return {"input_ids": input_ids, "attention_mask": torch.ones_like(input_ids)}


def evaluate_model(model: Any, tokenizer: Any, dataset: Any, config: dict[str, Any], evaluation_name: str = "evaluation") -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Generate completions from a model and evaluate them in the sandbox."""
    import torch

    records = [dataset[index] for index in range(len(dataset))]
    completions: list[str] = []
    for record in records:
        inputs = _prepare_generation_inputs(tokenizer, record["prompt"], int(config.get("max_prompt_length", 512)), torch)
        inputs = {key: value.to(model.device) for key, value in inputs.items()}
        with torch.no_grad():
            output = model.generate(**inputs, max_new_tokens=int(config.get("max_completion_length", 512)), do_sample=False)
        completions.append(tokenizer.decode(output[0][inputs["input_ids"].shape[-1]:], skip_special_tokens=True))
    return evaluate_texts(completions, records, float(config.get("sandbox_timeout_seconds", 3)), config.get("log_path", "logs/logs.txt"), evaluation_name)
