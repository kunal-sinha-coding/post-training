"""Validate synthetic MBPP tests before training can load their artifact.

The flow reads JSON Lines records, checks their schema and declared input
constraints, verifies assertion structure against the original tests, executes
every generated assertion with the trusted reference implementation in an
isolated process, and emits a machine-readable summary with a failing exit code.
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REQUIRED_FIELDS = {"task_id", "test_code", "reference_code", "generated_tests", "constraints"}


@dataclass(frozen=True)
class ConstructorValue:
    """Represent a constructor call without executing dataset code."""

    name: str
    arguments: tuple[Any, ...]


def _assertion_parts(source: str) -> tuple[ast.Call, ast.expr]:
    """Parse one equality assertion and return its call and expected expression."""
    # Require exactly one assertion whose left side is a direct function call.
    body = ast.parse(source).body
    if len(body) != 1 or not isinstance(body[0], ast.Assert):
        raise ValueError("The test must contain exactly one assertion.")
    comparison = body[0].test
    if not isinstance(comparison, ast.Compare) or len(comparison.ops) != 1 or not isinstance(comparison.ops[0], ast.Eq):
        raise ValueError("The assertion must use one equality comparison.")
    if not isinstance(comparison.left, ast.Call) or not isinstance(comparison.left.func, ast.Name):
        raise ValueError("The assertion must call one named function on its left side.")
    return comparison.left, comparison.comparators[0]


def _node_type(node: ast.expr) -> str:
    """Return a stable structural type name for an argument expression."""
    # Use literal runtime types when possible and AST types for constructor calls.
    try:
        return type(ast.literal_eval(node)).__name__
    except (ValueError, TypeError):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            return f"call:{node.func.id}"
        return type(node).__name__


def _literal_arguments(call: ast.Call) -> list[Any]:
    """Evaluate literal positional arguments for declarative constraint checks."""
    # Reconstruct literals and named constructors without executing dataset code.
    def value(node: ast.expr) -> Any:
        """Convert one safe expression into a structural Python value."""
        # Preserve named constructor structure for records such as Pair objects.
        if isinstance(node, (ast.Name, ast.Attribute)):
            return ast.unparse(node)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and not node.keywords:
            return ConstructorValue(node.func.id, tuple(value(argument) for argument in node.args))
        if isinstance(node, ast.List):
            return [value(item) for item in node.elts]
        if isinstance(node, ast.Tuple):
            return tuple(value(item) for item in node.elts)
        if isinstance(node, ast.Set):
            return {value(item) for item in node.elts}
        if isinstance(node, ast.Dict):
            return {value(key): value(item) for key, item in zip(node.keys, node.values) if key is not None}
        try:
            return ast.literal_eval(node)
        except (ValueError, TypeError) as error:
            raise ValueError("Constraints require literals or named constructor calls.") from error

    # Convert each positional input independently.
    return [value(argument) for argument in call.args]


def _check_constraint(constraint: dict[str, Any], arguments: list[Any]) -> str | None:
    """Return an error when one declared constraint is violated."""
    # Resolve argument indices through one checked accessor.
    def argument(key: str = "arg") -> Any:
        index = constraint.get(key)
        if not isinstance(index, int) or index < 0 or index >= len(arguments):
            raise ValueError(f"Constraint field {key!r} must name a valid argument index.")
        return arguments[index]

    # Validate one supported relationship or domain restriction.
    kind = constraint.get("type")
    if kind == "fixture_tree":
        return None
    if kind == "arg_type":
        expected = constraint.get("type_name", constraint.get("value"))
        if expected is None:
            expected = constraint.get("expected")
        actual = f"call:{argument().name}" if isinstance(argument(), ConstructorValue) else type(argument()).__name__
        if actual != expected:
            return "arg_type"
    elif kind == "length_equals":
        if len(argument("container")) != argument("scalar"):
            return "length_equals"
    elif kind == "equal_lengths":
        indices = constraint.get("args")
        if not isinstance(indices, list) or not indices:
            raise ValueError("equal_lengths requires a nonempty arguments list.")
        lengths = [len(arguments[index]) for index in indices]
        if len(set(lengths)) != 1:
            return "equal_lengths"
    elif kind == "nonempty":
        if len(argument()) == 0:
            return "nonempty"
    elif kind == "positive":
        if argument() <= 0:
            return "positive"
    elif kind == "nonnegative":
        if argument() < 0:
            return "nonnegative"
    elif kind == "nonzero":
        if argument() == 0:
            return "nonzero"
    elif kind == "sorted":
        value = argument()
        if list(value) != sorted(value):
            return "sorted"
    elif kind == "rectangular":
        matrix = argument()
        if not matrix or any(not isinstance(row, (list, tuple)) for row in matrix) or len({len(row) for row in matrix}) != 1:
            return "rectangular"
    elif kind == "square":
        matrix = argument()
        if not matrix or any(not isinstance(row, (list, tuple)) or len(row) != len(matrix) for row in matrix):
            return "square"
    elif kind == "one_based_index":
        index = argument("index")
        size = len(argument("container"))
        if not 1 <= index <= size:
            return "one_based_index"
    elif kind == "zero_based_index":
        index = argument("index")
        size = len(argument("container"))
        if not 0 <= index < size:
            return "zero_based_index"
    elif kind == "none_output_allowed":
        if not isinstance(constraint.get("allowed"), bool):
            raise ValueError("none_output_allowed requires a Boolean allowed field.")
    else:
        raise ValueError(f"Unsupported constraint type: {kind!r}.")
    return None


def _oracle_results(reference_code: str, tests: list[str], timeout_seconds: float) -> list[str | None]:
    """Run each generated assertion with the reference implementation in isolation."""
    # Run every assertion in its own child so global state cannot leak between tests.
    results: list[str | None] = []
    with tempfile.TemporaryDirectory(prefix="mbpp-validation-") as directory:
        environment = {"PATH": os.environ.get("PATH", ""), "PYTHONIOENCODING": "utf-8"}
        for index, test in enumerate(tests):
            child = reference_code + "\n" + test + "\n"
            script = Path(directory) / f"validate_{index}.py"
            script.write_text(child, encoding="utf-8")
            try:
                completed = subprocess.run(
                    [sys.executable, "-I", str(script)], capture_output=True, text=True, timeout=timeout_seconds,
                    cwd=directory, env=environment, check=False,
                )
            except subprocess.TimeoutExpired:
                results.append("TimeoutExpired")
                continue
            if completed.returncode == 0:
                results.append(None)
            else:
                detail = completed.stderr.strip().splitlines()[-1] if completed.stderr.strip() else "ReferenceError"
                results.append(detail)
    return results


def validate_record(record: dict[str, Any], tests_per_task: int, timeout_seconds: float = 5.0) -> list[dict[str, Any]]:
    """Validate one artifact record and return all detected errors."""
    # Record errors with task and test context for an auditable JSON report.
    task_id = record.get("task_id")
    errors: list[dict[str, Any]] = []

    def add(code: str, detail: str, test_index: int | None = None) -> None:
        """Append one structured validation error."""
        # Preserve the task and optional generated-test position.
        error = {"task_id": task_id, "code": code, "detail": detail}
        if test_index is not None:
            error["test_index"] = test_index
        errors.append(error)

    # Reject incomplete records before inspecting dependent fields.
    missing = sorted(REQUIRED_FIELDS - record.keys())
    if missing:
        add("record_shape", f"Missing required fields: {', '.join(missing)}.")
        return errors
    generated = record["generated_tests"]
    constraints = record["constraints"]
    if not isinstance(generated, list) or not all(isinstance(test, str) for test in generated):
        add("record_shape", "generated_tests must be a list of strings.")
        return errors
    if not isinstance(constraints, list) or not all(isinstance(item, dict) for item in constraints):
        add("record_shape", "constraints must be a list of objects.")
        return errors
    if len(generated) != tests_per_task:
        add("test_count", f"Expected {tests_per_task} generated tests but found {len(generated)}.")
    generation = record.get("generation")
    if not isinstance(generation, dict) or generation.get("requested_test_count") != tests_per_task:
        add("requested_count", "generation.requested_test_count must equal the validated test count.")

    # Derive the expected function signature and argument shapes from originals.
    try:
        original_module = ast.parse(str(record["test_code"]))
        original_parts = []
        for node in original_module.body:
            if isinstance(node, ast.Assert):
                original_parts.append(_assertion_parts(ast.unparse(node)))
    except (SyntaxError, ValueError) as error:
        add("original_test", str(error))
        return errors
    if not original_parts:
        add("original_test", "No original equality assertion was found.")
        return errors
    original_call = original_parts[0][0]
    expected_function = original_call.func.id
    expected_arity = (len(original_call.args), tuple(keyword.arg for keyword in original_call.keywords))
    expected_types = [set() for _ in original_call.args]
    for call, _ in original_parts:
        if len(call.args) == len(expected_types):
            for index, argument in enumerate(call.args):
                expected_types[index].add(_node_type(argument))
    originals_expect_none = any(isinstance(expected, ast.Constant) and expected.value is None for _, expected in original_parts)
    declared_none = [constraint.get("allowed") for constraint in constraints if constraint.get("type") == "none_output_allowed"]
    if declared_none != [originals_expect_none]:
        add("none_constraint", "none_output_allowed must be declared once and match the original tests.")

    # Parse every assertion and check signature, types, uniqueness, and constraints.
    parsed_calls: list[ast.Call | None] = []
    seen: set[str] = set()
    for index, source in enumerate(generated):
        try:
            call, expected = _assertion_parts(source)
        except (SyntaxError, ValueError) as error:
            add("assertion_shape", str(error), index)
            parsed_calls.append(None)
            continue
        canonical = ast.dump(ast.parse(source), include_attributes=False)
        if canonical in seen:
            add("duplicate", "The generated assertion duplicates an earlier assertion.", index)
        seen.add(canonical)
        if call.func.id != expected_function:
            add("function", f"Expected {expected_function!r} but found {call.func.id!r}.", index)
        if (len(call.args), tuple(keyword.arg for keyword in call.keywords)) != expected_arity:
            add("arity", "The positional or keyword argument shape differs from the original tests.", index)
        fixture_args = {constraint.get("arg") for constraint in constraints if constraint.get("type") == "fixture_tree"}
        if len(call.args) == len(expected_types) and any(position not in fixture_args and _node_type(argument) not in expected_types[position] for position, argument in enumerate(call.args)):
            add("argument_types", "The positional argument types differ from the original tests.", index)
        if isinstance(expected, ast.Constant) and expected.value is None and not originals_expect_none:
            add("accidental_none", "The generated expected value is None but no original expects None.", index)
        try:
            arguments = _literal_arguments(call)
            for constraint in constraints:
                violation = _check_constraint(constraint, arguments)
                if violation:
                    add("constraint", f"The {violation} constraint failed.", index)
        except (TypeError, ValueError, IndexError) as error:
            add("constraint_definition", str(error), index)
        parsed_calls.append(call)

    # Execute every syntactically valid assertion against the trusted reference.
    oracle_sources = [source for source, call in zip(generated, parsed_calls) if call is not None]
    oracle_indices = [index for index, call in enumerate(parsed_calls) if call is not None]
    for index, result in zip(oracle_indices, _oracle_results("\n".join(part for part in [str(record.get("reference_code", "")), str(record.get("test_setup_code", ""))] if part), oracle_sources, timeout_seconds)):
        if result is not None:
            add("oracle", result, index)
    return errors


def validate_artifact(path: Path, tests_per_task: int, timeout_seconds: float = 5.0) -> dict[str, Any]:
    """Validate every JSON Lines record and return a complete summary."""
    # Read every line independently so malformed JSON receives its own error.
    errors: list[dict[str, Any]] = []
    records = 0
    with path.open(encoding="utf-8") as source:
        for line_number, line in enumerate(source, start=1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
                if not isinstance(record, dict):
                    raise ValueError("The JSON value is not an object.")
            except (json.JSONDecodeError, ValueError) as error:
                errors.append({"task_id": None, "code": "json", "detail": str(error), "line": line_number})
                continue
            records += 1
            errors.extend(validate_record(record, tests_per_task, timeout_seconds))

    # Aggregate status and error counts for command-line consumers.
    counts: dict[str, int] = {}
    for error in errors:
        code = str(error["code"])
        counts[code] = counts.get(code, 0) + 1
    return {"valid": not errors, "record_count": records, "error_count": len(errors), "error_counts": counts, "errors": errors}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse artifact validation command-line options."""
    # Expose strict count, timeout, and optional summary file settings.
    parser = argparse.ArgumentParser(description="Validate generated MBPP tests before training.")
    parser.add_argument("artifact", type=Path)
    parser.add_argument("--tests-per-task", type=int, default=5)
    parser.add_argument("--timeout-seconds", type=float, default=5.0)
    parser.add_argument("--summary", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Validate an artifact, print JSON, and return a strict status code."""
    # Reject nonsensical numeric options before reading the artifact.
    args = parse_args(argv)
    if args.tests_per_task < 0 or args.timeout_seconds <= 0:
        raise ValueError("tests-per-task must be nonnegative and timeout-seconds must be positive.")
    summary = validate_artifact(args.artifact, args.tests_per_task, args.timeout_seconds)
    rendered = json.dumps(summary, indent=2, sort_keys=True)
    print(rendered)

    # Optionally persist the same machine-readable summary.
    if args.summary:
        args.summary.parent.mkdir(parents=True, exist_ok=True)
        args.summary.write_text(rendered + "\n", encoding="utf-8")
    return 0 if summary["valid"] else 1


if __name__ == "__main__":
    # Return validation status through the standard command-line entry point.
    raise SystemExit(main())
