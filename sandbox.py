"""Extract generated Python, validate its interface, and execute each test in a timed subprocess.

The scoring flow builds explicit dense components, blends them with the binary pass signal,
and summarizes reward variation for local logs and W&B.
"""

from __future__ import annotations

import ast
import json
import math
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


OUTPUT_FORMAT_ERROR = "Did not follow proper output formatting"
# These markers identify reasoning tags that should not reach the Python parser.
THINK_TAGS = ["<think>", "</think>"]
INTERFACE_IGNORED_NAMES = {"bool", "float", "int", "len", "list", "print", "set", "sorted", "str", "sum", "tuple"}
DENSE_REWARD_WEIGHTS = {"format": 0.05, "syntax": 0.10, "interface": 0.05, "tests": 0.80}
DEFAULT_REWARD_FUNCTION = "test_pass"
DEFAULT_REWARD_COEFFICIENT = 0.5
QWEN_EVALPLUS_STOP_STRINGS = ("<|endoftext|>", "<|endofmask|>", "</s>", "\nif __name__", "\ndef main(", "\nprint(", "\n#", "```")


@dataclass
class ExecutionResult:
    """Represent the observable outcome of one candidate execution."""

    passed: bool
    status: str
    stdout: str = ""
    stderr: str = ""
    returncode: int | None = None

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable representation of the result."""
        return asdict(self)


def extract_code(text: str) -> str:
    """Extract code from a labeled or continuation-starting Markdown fence."""
    # Find the opening Python fence while preserving the existing Code-label requirement.
    opening = re.search(r"(?:Code:\s*)?```(?:python|py)?\s*", text, flags=re.IGNORECASE)
    if opening is None:
        raise ValueError(OUTPUT_FORMAT_ERROR)
    # Use the closing fence when present and otherwise retain the incomplete generated body.
    remainder = text[opening.end():]
    closing = remainder.find("```")
    cleaned = remainder if closing < 0 else remainder[:closing]
    # Remove the legacy reasoning markers if they occur inside the extracted block.
    for tag in THINK_TAGS:
        cleaned = cleaned.replace(tag, "")
    return cleaned.strip()


def truncate_qwen_completion(text: str) -> str:
    """Apply the official Qwen EvalPlus stop strings before reward scoring."""
    # Keep the first official stop marker so reward execution sees the same completion boundary as EvalPlus.
    positions = [text.find(stop) for stop in QWEN_EVALPLUS_STOP_STRINGS if text.find(stop) >= 0 and not (stop == "```" and text.lstrip().startswith("```"))]
    return text[:min(positions)] if positions else text


def wrap_qwen_continuation(text: str) -> str:
    """Wrap a raw Qwen continuation so the shared scorer can extract it as Python."""
    # Recreate the opening fence supplied by the prompt when generation returned only its body.
    return text if "```" in text else f"```python\n{text}"


def _safe_environment() -> dict[str, str]:
    """Build a minimal environment for the child Python process."""
    return {"PATH": os.environ.get("PATH", ""), "PYTHONIOENCODING": "utf-8"}


def execute_code(code: str, tests: str, timeout_seconds: float = 3.0) -> ExecutionResult:
    """Run candidate code and tests in a temporary timed subprocess."""
    if not code.strip():
        return ExecutionResult(False, "empty")
    with tempfile.TemporaryDirectory(prefix="grpo-mbpp-") as directory:
        script = Path(directory) / "candidate.py"
        script.write_text(f"{code}\n\n{tests}\n", encoding="utf-8")
        try:
            completed = subprocess.run(
                [sys.executable, "-I", str(script)],
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                cwd=directory,
                env=_safe_environment(),
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            return ExecutionResult(False, "timeout", str(exc.stdout or ""), str(exc.stderr or ""))
        status = "passed" if completed.returncode == 0 else "failed"
        if completed.returncode != 0 and "SyntaxError" in completed.stderr:
            status = "syntax_error"
        return ExecutionResult(status == "passed", status, completed.stdout, completed.stderr, completed.returncode)


def split_test_cases(tests: str) -> list[str]:
    """Split test imports and assertions into independently executable cases."""
    # Preserve shared setup before running each assertion in its own subprocess.
    tree = ast.parse(tests)
    assertions = [node for node in tree.body if isinstance(node, ast.Assert)]
    if not assertions:
        return [tests]
    setup = "\n".join(ast.unparse(node) for node in tree.body if not isinstance(node, ast.Assert))
    return ["\n".join(part for part in (setup, ast.unparse(assertion)) if part) for assertion in assertions]


def execute_test_cases(code: str, test_cases: list[str], timeout_seconds: float = 3.0) -> tuple[int, int, bool]:
    """Run each assertion independently and return progress and execution status."""
    # Run every assertion so partially correct candidates receive partial reward.
    passed = 0
    executed = False
    for test_case in test_cases:
        result = execute_code(code, test_case, timeout_seconds)
        if result.status == "syntax_error":
            return passed, len(test_cases), executed
        if result.passed:
            passed += 1
            executed = True
        elif "AssertionError" in result.stderr:
            executed = True
    return passed, len(test_cases), executed


def expected_interface(tests: str) -> tuple[str | None, set[int]]:
    """Infer the tested function name and positional arities from the assertions."""
    # Select the outer task call and ignore common helpers used around it.
    try:
        tree = ast.parse(tests)
    except SyntaxError:
        return None, set()
    calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id not in INTERFACE_IGNORED_NAMES]
    if not calls:
        return None, set()
    name = calls[0].func.id
    arities = {len(node.args) for node in calls if node.func.id == name}
    return name, arities


def validate_interface(code: str, tests: str) -> bool:
    """Check that the candidate exposes the exact function tested by MBPP."""
    # Compare the top-level definition with the calls found in the test assertions.
    expected_name, expected_arities = expected_interface(tests)
    if expected_name is None or len(expected_arities) != 1:
        return False
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return False
    definitions = [node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == expected_name]
    if len(definitions) != 1:
        return False
    function = definitions[0]
    positional_count = len(function.args.posonlyargs) + len(function.args.args)
    return not function.args.vararg and not function.args.kwarg and positional_count == next(iter(expected_arities))


def score_completion(completion: str, tests: str, timeout_seconds: float = 3.0, reward_function: str = DEFAULT_REWARD_FUNCTION, reward_coefficient: float = DEFAULT_REWARD_COEFFICIENT) -> tuple[float, dict[str, object]]:
    """Return the configured reward and diagnostics for one completion."""
    # Keep partial progress and complete correctness visible before selecting the scalar reward.
    components = {"format": 0.0, "syntax": 0.0, "interface": 0.0, "tests": 0.0, "pass": 0.0}
    if reward_function not in {"test_pass", "hybrid"}:
        raise ValueError("reward_function must be 'test_pass' or 'hybrid'.")
    if not 0.0 <= reward_coefficient <= 1.0:
        raise ValueError("reward_coefficient must be between zero and one.")
    try:
        code = extract_code(completion)
    except ValueError:
        return 0.0, {"status": "format_error", "passed_tests": 0, "total_tests": 0, "interface_valid": False, "reward_components": components}
    try:
        compile(code, "<candidate>", "exec")
    except SyntaxError:
        return sum(components.values()), {"status": "syntax_error", "passed_tests": 0, "total_tests": 0, "interface_valid": False, "reward_components": components}
    interface_valid = validate_interface(code, tests)
    test_cases = split_test_cases(tests)
    passed, total, _ = execute_test_cases(code, test_cases, timeout_seconds)
    fraction = passed / total if total else 0.0
    components["tests"] = fraction
    status = "passed" if passed == total else "partial" if passed else "failed"
    components["pass"] = float(passed == total and total > 0)
    reward = fraction if reward_function == "test_pass" else reward_coefficient * components["pass"] + (1.0 - reward_coefficient) * fraction
    return reward, {"status": status, "passed_tests": passed, "total_tests": total, "interface_valid": interface_valid, "reward_components": components}


def reward_for_completion(completion: str, tests: str, timeout_seconds: float = 3.0) -> float:
    """Return the dense reward for one completion."""
    # Preserve the simple scalar API used by existing callers and tests.
    return score_completion(completion, tests, timeout_seconds)[0]


def summarize_reward_groups(rewards: list[float], details: list[dict[str, object]], group_size: int = 4) -> dict[str, float]:
    """Summarize within-prompt reward variation for W&B and local logs."""
    # Group consecutive completions because GRPO emits one group per prompt.
    groups = [rewards[index : index + group_size] for index in range(0, len(rewards), group_size)]
    if not groups:
        return {}
    group_stds = []
    flat_groups = 0
    mixed_groups = 0
    for group in groups:
        mean = sum(group) / len(group)
        std = math.sqrt(sum((value - mean) ** 2 for value in group) / len(group))
        group_stds.append(std)
        flat_groups += int(std == 0.0)
        mixed_groups += int(std > 0.0)
    total_tests = sum(int(detail["total_tests"]) for detail in details)
    passed_tests = sum(int(detail["passed_tests"]) for detail in details)
    diagnostics = {
        "reward/group_count": float(len(groups)),
        "reward/flat_group_fraction": flat_groups / len(groups),
        "reward/mixed_group_fraction": mixed_groups / len(groups),
        "reward/mean_group_std": sum(group_stds) / len(group_stds),
        "reward/all_zero_fraction": sum(reward == 0.0 for reward in rewards) / len(rewards),
        "reward/format_error_fraction": sum(detail["status"] == "format_error" for detail in details) / len(details),
        "reward/interface_valid_fraction": sum(bool(detail.get("interface_valid", False)) for detail in details) / len(details),
        "reward/interface_error_fraction": sum(not bool(detail.get("interface_valid", False)) for detail in details) / len(details),
        "reward/partial_test_fraction": passed_tests / total_tests if total_tests else 0.0,
        "reward/full_pass_fraction": sum(detail["status"] == "passed" for detail in details) / len(details),
        "reward/mean": sum(rewards) / len(rewards),
        "reward/min": min(rewards),
        "reward/max": max(rewards),
    }
    # Emit mean, standard deviation, minimum, and maximum for every dense reward component.
    for component in ("format", "syntax", "interface", "test_progress", "pass"):
        values = [float(detail.get("reward_components", {}).get("tests" if component == "test_progress" else component, 0.0)) for detail in details]
        mean = sum(values) / len(values)
        std = math.sqrt(sum((value - mean) ** 2 for value in values) / len(values))
        diagnostics[f"reward/{component}/mean"] = mean
        diagnostics[f"reward/{component}/std"] = std
        diagnostics[f"reward/{component}/min"] = min(values)
        diagnostics[f"reward/{component}/max"] = max(values)
    return diagnostics


def reward_function(completions: list[object], test_code: list[str], sandbox_timeout_seconds: float = 3.0, diagnostics: dict[str, Any] | None = None, group_size: int = 4, reward_function_name: str = DEFAULT_REWARD_FUNCTION, reward_coefficient: float = DEFAULT_REWARD_COEFFICIENT, trace_path: str | None = None, task_ids: list[object] | None = None, **_: object) -> list[float]:
    """Score a GRPO batch with the configured test-pass or hybrid reward."""
    # Record candidate outcomes so reward variation remains visible during training.
    rewards: list[float] = []
    details: list[dict[str, object]] = []
    trace_records: list[dict[str, object]] = []
    for index, (completion, tests) in enumerate(zip(completions, test_code)):
        if isinstance(completion, list):
            text = "".join(str(part.get("text", "")) if isinstance(part, dict) else str(part) for part in completion)
        elif isinstance(completion, dict):
            text = str(completion.get("content", completion.get("text", "")))
        else:
            text = str(completion)
        truncated = truncate_qwen_completion(text)
        scored_text = wrap_qwen_continuation(truncated)
        reward, detail = score_completion(scored_text, tests, sandbox_timeout_seconds, reward_function_name, reward_coefficient)
        rewards.append(reward)
        details.append(detail)
        trace_records.append({
            "index": index,
            "task_id": str(task_ids[index]) if task_ids is not None and index < len(task_ids) else None,
            "raw_completion": text,
            "truncated_completion": truncated,
            "scored_completion": scored_text,
            "test_code": tests,
            "reward": reward,
            "detail": detail,
        })
    if trace_path:
        # Append one auditable JSON record for every scored sampled completion.
        trace_file = Path(trace_path)
        trace_file.parent.mkdir(parents=True, exist_ok=True)
        with trace_file.open("a", encoding="utf-8") as handle:
            for record in trace_records:
                handle.write(json.dumps(record, sort_keys=True) + "\n")
    if diagnostics is not None:
        diagnostics.update(summarize_reward_groups(rewards, details, group_size))
        diagnostics["reward/function"] = reward_function_name
        diagnostics["reward/coefficient"] = reward_coefficient
    return rewards
