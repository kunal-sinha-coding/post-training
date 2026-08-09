"""Small, timed subprocess sandbox for scoring generated Python code."""

from __future__ import annotations

import ast
import math
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path


OUTPUT_FORMAT_ERROR = "Did not follow proper output formatting"
# These markers identify reasoning tags that should not reach the Python parser.
THINK_TAGS = ["<think>", "</think>"]


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
    # Accept the legacy Code label or a fenced block that starts the continuation.
    match = re.search(r"(?:Code:\s*)?```(?:python|py)?\s*(.*?)```", text, flags=re.IGNORECASE | re.DOTALL)
    if match is None:
        raise ValueError(OUTPUT_FORMAT_ERROR)
    # Remove the legacy reasoning markers if they occur inside the extracted block.
    cleaned = match.group(1)
    for tag in THINK_TAGS:
        cleaned = cleaned.replace(tag, "")
    return cleaned.strip()


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


def score_completion(completion: str, tests: str, timeout_seconds: float = 3.0) -> tuple[float, dict[str, object]]:
    """Return the dense reward and diagnostics for one completion."""
    try:
        code = extract_code(completion)
    except ValueError:
        return 0.0, {"status": "format_error", "passed_tests": 0, "total_tests": 0}
    try:
        compile(code, "<candidate>", "exec")
    except SyntaxError:
        return 0.05, {"status": "syntax_error", "passed_tests": 0, "total_tests": 0}
    test_cases = split_test_cases(tests)
    passed, total, executed = execute_test_cases(code, test_cases, timeout_seconds)
    fraction = passed / total if total else 0.0
    reward = 0.05 + 0.10 + (0.05 if executed else 0.0) + 0.80 * fraction
    status = "passed" if passed == total else "partial" if passed else "failed"
    return reward, {"status": status, "passed_tests": passed, "total_tests": total}


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
    return {
        "reward/group_count": float(len(groups)),
        "reward/flat_group_fraction": flat_groups / len(groups),
        "reward/mixed_group_fraction": mixed_groups / len(groups),
        "reward/mean_group_std": sum(group_stds) / len(group_stds),
        "reward/all_zero_fraction": sum(reward == 0.0 for reward in rewards) / len(rewards),
        "reward/format_error_fraction": sum(detail["status"] == "format_error" for detail in details) / len(details),
        "reward/partial_test_fraction": passed_tests / total_tests if total_tests else 0.0,
        "reward/full_pass_fraction": sum(detail["status"] == "passed" for detail in details) / len(details),
        "reward/mean": sum(rewards) / len(rewards),
        "reward/min": min(rewards),
        "reward/max": max(rewards),
    }


def reward_function(completions: list[object], test_code: list[str], sandbox_timeout_seconds: float = 3.0, diagnostics: dict[str, float] | None = None, group_size: int = 4, **_: object) -> list[float]:
    """Score a GRPO batch with dense rewards and group diagnostics."""
    # Record candidate outcomes so reward sparsity is visible during training.
    rewards: list[float] = []
    details: list[dict[str, object]] = []
    for completion, tests in zip(completions, test_code):
        if isinstance(completion, list):
            text = "".join(str(part.get("text", "")) if isinstance(part, dict) else str(part) for part in completion)
        elif isinstance(completion, dict):
            text = str(completion.get("content", completion.get("text", "")))
        else:
            text = str(completion)
        reward, detail = score_completion(text, tests, sandbox_timeout_seconds)
        rewards.append(reward)
        details.append(detail)
    if diagnostics is not None:
        diagnostics.update(summarize_reward_groups(rewards, details, group_size))
    return rewards
