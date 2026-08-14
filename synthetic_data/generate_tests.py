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

        # Reject calls that cannot be reconstructed safely from literal values.
        try:
            for argument in call.args:
                ast.literal_eval(argument)
            for keyword in call.keywords:
                if keyword.arg is None:
                    raise ValueError("Expanded keyword arguments are unsupported.")
                ast.literal_eval(keyword.value)
        except (ValueError, TypeError):
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
        return _unique_values([0, 1, -1, value + 1, value - 1, value + delta, value - delta, -value, value * 2])

    # Explore finite nearby and scaled values for floating point inputs.
    if isinstance(value, float) and math.isfinite(value):
        delta = rng.choice([0.5, 1.0, 2.0])
        return _unique_values([0.0, 1.0, -1.0, value + delta, value - delta, -value, value * 2.0])

    # Explore length, order, casing, whitespace, and punctuation for strings.
    if isinstance(value, str):
        middle = value[len(value) // 2 :] if value else "x"
        return _unique_values(["", value[:1], middle, value[::-1], value.lower(), value.upper(), value + value, f" {value} ", f"{value}!"])

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


def generate_candidate_calls(calls: list[ast.Call], limit: int, seed: int) -> list[str]:
    """Generate unique mutated calls in deterministic seeded order."""
    # Seed a local generator so task processing order cannot change the output.
    rng = random.Random(seed)
    candidates: list[str] = []
    seen = {ast.unparse(call) for call in calls}

    # Mutate one positional argument at a time to stay near the demonstrated domain.
    for call in calls:
        for index, argument in enumerate(call.args):
            value = ast.literal_eval(argument)
            options = mutation_options(value, rng)
            rng.shuffle(options)
            for replacement in options:
                mutated = ast.Call(func=call.func, args=list(call.args), keywords=list(call.keywords))
                mutated.args[index] = _literal_node(replacement)
                source = ast.unparse(ast.fix_missing_locations(mutated))
                if source not in seen:
                    seen.add(source)
                    candidates.append(source)

        # Mutate one keyword argument at a time with the same conservative policy.
        for index, keyword in enumerate(call.keywords):
            value = ast.literal_eval(keyword.value)
            options = mutation_options(value, rng)
            rng.shuffle(options)
            for replacement in options:
                keywords = [ast.keyword(arg=item.arg, value=item.value) for item in call.keywords]
                keywords[index].value = _literal_node(replacement)
                mutated = ast.Call(func=call.func, args=list(call.args), keywords=keywords)
                source = ast.unparse(ast.fix_missing_locations(mutated))
                if source not in seen:
                    seen.add(source)
                    candidates.append(source)

    # Shuffle all mutations to avoid always favoring the first original assertion.
    rng.shuffle(candidates)
    return candidates[: max(limit * 5, limit)]


def _safe_environment() -> dict[str, str]:
    """Build the minimal environment used by the isolated oracle process."""
    # Preserve only executable discovery and deterministic Unicode output.
    return {"PATH": os.environ.get("PATH", ""), "PYTHONIOENCODING": "utf-8"}


def run_reference_oracle(reference_code: str, calls: list[str], timeout_seconds: float) -> list[dict[str, Any]]:
    """Evaluate a batch of calls twice in one isolated reference subprocess."""
    # Build a child program that reports stable representable values as JSON.
    child = f'''import ast
import json

{reference_code}

calls = json.loads({json.dumps(json.dumps(calls))})
results = []
for source in calls:
    try:
        first = eval(source)
        second = eval(source)
        rendered = repr(first)
        ast.literal_eval(rendered)
        results.append({{"ok": first == second and repr(second) == rendered, "output_repr": rendered}})
    except BaseException as error:
        results.append({{"ok": False, "error": type(error).__name__}})
print(json.dumps(results))
'''

    # Execute the complete batch in one temporary isolated Python process.
    with tempfile.TemporaryDirectory(prefix="mbpp-test-oracle-") as directory:
        script = Path(directory) / "oracle.py"
        script.write_text(child, encoding="utf-8")
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
        except subprocess.TimeoutExpired:
            return [{"ok": False, "error": "TimeoutExpired"} for _ in calls]

    # Reject the full batch when reference setup or protocol output fails.
    if completed.returncode != 0:
        return [{"ok": False, "error": "ReferenceError"} for _ in calls]
    try:
        results = json.loads(completed.stdout.strip())
    except json.JSONDecodeError:
        return [{"ok": False, "error": "ProtocolError"} for _ in calls]
    if not isinstance(results, list) or len(results) != len(calls):
        return [{"ok": False, "error": "ProtocolError"} for _ in calls]
    return results


def augment_record(record: dict[str, Any], tests_per_task: int = 20, seed: int = 42, timeout_seconds: float = 3.0) -> dict[str, Any]:
    """Add validated generated assertions and metadata to one normalized record."""
    # Derive a stable per-task seed so records can be generated independently.
    task_id = record.get("task_id")
    task_seed = seed + sum(ord(character) for character in str(task_id))
    calls = extract_literal_calls(str(record.get("test_code", "")))
    candidates = generate_candidate_calls(calls, tests_per_task, task_seed)
    results = run_reference_oracle(str(record.get("reference_code", "")), candidates, timeout_seconds) if candidates else []

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

    # Preserve source fields and attach auditable generation details.
    augmented = dict(record)
    augmented["generated_tests"] = generated_tests
    augmented["generation"] = {
        "seed": task_seed,
        "requested_test_count": tests_per_task,
        "candidate_test_count": len(candidates),
        "accepted_test_count": len(generated_tests),
        "rejection_counts": rejection_counts,
    }
    return augmented


def write_jsonl(records: Any, output_path: Path, tests_per_task: int, seed: int, timeout_seconds: float) -> None:
    """Augment records and write one deterministic JSON object per line."""
    # Create the parent directory before streaming records to the output file.
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as output:
        for record in records:
            augmented = augment_record(dict(record), tests_per_task, seed, timeout_seconds)
            output.write(json.dumps(augmented, sort_keys=True) + "\n")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command line options for dataset loading and generation."""
    # Keep defaults aligned with the official MBPP training experiment.
    parser = argparse.ArgumentParser(description="Generate reference-validated hidden MBPP tests.")
    parser.add_argument("--dataset-name", default="google-research-datasets/mbpp")
    parser.add_argument("--dataset-config", default=None)
    parser.add_argument("--split", default="train")
    parser.add_argument("--tests-per-task", type=int, default=20)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--timeout-seconds", type=float, default=3.0)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
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
    write_jsonl(records, args.output, args.tests_per_task, args.seed, args.timeout_seconds)
    return 0


if __name__ == "__main__":
    # Return the process status through the standard command line entry point.
    raise SystemExit(main())
