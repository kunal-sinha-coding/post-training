"""Generate deterministic hidden tests for MBPP with an isolated reference oracle.

The flow loads each official training record, parses literal function calls from its
assertions, mutates their inputs without changing task semantics, evaluates all
candidate calls in one isolated subprocess, and writes accepted assertions and
generation metadata as JSON Lines.
"""

from __future__ import annotations

import argparse
import ast
import json
import math
import os
import random
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

# Support both module imports and direct script execution from the repository.
try:
    from synthetic_data.constraints import infer_constraints, validate_call
except ModuleNotFoundError:
    from constraints import infer_constraints, validate_call


DEFAULT_OUTPUT = Path(__file__).with_name("mbpp_train_tests.jsonl")


def extract_literal_calls(test_code: str) -> list[ast.Call]:
    """Extract direct function calls whose arguments are Python literals."""
    # Parse only complete equality assertions with a direct call on the left.
    calls: list[ast.Call] = []
    for node in ast.parse(test_code).body:
        if not isinstance(node, ast.Assert) or not isinstance(node.test, ast.Compare):
            continue
        comparison = node.test
        if len(comparison.ops) != 1 or not isinstance(comparison.ops[0], ast.Eq) or not isinstance(comparison.left, ast.Call):
            continue
        call = comparison.left
        if not isinstance(call.func, ast.Name):
            continue

        # Accept literals and constructor calls whose leaves are literals.
        def supported(node: ast.AST) -> bool:
            """Accept literal syntax and named constructors without executable expressions."""
            if isinstance(node, ast.Call):
                return isinstance(node.func, ast.Name) and all(supported(item) for item in node.args) and all(item.arg is not None and supported(item.value) for item in node.keywords)
            if isinstance(node, ast.Name):
                return False
            return all(supported(child) for child in ast.iter_child_nodes(node)) if not isinstance(node, (ast.Constant, ast.Load)) else True

        if not all(supported(argument) for argument in call.args) or not all(keyword.arg is not None and supported(keyword.value) for keyword in call.keywords):
            continue
        calls.append(call)
    return calls


def _unique_values(values: list[Any]) -> list[Any]:
    """Return values in stable order after deduplicating their representations."""
    # Use representations because nested containers are not always hashable.
    unique: list[Any] = []
    seen: set[str] = set()
    for value in values:
        key = repr(value)
        if key not in seen:
            seen.add(key)
            unique.append(value)
    return unique


def mutation_options(value: Any, rng: random.Random) -> list[Any]:
    """Create deterministic type-aware alternatives for one literal value."""
    # Mutate booleans before integers because bool is an int subclass.
    if isinstance(value, bool):
        return [not value]

    # Explore boundaries, nearby values, scale changes, and sign changes for integers.
    if isinstance(value, int):
        delta = rng.randint(1, max(2, abs(value) + 1))
        nearby = [value + offset for offset in range(-24, 25) if offset]
        scaled = [value * factor for factor in range(2, 7)]
        return _unique_values([0, 1, -1, value + 1, value - 1, value + delta, value - delta, -value, value * 2, *nearby, *scaled])

    # Explore finite nearby and scaled values for floating point inputs.
    if isinstance(value, float) and math.isfinite(value):
        delta = rng.choice([0.5, 1.0, 2.0])
        return _unique_values([0.0, 1.0, -1.0, value + delta, value - delta, -value, value * 2.0])

    # Explore length, order, casing, whitespace, and punctuation for strings.
    if isinstance(value, str):
        middle = value[len(value) // 2 :] if value else "x"
        options = ["", value[:1], middle, value[::-1], value.lower(), value.upper(), value + value, f" {value} ", f"{value}!"]

        # Add stable rotations and character substitutions for wider same-type coverage.
        for offset in range(1, max(2, len(value))):
            options.append(value[offset:] + value[:offset])
        alphabet = "aA0_x- !"
        for index in range(max(1, len(value))):
            for character in alphabet:
                base = value or "x"
                options.append(base[:index] + character + base[index + 1 :])
        return _unique_values(options)

    # Preserve list representation while varying size, order, and one nested value.
    if isinstance(value, list):
        options: list[Any] = [[], value[:1], value[-1:], list(reversed(value)), value + value[:1]]
        if value:
            for replacement in mutation_options(value[0], rng)[:3]:
                options.append([replacement, *value[1:]])
        try:
            options.append(sorted(value))
        except TypeError:
            pass
        return _unique_values(options)

    # Preserve tuple representation while applying the list mutation strategy.
    if isinstance(value, tuple):
        return _unique_values([tuple(option) for option in mutation_options(list(value), rng)])

    # Preserve dictionary representation while varying membership and one value.
    if isinstance(value, dict):
        items = list(value.items())
        options = [{}, dict(items[:1]), dict(reversed(items))]
        if items:
            key, item_value = items[0]
            for replacement in mutation_options(item_value, rng)[:3]:
                options.append({**value, key: replacement})
        return _unique_values(options)

    # Preserve set representation while varying membership when its values are supported.
    if isinstance(value, set):
        items = sorted(value, key=repr)
        options = [set(), set(items[:1]), set(items[1:]), set(items)]
        return _unique_values(options)
    return []


def _literal_node(value: Any) -> ast.expr:
    """Convert a supported Python value into an expression node."""
    # Parse repr so tuples, sets, dictionaries, and nested containers remain literals.
    return ast.parse(repr(value), mode="eval").body


def _constant_paths(node: ast.AST, path: tuple[tuple[str, int | None], ...] = ()) -> list[tuple[tuple[str, int | None], ...]]:
    """Return paths to mutable literal leaves while preserving container shapes."""
    # Treat booleans, numbers, and strings as the only directly mutable leaves.
    if isinstance(node, ast.Constant) and isinstance(node.value, (bool, int, float, str)):
        return [path]
    paths: list[tuple[tuple[str, int | None], ...]] = []
    for field, value in ast.iter_fields(node):
        if isinstance(value, list):
            for index, child in enumerate(value):
                if isinstance(child, ast.AST):
                    paths.extend(_constant_paths(child, path + ((field, index),)))
        elif isinstance(value, ast.AST):
            paths.extend(_constant_paths(value, path + ((field, None),)))
    return paths


def _replace_path(node: ast.AST, path: tuple[tuple[str, int | None], ...], replacement: ast.expr) -> None:
    """Replace one selected literal leaf in a copied call tree."""
    # Walk to the parent node and update its field or list entry.
    current = node
    for field, index in path[:-1]:
        current = getattr(current, field) if index is None else getattr(current, field)[index]
    field, index = path[-1]
    if index is None:
        setattr(current, field, replacement)
    else:
        getattr(current, field)[index] = replacement


def generate_candidate_calls(calls: list[ast.Call], limit: int, seed: int, constraints: list[dict[str, Any]] | None = None) -> list[str]:
    """Generate unique shape-preserving calls that satisfy inferred constraints."""
    # Seed a local generator so task processing order cannot change the output.
    import copy

    rng = random.Random(seed)
    candidates: list[str] = []
    seen = {ast.unparse(call) for call in calls}
    active_constraints = constraints or []

    # Mutate literal leaves individually so lengths, matrix shapes, and arity remain fixed.
    for call in calls:
        for path in _constant_paths(call):
            original = copy.deepcopy(call)
            current: ast.AST = original
            for field, index in path:
                current = getattr(current, field) if index is None else getattr(current, field)[index]
            options = mutation_options(current.value, rng) if isinstance(current, ast.Constant) else []
            parent: ast.AST = call
            for field, index in path[:-1]:
                parent = getattr(parent, field) if index is None else getattr(parent, field)[index]
            if isinstance(parent, ast.UnaryOp):
                options = [abs(option) if type(option) in (int, float) else option for option in options]
            rng.shuffle(options)
            for option in options:
                mutated = copy.deepcopy(call)
                _replace_path(mutated, path, _literal_node(option))
                if validate_call(active_constraints, mutated):
                    continue
                source = ast.unparse(ast.fix_missing_locations(mutated))
                if source not in seen:
                    seen.add(source)
                    candidates.append(source)

    # Shuffle all valid mutations to balance coverage across official assertions.
    rng.shuffle(candidates)
    return candidates[: max(limit * 10, limit)]


def _safe_environment() -> dict[str, str]:
    """Build the minimal environment used by the isolated oracle process."""
    # Preserve only executable discovery and deterministic Unicode output.
    return {"PATH": os.environ.get("PATH", ""), "PYTHONIOENCODING": "utf-8"}


def run_reference_oracle(reference_code: str, calls: list[str], timeout_seconds: float) -> list[dict[str, Any]]:
    """Evaluate each candidate twice in its own isolated reference subprocess."""
    # Isolate candidates so a timeout or global mutation cannot poison later tests.
    results: list[dict[str, Any]] = []
    for source in calls:
        child = f"""import ast\nimport json\nfrom collections.abc import Mapping\n\n{reference_code}\n\ntry:\n    first = eval({source!r})\n    second = eval({source!r})\n    rendered_value = dict(first) if isinstance(first, Mapping) else first\n    second_value = dict(second) if isinstance(second, Mapping) else second\n    rendered = repr(rendered_value)\n    ast.literal_eval(rendered)\n    ok = first is not None and rendered_value == second_value and repr(second_value) == rendered\n    result = {{"ok": ok, "output_repr": rendered}}\n    if not ok:\n        result["error"] = "NoneResult" if first is None else "UnstableResult"\n    print(json.dumps(result))\nexcept BaseException as error:\n    print(json.dumps({{"ok": False, "error": type(error).__name__}}))\n"""

        # Run one candidate in a fresh temporary directory and minimal environment.
        with tempfile.TemporaryDirectory(prefix="mbpp-test-oracle-") as directory:
            script = Path(directory) / "oracle.py"
            script.write_text(child, encoding="utf-8")
            try:
                completed = subprocess.run([sys.executable, "-I", str(script)], capture_output=True, text=True, timeout=timeout_seconds, cwd=directory, env=_safe_environment(), check=False)
            except subprocess.TimeoutExpired:
                results.append({"ok": False, "error": "TimeoutExpired"})
                continue

        # Decode only the final protocol line because reference functions may print output.
        try:
            result = json.loads(completed.stdout.strip().splitlines()[-1]) if completed.returncode == 0 else {"ok": False, "error": "ReferenceError"}
        except (IndexError, json.JSONDecodeError):
            result = {"ok": False, "error": "ProtocolError"}
        results.append(result)
    return results


def augment_record(record: dict[str, Any], tests_per_task: int = 20, seed: int = 42, timeout_seconds: float = 3.0) -> dict[str, Any]:
    """Add validated generated assertions and metadata to one normalized record."""
    # Derive a stable per-task seed so records can be generated independently.
    task_id = record.get("task_id")
    task_seed = seed + sum(ord(character) for character in str(task_id))
    calls = extract_literal_calls(str(record.get("test_code", "")))
    constraints = infer_constraints(calls, str(record.get("text", record.get("prompt", ""))))
    original_module = ast.parse(str(record.get("test_code", "")))
    originals_expect_none = any(isinstance(node, ast.Assert) and isinstance(node.test, ast.Compare) and isinstance(node.test.comparators[0], ast.Constant) and node.test.comparators[0].value is None for node in original_module.body)
    for constraint in constraints:
        if constraint.get("type") == "none_output_allowed":
            constraint["allowed"] = originals_expect_none
    candidates = generate_candidate_calls(calls, tests_per_task, task_seed, constraints)

    # Reuse declared fixture subtrees for the sole nonliteral binary-tree task.
    if not calls and "binary tree" in str(record.get("prompt", "")).lower():
        original_module = ast.parse(str(record.get("test_code", "")))
        original_calls = [node.test.left for node in original_module.body if isinstance(node, ast.Assert) and isinstance(node.test, ast.Compare) and isinstance(node.test.left, ast.Call)]
        function_name = original_calls[0].func.id if original_calls and isinstance(original_calls[0].func, ast.Name) else ""
        setup_module = ast.parse(str(record.get("test_setup_code", "")))
        fixture_targets = [ast.unparse(node.targets[0]) for node in setup_module.body if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Attribute)]
        candidates = [f"{function_name}({target})" for target in dict.fromkeys(fixture_targets)][: max(tests_per_task * 10, tests_per_task)]
        constraints = [{"type": "fixture_tree", "arg": 0}, {"type": "none_output_allowed", "allowed": False}]
    reference_code = "\n".join(part for part in [str(record.get("reference_code", "")), str(record.get("test_setup_code", ""))] if part)
    results = run_reference_oracle(reference_code, candidates, timeout_seconds) if candidates else []

    # Keep only stable oracle results and format them as ordinary assertions.
    generated_tests: list[str] = []
    rejection_counts: dict[str, int] = {}
    for call, result in zip(candidates, results):
        if bool(result.get("ok")):
            generated_tests.append(f"assert {call} == {result['output_repr']}")
            if len(generated_tests) == tests_per_task:
                break
        else:
            reason = str(result.get("error", "UnstableResult"))
            rejection_counts[reason] = rejection_counts.get(reason, 0) + 1

    # Fail closed when the requested exact coverage cannot be generated safely.
    if len(generated_tests) != tests_per_task:
        raise ValueError(f"Task {task_id} generated {len(generated_tests)} of {tests_per_task} required tests.")

    # Preserve source fields and attach auditable constraints and generation details.
    augmented = dict(record)
    augmented["constraints"] = constraints
    augmented["generated_tests"] = generated_tests
    augmented["generation"] = {
        "seed": task_seed,
        "requested_test_count": tests_per_task,
        "candidate_test_count": len(candidates),
        "accepted_test_count": len(generated_tests),
        "rejection_counts": rejection_counts,
    }
    return augmented


def write_jsonl(records: Any, output_path: Path, tests_per_task: int, seed: int, timeout_seconds: float, resume: bool = False) -> None:
    """Augment records while optionally preserving completed task records."""
    # Load completed identifiers before appending to an interrupted artifact.
    completed: set[str] = set()
    if resume and output_path.exists():
        with output_path.open(encoding="utf-8") as existing:
            completed = {str(json.loads(line)["task_id"]) for line in existing if line.strip()}

    # Create the parent directory before streaming remaining records.
    output_path.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if resume else "w"
    with output_path.open(mode, encoding="utf-8") as output:
        for record in records:
            if str(record.get("task_id")) in completed:
                continue
            augmented = augment_record(dict(record), tests_per_task, seed, timeout_seconds)
            output.write(json.dumps(augmented, sort_keys=True) + "\n")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command line options for dataset loading and generation."""
    # Keep defaults aligned with the official MBPP training experiment.
    parser = argparse.ArgumentParser(description="Generate reference-validated hidden MBPP tests.")
    parser.add_argument("--dataset-name", default="google-research-datasets/mbpp")
    parser.add_argument("--dataset-config", default=None)
    parser.add_argument("--split", default="train")
    parser.add_argument("--tests-per-task", type=int, default=5)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--timeout-seconds", type=float, default=3.0)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--resume", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Load MBPP and write generated hidden tests to JSON Lines."""
    # Validate options before importing the optional dataset dependency.
    args = parse_args(argv)
    if args.tests_per_task < 0:
        raise ValueError("The number of tests per task cannot be negative.")
    if args.timeout_seconds <= 0:
        raise ValueError("The timeout must be positive.")

    # Add the repository root so direct script execution can import the data loader.
    repository_root = str(Path(__file__).resolve().parents[1])
    if repository_root not in sys.path:
        sys.path.insert(0, repository_root)

    # Reuse the repository loader so output records match the training schema.
    from data import load_mbpp

    records = load_mbpp(args.dataset_name, args.dataset_config, args.split)
    write_jsonl(records, args.output, args.tests_per_task, args.seed, args.timeout_seconds, args.resume)
    return 0


if __name__ == "__main__":
    # Return the process status through the standard command line entry point.
    raise SystemExit(main())
