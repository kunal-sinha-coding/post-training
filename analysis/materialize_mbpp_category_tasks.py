"""Validate generated category tasks and derive their expected test outputs.

The script reads task specifications from the prompt agents, checks each reference
function and literal test call, executes each call in the repository subprocess
sandbox, and saves outputs plus executable assertions in a task JSONL artifact.
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

# Put the repository root on the import path when this file runs as a script.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sandbox import execute_code

def validate_reference(task: dict[str, Any]) -> ast.FunctionDef:
    """Require one plain function and literal calls to its declared entry point."""
    # Reject incomplete records before parsing generated Python.
    required = {"prompt_id", "category", "task_text", "entry_point", "reference_solution", "test_inputs"}
    if not required <= task.keys() or any(not task[key] for key in required):
        raise ValueError("task is missing a required field")
    # Require exactly one top-level plain function with the declared name.
    tree = ast.parse(task["reference_solution"])
    definitions = [node for node in tree.body if isinstance(node, ast.FunctionDef)]
    if len(tree.body) != 1 or len(definitions) != 1 or definitions[0].name != task["entry_point"]:
        raise ValueError("reference must define only the declared function")
    function = definitions[0]
    if function.decorator_list or function.args.vararg or function.args.kwarg:
        raise ValueError("reference function uses an unsupported signature")
    # Block imports, nested definitions, dynamic execution, and filesystem or network calls.
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom, ast.ClassDef, ast.AsyncFunctionDef, ast.Lambda)):
            raise ValueError("reference contains a disallowed definition or import")
        if isinstance(node, ast.Attribute) and node.attr.startswith("__"):
            raise ValueError("reference uses a dunder attribute")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in {"open", "eval", "exec", "compile", "input", "__import__", "print"}:
            raise ValueError("reference uses a disallowed built-in")
    # Ensure all three calls use literal inputs and invoke the declared function.
    if not isinstance(task["test_inputs"], list) or len(task["test_inputs"]) != 3:
        raise ValueError("test_inputs must contain exactly three calls")
    for expression in task["test_inputs"]:
        call = ast.parse(expression, mode="eval").body
        if not isinstance(call, ast.Call) or not isinstance(call.func, ast.Name) or call.func.id != task["entry_point"]:
            raise ValueError("each input must call the declared entry point")
        if any(isinstance(arg, ast.Starred) for arg in call.args):
            raise ValueError("starred arguments are not allowed")
        for value in [*call.args, *(keyword.value for keyword in call.keywords)]:
            ast.literal_eval(value)
    return function


def materialize_task(task: dict[str, Any], timeout_seconds: float) -> dict[str, Any]:
    """Run all literal inputs against the reference and create assertions."""
    # Validate the generated function and its three test calls before execution.
    validate_reference(task)
    expected_outputs = []
    assertions = []
    # Execute each reference call in its own timed sandbox subprocess.
    for expression in task["test_inputs"]:
        capture = f"print('__SYNTHETIC_OUTPUT__' + repr({expression}))"
        result = execute_code(task["reference_solution"], capture, timeout_seconds=timeout_seconds)
        if not result.passed:
            raise RuntimeError(f"reference failed on {expression}: {result.status}: {result.stderr[-1200:]}")
        lines = [line for line in result.stdout.splitlines() if line.startswith("__SYNTHETIC_OUTPUT__")]
        if len(lines) != 1:
            raise RuntimeError(f"reference returned an invalid capture for {expression}")
        output_repr = lines[0].removeprefix("__SYNTHETIC_OUTPUT__")
        expected = ast.literal_eval(output_repr)
        if repr(expected) != output_repr:
            raise RuntimeError(f"reference output is not a stable Python literal: {output_repr}")
        expected_outputs.append(output_repr)
        assertions.append(f"assert {expression} == {output_repr}")
    # Keep the prompt inputs and computed results with the task for later audit.
    return {**task, "expected_outputs": expected_outputs, "tests": assertions, "reference_status": "passed"}


def run(specs_path: Path, prompts_path: Path, output_path: Path, timeout_seconds: float) -> int:
    """Validate all task specs and save a complete materialized JSONL file."""
    # Index prompt metadata so each generated task keeps its original prompt provenance.
    prompt_lines = prompts_path.read_text(encoding="utf-8").splitlines()
    prompts = {row["prompt_id"]: row for line in prompt_lines if line.strip() for row in [json.loads(line)]}
    output_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    # Write to a temporary path so an invalid task cannot leave a partial result file.
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=output_path.parent, delete=False) as handle:
        temporary_path = Path(handle.name)
        try:
            with specs_path.open(encoding="utf-8") as specs:
                for line_number, line in enumerate(specs, start=1):
                    if not line.strip():
                        continue
                    task = json.loads(line)
                    prompt = prompts.get(task.get("prompt_id"))
                    if prompt is None or prompt["category"] != task.get("category"):
                        raise ValueError(f"line {line_number} has no matching category prompt")
                    materialized = materialize_task(task, timeout_seconds)
                    materialized["example_task_ids"] = prompt["example_task_ids"]
                    materialized["generation_model"] = "gpt-6-luna"
                    handle.write(json.dumps(materialized, ensure_ascii=False) + "\n")
                    count += 1
            # Replace the output only after every task has passed sandbox execution.
            os.replace(temporary_path, output_path)
        except Exception:
            temporary_path.unlink(missing_ok=True)
            raise
    return count


def parse_args() -> argparse.Namespace:
    """Parse input files, output file, and sandbox timeout."""
    # Keep the one-per-category preview paths as defaults for this runbook.
    parser = argparse.ArgumentParser(description="Materialize generated MBPP category tasks.")
    parser.add_argument("--specs", type=Path, default=ROOT / "analysis" / "mbpp_category_synthetic_task_specs.jsonl")
    parser.add_argument("--prompts", type=Path, default=ROOT / "analysis" / "mbpp_category_prompt_preview.jsonl")
    parser.add_argument("--output", type=Path, default=ROOT / "analysis" / "mbpp_category_synthetic_tasks_preview.jsonl")
    parser.add_argument("--timeout-seconds", type=float, default=5.0)
    return parser.parse_args()


if __name__ == "__main__":
    # Materialize every generated task and report the accepted count.
    args = parse_args()
    count = run(args.specs, args.prompts, args.output, args.timeout_seconds)
    print(f"Materialized {count} tasks to {args.output}", flush=True)
