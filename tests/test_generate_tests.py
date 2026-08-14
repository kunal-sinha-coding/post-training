"""Verify deterministic mutation, isolated oracle filtering, and JSONL serialization.

The tests use small local reference functions so generator behavior can be checked
without downloading MBPP or depending on network access.
"""

from __future__ import annotations

import json

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


def test_augment_record_adds_requested_reference_validated_tests() -> None:
    """Attach generated assertions and complete generation metadata."""
    # Generate a small number of tests from the local sample.
    augmented = augment_record(sample_record(), tests_per_task=5, seed=11, timeout_seconds=2.0)
    generated = augmented["generated_tests"]
    assert len(generated) == 5
    assert all(str(test).startswith("assert total(") for test in generated)
    assert augmented["generation"]["accepted_test_count"] == 5
    assert augmented["generation"]["requested_test_count"] == 5


def test_write_jsonl_writes_one_augmented_record_per_line(tmp_path) -> None:
    """Serialize augmented records as stable JSON Lines output."""
    # Write two records and load each output line independently.
    output_path = tmp_path / "generated.jsonl"
    write_jsonl([sample_record(), {**sample_record(), "task_id": 2}], output_path, 3, 5, 2.0)
    lines = output_path.read_text(encoding="utf-8").splitlines()
    records = [json.loads(line) for line in lines]
    assert [record["task_id"] for record in records] == [1, 2]
    assert all(len(record["generated_tests"]) == 3 for record in records)
