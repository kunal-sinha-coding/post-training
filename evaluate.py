"""Evaluation helpers for MBPP code-generation checkpoints."""

from __future__ import annotations

import ast
import json
import re
import subprocess
from zoneinfo import ZoneInfo
from datetime import datetime
from pathlib import Path
from typing import Any
from sandbox import expected_interface, extract_code, score_completion

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
    """Append raw model samples and their extracted sandbox inputs for one training step."""
    # Record both the unmodified model text and the code sent to scoring after fence extraction.
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
            handle.write(f"Raw completion from LLM:\n{text}\n\n")
            handle.write(f"Sandbox input after fence extraction/truncation:\n{executed_code}\n")
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



def append_evaluation_log(log_path: str | Path, evaluation_name: str, records: list[dict[str, Any]], details: list[dict[str, Any]], raw_completions: list[str] | None = None) -> None:
    """Append prompt, completion, execution result, and reward for every example."""
    path = Path(log_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for index, (record, detail) in enumerate(zip(records, details)):
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
                    f"Raw completion from LLM:\n{(raw_completions[index] if raw_completions and index < len(raw_completions) else detail.get('raw_completion', ''))}\n\n"
                    f"Sandbox input after fence extraction/truncation:\n{detail.get('completion', '')}\n\n"
                f"Code execution result:\n{json.dumps(execution, indent=2)}\n\n"
                f"Award:\n{detail.get('reward', 0.0)}\n\n\n"
            )


def aggregate_results(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate execution outcomes into stable evaluation metrics."""
    total = len(results)
    counts = {status: sum(result["status"] == status for result in results) for status in {result["status"] for result in results}}
    metrics = {
        "examples": total,
        "pass_at_1": sum(bool(result["passed"]) for result in results) / total if total else 0.0,
        "average_reward": sum(float(result["reward"]) for result in results) / total if total else 0.0,
        "status_counts": counts,
    }
    # Summarize reward components so evaluation reward gains can be audited for misalignment.
    for component in ("format", "syntax", "interface", "tests", "pass"):
        values = [float(result.get("reward_components", {}).get(component, 0.0)) for result in results]
        metrics[f"reward_{component}_mean"] = sum(values) / total if total else 0.0
    metrics["successful_examples"] = sum(bool(result["passed"]) for result in results)
    metrics["unique_completion_rate"] = len({str(result.get("completion", "")).strip() for result in results}) / total if total else 0.0
    metrics["repeated_completion_fraction"] = 1.0 - metrics["unique_completion_rate"]
    return metrics


def code_fence_stopping_criteria(tokenizer: Any, prompt_width: int) -> Any:
    """Stop each generation after a closing code fence appears in generated tokens."""
    import torch
    from transformers import StoppingCriteria, StoppingCriteriaList

    class CodeFenceCriteria(StoppingCriteria):
        """Track per-sequence closing-fence matches without scanning prompt tokens."""

        def __init__(self) -> None:
            # Tokenize the stop sequence once and track which rows have finished.
            encoded = tokenizer("```", add_special_tokens=False)
            self.stop_ids = torch.tensor(encoded["input_ids"], dtype=torch.long)
            self.finished: torch.Tensor | None = None

        def __call__(self, input_ids: Any, scores: Any, **kwargs: Any) -> bool:
            """Return true only after every generated row has emitted the closing fence."""
            del scores, kwargs
            stop_ids = self.stop_ids.to(input_ids.device)
            if self.finished is None or self.finished.shape[0] != input_ids.shape[0]:
                self.finished = torch.zeros(input_ids.shape[0], dtype=torch.bool, device=input_ids.device)
            generated = input_ids[:, prompt_width:]
            if generated.shape[1] >= stop_ids.shape[0]:
                suffix = generated[:, -stop_ids.shape[0]:]
                self.finished |= torch.all(suffix == stop_ids, dim=1)
            return bool(torch.all(self.finished).item())

    return StoppingCriteriaList([CodeFenceCriteria()])


def forced_code_prefix_processor(tokenizer: Any, prompt_width: int, prefix_text: str = "Code:\n```python\n") -> Any:
    """Force every completion to begin with the required Code label and Python fence."""
    import torch
    from transformers import LogitsProcessor

    class ForcedCodePrefix(LogitsProcessor):
        """Constrain only the initial generated tokens to the canonical response prefix."""

        def __init__(self) -> None:
            # Tokenize the protocol prefix without adding special tokens.
            self.prefix_ids = tokenizer(prefix_text, add_special_tokens=False)["input_ids"]

        def __call__(self, input_ids: Any, scores: Any) -> Any:
            """Allow only the next prefix token until the required prefix is complete."""
            generated_steps = input_ids.shape[1] - prompt_width
            if generated_steps >= len(self.prefix_ids):
                return scores
            constrained = torch.full_like(scores, torch.finfo(scores.dtype).min)
            constrained[:, self.prefix_ids[generated_steps]] = 0
            return constrained

    return ForcedCodePrefix()


def forced_code_prefix_length(tokenizer: Any, prefix_text: str = "Code:\n```python\n") -> int:
    """Return the number of generated tokens reserved for the forced response prefix."""
    return len(tokenizer(prefix_text, add_special_tokens=False)["input_ids"])


def _interface_generation_prefix(tokenizer: Any, tests: str, include_generic_arguments: bool = False) -> str:
    """Build the complete prefilled function header inferred from the tests."""
    name, arities = expected_interface(tests)
    if name is None:
        return "Code:\n```python\n"
    if not include_generic_arguments or len(arities) != 1:
        return f"Code:\n```python\ndef {name}("
    count = next(iter(arities))
    arguments = ", ".join(f"arg{i}" for i in range(1, count + 1))
    return f"Code:\n```python\ndef {name}({arguments}):\n"


def evaluate_texts(completions: list[str], records: list[dict[str, Any]], timeout_seconds: float = 3.0, log_path: str | Path = "logs/logs.txt", evaluation_name: str = "evaluation", pass_weight: float = 0.5, diagnostics: dict[str, float] | None = None) -> tuple[dict[str, Any], list[dict[str, Any]]]:
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
        reward, score_details = score_completion(completion, record["test_code"], timeout_seconds, pass_weight)
        passed = score_details["status"] == "passed"
        details.append({"task_id": record.get("task_id"), "raw_completion": completion, "completion": executed_completion, "reward": reward, "passed": passed, **score_details})
    append_evaluation_log(log_path, evaluation_name, records, details, completions)
    metrics = aggregate_results(details)
    # Include model-distribution diagnostics collected during generation when available.
    if diagnostics:
        metrics.update(diagnostics)
    return metrics, details


def _generation_diagnostics(model: Any, output: Any, prompt_width: int, torch: Any) -> dict[str, float]:
    """Measure token entropy and optional reference-policy KL on generated tokens."""
    # Compare the policy distribution with an attached reference model when one exists.
    generated_width = max(0, int(output.shape[-1]) - prompt_width)
    if not generated_width:
        return {}
    attention_mask = torch.ones_like(output)
    with torch.no_grad():
        policy_logits = model(input_ids=output, attention_mask=attention_mask).logits[:, prompt_width - 1 : -1, :]
        policy_log_probs = torch.log_softmax(policy_logits, dim=-1)
        policy_probs = policy_log_probs.exp()
        entropy = -(policy_probs * policy_log_probs).sum(dim=-1).mean().item()
        diagnostics = {"entropy": float(entropy)}
        reference_model = getattr(model, "ref_model", None) or getattr(model, "reference_model", None)
        if reference_model is not None:
            reference_logits = reference_model(input_ids=output, attention_mask=attention_mask).logits[:, prompt_width - 1 : -1, :]
            reference_log_probs = torch.log_softmax(reference_logits, dim=-1)
            kl = (policy_probs * (policy_log_probs - reference_log_probs)).sum(dim=-1).mean().item()
            diagnostics["reference_kl"] = float(kl)
    return diagnostics


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


def _wrong_arity(completion: str, tests: str) -> tuple[str, int, int] | None:
    """Return the expected name and arities when a generated function has the wrong argument count."""
    try:
        expected_name, expected_arities = expected_interface(tests)
        if expected_name is None or len(expected_arities) != 1:
            return None
        code = extract_code(completion)
        tree = ast.parse(code)
    except (ValueError, SyntaxError):
        return None
    definitions = [node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == expected_name]
    if len(definitions) != 1:
        return None
    definition = definitions[0]
    actual = len(definition.args.posonlyargs) + len(definition.args.args)
    expected = next(iter(expected_arities))
    if actual == expected:
        return None
    return expected_name, actual, expected


def evaluate_model(model: Any, tokenizer: Any, dataset: Any, config: dict[str, Any], evaluation_name: str = "evaluation") -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Generate completions from a model and evaluate them in the sandbox."""
    import torch

    # Disable dropout during every evaluation and restore the caller's mode afterward.
    was_training = bool(model.training)
    model.eval()
    records = [dataset[index] for index in range(len(dataset))]
    completions: list[str] = []
    entropy_values: list[float] = []
    reference_kl_values: list[float] = []
    batch_size = max(1, int(config.get("evaluation_batch_size", 8)))
    try:
        for record in records:
            retry_prompt = str(record["prompt"])
            completion = ""
            max_retries = max(0, int(config.get("max_retries", 0)))
            for attempt in range(max_retries + 1):
                expected_name, _ = expected_interface(record["test_code"])
                prefix_text = _interface_generation_prefix(tokenizer, record["test_code"], bool(config.get("include_generic_arguments", False)))
                inputs = _prepare_generation_inputs(tokenizer, retry_prompt, int(config.get("max_prompt_length", 512)), torch)
                inputs = {key: value.to(model.device) for key, value in inputs.items()}
                prompt_width = inputs["input_ids"].shape[-1]
                with torch.no_grad():
                    output = model.generate(
                        **inputs,
                        max_new_tokens=int(config.get("max_completion_length", 512)),
                        do_sample=bool(config.get("do_sample", False)),
                        **({"temperature": float(config["temperature"])} if config.get("do_sample", False) and config.get("temperature") is not None else {}),
                        logits_processor=[forced_code_prefix_processor(tokenizer, prompt_width, prefix_text)],
                        stopping_criteria=code_fence_stopping_criteria(tokenizer, prompt_width + forced_code_prefix_length(tokenizer, prefix_text)),
                    )
                generation_metrics = _generation_diagnostics(model, output, prompt_width, torch)
                if "entropy" in generation_metrics:
                    entropy_values.append(generation_metrics["entropy"])
                if "reference_kl" in generation_metrics:
                    reference_kl_values.append(generation_metrics["reference_kl"])
                completion = tokenizer.decode(output[0, prompt_width:], skip_special_tokens=True)
                retry_info = _wrong_arity(completion, record["test_code"])
                if retry_info is None or attempt >= max_retries:
                    break
                name, actual, expected = retry_info
                retry_prompt += (
                    f"\n\nPrevious generation:\n{completion}\n\n"
                    f"This previous generation was incorrect because it had {actual} arguments instead of {expected}. Try again.\n\n"
                    f"Code:\n```python\ndef {name}("
                )
            completions.append(completion)
        diagnostics = {}
        if entropy_values:
            diagnostics["entropy"] = sum(entropy_values) / len(entropy_values)
        if reference_kl_values:
            diagnostics["reference_kl"] = sum(reference_kl_values) / len(reference_kl_values)
        return evaluate_texts(completions, records, float(config.get("sandbox_timeout_seconds", 3)), config.get("log_path", "logs/logs.txt"), evaluation_name, float(config.get("pass_weight", 0.5)), diagnostics)
    finally:
        model.train(was_training)


def evaluate_pass_at_n(model: Any, tokenizer: Any, dataset: Any, config: dict[str, Any], evaluation_name: str = "evaluation") -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Generate a batched candidate pool per task and report cumulative pass-at-N metrics."""
    import torch

    # Keep evaluation deterministic while allowing independent sampled candidates.
    was_training = bool(model.training)
    model.eval()
    records = [dataset[index] for index in range(len(dataset))]
    candidate_count = max(1, int(config.get("evaluation_num_completions", 16)))
    pass_counts = {n: 0 for n in (1, 2, 4, 8, 16) if n <= candidate_count}
    details: list[dict[str, Any]] = []
    rewards: list[float] = []
    try:
        # Generate all candidates for each task in one batched model call.
        for record in records:
            prompts = [str(record["prompt"])] * candidate_count
            inputs = _prepare_generation_batch(tokenizer, prompts, int(config.get("max_prompt_length", 512)), torch)
            inputs = {key: value.to(model.device) for key, value in inputs.items()}
            prompt_width = inputs["input_ids"].shape[-1]
            prefix_text = _interface_generation_prefix(tokenizer, record["test_code"], bool(config.get("include_generic_arguments", False)))
            with torch.no_grad():
                output = model.generate(
                    **inputs,
                    max_new_tokens=int(config.get("max_completion_length", 512)),
                    do_sample=bool(config.get("do_sample", False)),
                    **({"temperature": float(config["temperature"])} if config.get("do_sample", False) and config.get("temperature") is not None else {}),
                    logits_processor=[forced_code_prefix_processor(tokenizer, prompt_width, prefix_text)],
                    stopping_criteria=code_fence_stopping_criteria(tokenizer, prompt_width + forced_code_prefix_length(tokenizer, prefix_text)),
                )
            statuses: list[str] = []
            # Score every candidate independently and retain task-level audit records.
            for sample_index in range(candidate_count):
                completion = tokenizer.decode(output[sample_index, prompt_width:], skip_special_tokens=True)
                reward, score_details = score_completion(completion, record["test_code"], float(config.get("sandbox_timeout_seconds", 3)), float(config.get("pass_weight", 0.5)))
                rewards.append(reward)
                statuses.append(str(score_details["status"]))
                details.append({"task_id": record.get("task_id"), "sample_index": sample_index + 1, "raw_completion": completion, "completion": completion, "reward": reward, **score_details})
            # Count a task once when any of the first N candidates passes.
            for n in pass_counts:
                if "passed" in statuses[:n]:
                    pass_counts[n] += 1
        total = len(records)
        metrics = {
            "examples": total,
            "candidate_count": candidate_count,
            **{f"pass_at_{n}": count / total if total else 0.0 for n, count in pass_counts.items()},
            "average_reward": sum(rewards) / len(rewards) if rewards else 0.0,
            "successful_examples": pass_counts.get(1, 0),
        }
        return metrics, details
    finally:
        model.train(was_training)
