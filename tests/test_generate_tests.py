"""Verify deterministic mutation, isolated oracle filtering, and JSONL serialization.

The tests use small local reference functions so generator behavior can be checked
without downloading MBPP or depending on network access.
"""

from __future__ import annotations

import json

import ast
import pytest

from synthetic_data.constraints import infer_constraints, validate_call
from synthetic_data.generate_tests import augment_record, extract_literal_calls, generate_candidate_calls, run_reference_oracle, write_jsonl


def sample_record() -> dict[str, object]:
    """Return one normalized record with a deterministic list function."""
    # Use the same normalized fields emitted by the repository dataset loader.
    return {
        "task_id": 1,
        "prompt": "Return the sum of a list.",
        "test_code": "assert total([1, 2]) == 3\nassert total([4]) == 4",
        "reference_code": "def total(values):\n    return sum(values)",
    }


def test_extract_literal_calls_ignores_nonliteral_and_noncall_assertions() -> None:
    """Keep only direct calls whose arguments can be safely reconstructed."""
    # Include valid, variable based, and predicate assertions in one input.
    tests = "assert total([1, 2]) == 3\nassert total(values) == 3\nassert ready"
    calls = extract_literal_calls(tests)
    assert [ast_source.func.id for ast_source in calls] == ["total"]


def test_extract_literal_calls_accepts_named_constructors() -> None:
    """Accept constructor values when every constructor argument is literal syntax."""
    # Parse Pair objects without allowing arbitrary variable expressions.
    calls = extract_literal_calls("assert chain([Pair(1, 2), Pair(3, 4)], 2) == 2")
    assert len(calls) == 1


def test_constraints_reject_broken_lengths_domains_and_shapes() -> None:
    """Reject candidates that violate relationships demonstrated by official calls."""
    # Infer linked size, positivity, nonempty, and square matrix constraints.
    calls = extract_literal_calls("assert solve([[1, 2], [3, 4]], 2) == 1\nassert solve([[5]], 1) == 1")
    constraints = infer_constraints(calls, "Solve a square matrix of positive values.")
    broken = extract_literal_calls("assert solve([[1, 2], [3, 4]], 0) == 1")[0]
    assert "positive:1" in validate_call(constraints, broken)
    assert "length_equals:0:1" in validate_call(constraints, broken)


def test_generate_candidate_calls_is_deterministic_and_unique() -> None:
    """Produce the same unique mutations for a fixed seed."""
    # Generate twice from the same parsed assertions.
    calls = extract_literal_calls(str(sample_record()["test_code"]))
    first = generate_candidate_calls(calls, limit=20, seed=7)
    second = generate_candidate_calls(calls, limit=20, seed=7)
    assert first == second
    assert len(first) == len(set(first))
    assert "total([1, 2])" not in first


def test_run_reference_oracle_accepts_values_and_rejects_errors() -> None:
    """Evaluate all candidate calls in one isolated oracle batch."""
    # Mix a valid call with one that raises inside the reference function.
    reference = "def reciprocal(value):\n    return 1 / value"
    results = run_reference_oracle(reference, ["reciprocal(2)", "reciprocal(0)"], timeout_seconds=2.0)
    assert results[0] == {"ok": True, "output_repr": "0.5"}
    assert results[1]["ok"] is False
    assert results[1]["error"] == "ZeroDivisionError"


def test_run_reference_oracle_rejects_none_without_poisoning_later_calls() -> None:
    """Reject accidental None while continuing with independently isolated candidates."""
    # Place a None result before a valid result to verify per-candidate isolation.
    reference = "def maybe(value):\n    return None if value == 0 else value"
    results = run_reference_oracle(reference, ["maybe(0)", "maybe(2)"], timeout_seconds=2.0)
    assert results[0]["error"] == "NoneResult"
    assert results[1] == {"ok": True, "output_repr": "2"}


def test_augment_record_adds_requested_reference_validated_tests() -> None:
    """Attach generated assertions and complete generation metadata."""
    # Generate a small number of tests from the local sample.
    augmented = augment_record(sample_record(), tests_per_task=5, seed=11, timeout_seconds=2.0)
    generated = augmented["generated_tests"]
    assert len(generated) == 5
    assert all(str(test).startswith("assert total(") for test in generated)
    assert augmented["generation"]["accepted_test_count"] == 5
    assert augmented["generation"]["requested_test_count"] == 5


def test_augment_record_fails_when_exact_coverage_is_impossible() -> None:
    """Fail closed instead of writing an artifact with fewer tests than requested."""
    # Use an immutable empty tuple whose call contains no mutable literal leaves.
    record = {"task_id": 3, "text": "Return zero.", "test_code": "assert fixed(()) == 0", "reference_code": "def fixed(value):\n    return 0"}
    with pytest.raises(ValueError, match="generated 0 of 1"):
        augment_record(record, tests_per_task=1, seed=1, timeout_seconds=2.0)


def test_write_jsonl_writes_one_augmented_record_per_line(tmp_path) -> None:
    """Serialize augmented records as stable JSON Lines output."""
    # Write two records and load each output line independently.
    output_path = tmp_path / "generated.jsonl"
    write_jsonl([sample_record(), {**sample_record(), "task_id": 2}], output_path, 3, 5, 2.0)
    lines = output_path.read_text(encoding="utf-8").splitlines()
    records = [json.loads(line) for line in lines]
    assert [record["task_id"] for record in records] == [1, 2]
    assert all(len(record["generated_tests"]) == 3 for record in records)
