"""Evaluation helpers for MBPP code-generation checkpoints."""

from __future__ import annotations

import json
import re
import subprocess
from zoneinfo import ZoneInfo
from datetime import datetime
from pathlib import Path
from typing import Any
from sandbox import extract_code, score_completion

MAX_RUN_LOGS = 10


def _append_run_header(path: Path, timestamp: str) -> None:
    """Append one standard run header to a log file."""
    # Keep results and detailed logs visually aligned at every run boundary.
    path.parent.mkdir(parents=True, exist_ok=True)
    prefix = "\n\n\n" if path.exists() and path.stat().st_size else ""
    separator = "-" * 72
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"{prefix}{separator}\nRUN STARTING\nTimestamp: {timestamp}\n{separator}\n")


def start_run_log(log_path: str | Path, results_log_path: str | Path | None = None) -> None:
    """Append a clearly separated, human-readable run-start header."""
    path = Path(log_path)
    timestamp = datetime.now(ZoneInfo("America/Los_Angeles")).strftime("%Y-%m-%d %H:%M:%S %Z")
    _append_run_header(path, timestamp)
    if results_log_path is not None:
        _append_run_header(Path(results_log_path), timestamp)
    cleanup_run_logs(path)


def cleanup_run_logs(log_path: str | Path) -> None:
    """Keep only the newest configured number of run logs in the log directory."""
    if MAX_RUN_LOGS == -1:
        return
    if MAX_RUN_LOGS < -1:
        raise ValueError("MAX_RUN_LOGS must be -1 or a non-negative integer.")

    # Treat the existing text and log files in the configured directory as run logs.
    directory = Path(log_path).parent
    log_files = [
        candidate
        for candidate in directory.iterdir()
        if candidate.is_file() and candidate.suffix in {".log", ".txt"} and candidate.name not in {"results.txt", "error_analysis.txt"}
    ]
    log_files.sort(key=lambda candidate: candidate.stat().st_mtime, reverse=True)
    for stale_log in log_files[MAX_RUN_LOGS:]:
        stale_log.unlink()
    _truncate_error_analysis(directory / "error_analysis.txt")


def _truncate_error_analysis(path: Path) -> None:
    """Keep only the newest configured number of error analysis reports."""
    # Treat each ERROR ANALYSIS header as the beginning of one report.
    if not path.is_file() or MAX_RUN_LOGS == -1:
        return
    contents = path.read_text(encoding="utf-8")
    starts = [match.start() for match in re.finditer(r"(?m)^-{72}\nERROR ANALYSIS\n", contents)]
    if MAX_RUN_LOGS == 0:
        path.write_text("", encoding="utf-8")
        return
    if len(starts) <= MAX_RUN_LOGS:
        return
    kept_start = starts[-MAX_RUN_LOGS]
    path.write_text(contents[kept_start:], encoding="utf-8")


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
    # Score evaluation completions with the same dense reward used during training.
    details = []
    for completion, record in zip(completions, records):
        # Preserve extracted code for logs while retaining malformed completions as failures.
        try:
            executed_completion = extract_code(completion)
        except ValueError:
            executed_completion = ""

        # Reuse the training scorer so average reward has identical semantics.
        reward, score_details = score_completion(completion, record["test_code"], timeout_seconds)
        passed = score_details["status"] == "passed"
        details.append({"task_id": record.get("task_id"), "completion": executed_completion, "reward": reward, "passed": passed, **score_details})
    append_evaluation_log(log_path, evaluation_name, records, details)
    return aggregate_results(details), details


def _change_description(results_log_path: str | Path, config: dict[str, Any]) -> tuple[str, str]:
    """Describe repository changes since the previous recorded evaluation."""
    # Use the previous result commit as a stable comparison point when Git is available.
    current_commit = "unknown"
    try:
        current_commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
        previous_commits = []
        results_path = Path(results_log_path)
        if results_path.is_file():
            for line in results_path.read_text(encoding="utf-8").splitlines():
                if line.startswith("Git commit: "):
                    previous_commits.append(line.removeprefix("Git commit: ").strip())
        previous_commit = previous_commits[-1] if previous_commits else ""
        if previous_commit:
            changes = subprocess.run(["git", "log", "--oneline", f"{previous_commit}..{current_commit}"], capture_output=True, text=True, check=True).stdout.strip()
            description = changes or "No committed code changes since the previous evaluation."
        else:
            description = "No previous evaluation result was available for comparison."
    except (OSError, subprocess.CalledProcessError):
        description = "Git change history was unavailable; compare the YAML and artifacts manually."
    return current_commit, description


def append_evaluation_result(results_log_path: str | Path, name: str, metrics: dict[str, Any], metadata: dict[str, Any]) -> None:
    """Append metrics, context, configuration, and change metadata to results.txt."""
    # Store the complete YAML text so each result is independently reproducible.
    config_yaml = metadata.get("_config_yaml", "")
    current_commit, changes = _change_description(results_log_path, metadata)
    path = Path(results_log_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    training_context = metadata.get("training_context", "unknown")
    epoch = metadata.get("_evaluation_epoch", "unknown")
    timestamp = datetime.now(ZoneInfo("America/Los_Angeles")).strftime("%Y-%m-%d %H:%M:%S %Z")
    config_path = metadata.get("_config_path", "unknown")
    with path.open("a", encoding="utf-8") as handle:
        handle.write(
            "\n"
            + "-" * 72
            + "\nEVALUATION RESULTS\n"
            + f"Evaluation: {name}\n"
            + f"Training context: {training_context}\n"
            + f"Epoch: {epoch}\n"
            + f"Timestamp: {timestamp}\n"
            + f"Git commit: {current_commit}\n"
            + f"Change description: {changes}\n"
            + "Metrics:\n"
            + json.dumps(metrics, indent=2, sort_keys=True)
            + "\nYAML path: "
            + f"{config_path}\nYAML contents:\n"
            + str(config_yaml)
            + "\n"
            + "-" * 72
            + "\n"
        )


def save_evaluation(output_dir: str | Path, name: str, metrics: dict[str, Any], details: list[dict[str, Any]], metadata: dict[str, Any] | None = None) -> None:
    """Persist evaluation artifacts and append a reproducible results record."""
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{name}-metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    (directory / f"{name}-details.json").write_text(json.dumps(details, indent=2), encoding="utf-8")
    if metadata:
        append_evaluation_result(metadata["results_log_path"], name, metrics, metadata)


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


def _prepare_generation_batch(tokenizer: Any, prompts: list[str], max_length: int, torch: Any) -> dict[str, Any]:
    """Tokenize multiple prompts together for more efficient generation."""
    # Use the configured padding token for batched generation.
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "left"
    if getattr(tokenizer, "chat_template", None):
        messages = [[{"role": "user", "content": prompt}] for prompt in prompts]
        encoded = tokenizer.apply_chat_template(
            messages,
            tokenize=True,
            add_generation_prompt=True,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=max_length,
        )
    else:
        encoded = tokenizer(prompts, return_tensors="pt", padding=True, truncation=True, max_length=max_length)
    if hasattr(encoded, "input_ids"):
        return dict(encoded)
    if isinstance(encoded, dict):
        return encoded
    return {"input_ids": encoded, "attention_mask": torch.ones_like(encoded)}


def evaluate_model(model: Any, tokenizer: Any, dataset: Any, config: dict[str, Any], evaluation_name: str = "evaluation") -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Generate completions from a model and evaluate them in the sandbox."""
    import torch

    # Disable dropout during every evaluation and restore the caller's mode afterward.
    was_training = bool(model.training)
    model.eval()
    records = [dataset[index] for index in range(len(dataset))]
    completions: list[str] = []
    batch_size = max(1, int(config.get("evaluation_batch_size", 8)))
    try:
        for start in range(0, len(records), batch_size):
            batch_records = records[start : start + batch_size]
            inputs = _prepare_generation_batch(tokenizer, [record["prompt"] for record in batch_records], int(config.get("max_prompt_length", 512)), torch)
            inputs = {key: value.to(model.device) for key, value in inputs.items()}
            with torch.no_grad():
                output = model.generate(**inputs, max_new_tokens=int(config.get("max_completion_length", 512)), do_sample=False)
            prompt_width = inputs["input_ids"].shape[-1]
            completions.extend(tokenizer.decode(item[prompt_width:], skip_special_tokens=True) for item in output)
        return evaluate_texts(completions, records, float(config.get("sandbox_timeout_seconds", 3)), config.get("log_path", "logs/logs.txt"), evaluation_name)
    finally:
        model.train(was_training)
