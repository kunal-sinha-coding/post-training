"""Small, timed subprocess sandbox for scoring generated Python code."""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path


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
    """Extract Python from reasoning blocks, fences, or a plain response."""
    # Remove complete reasoning blocks before looking for executable code.
    block_pattern = rf"{re.escape(THINK_TAGS[0])}.*?{re.escape(THINK_TAGS[1])}"
    cleaned = re.sub(block_pattern, "", text, flags=re.DOTALL | re.IGNORECASE)
    # Remove an unfinished reasoning block so its contents cannot cause a syntax error.
    cleaned = re.sub(rf"{re.escape(THINK_TAGS[0])}.*$", "", cleaned, flags=re.DOTALL | re.IGNORECASE)
    # Remove any remaining standalone reasoning markers from the response.
    for tag in THINK_TAGS:
        cleaned = cleaned.replace(tag, "")
    # Extract a fenced Python response when the model adds Markdown formatting.
    match = re.search(r"```(?:python|py)?\s*(.*?)```", cleaned, flags=re.IGNORECASE | re.DOTALL)
    return (match.group(1) if match else cleaned).strip()


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


def reward_for_completion(completion: str, tests: str, timeout_seconds: float = 3.0) -> float:
    """Return one for a passing candidate and zero for every other outcome."""
    return float(execute_code(extract_code(completion), tests, timeout_seconds).passed)


def reward_function(completions: list[object], test_code: list[str], sandbox_timeout_seconds: float = 3.0, **_: object) -> list[float]:
    """Score a GRPO batch using the supplied MBPP tests."""
    rewards: list[float] = []
    for completion, tests in zip(completions, test_code):
        if isinstance(completion, list):
            text = "".join(str(part.get("text", "")) if isinstance(part, dict) else str(part) for part in completion)
        elif isinstance(completion, dict):
            text = str(completion.get("content", completion.get("text", "")))
        else:
            text = str(completion)
        rewards.append(reward_for_completion(text, tests, sandbox_timeout_seconds))
    return rewards
