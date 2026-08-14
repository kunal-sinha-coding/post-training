"""Verify strict synthetic artifact validation and command-line status behavior.

The tests construct small local records that exercise successful validation,
schema and count rejection, signature and constraint checks, None protection,
duplicate detection, oracle failures, and JSON summary output without MBPP access.
"""

from __future__ import annotations

import json

from synthetic_data.validate_tests import main, validate_artifact, validate_record


def valid_record() -> dict[str, object]:
    """Return one valid constrained record with two synthetic tests."""
    # Match list length to the scalar size in originals and generated tests.
    return {
        "task_id": 1,
        "test_code": "assert total([1, 2], 2) == 3",
        "reference_code": "def total(values, n):\n    return sum(values[:n])",
        "generated_tests": ["assert total([3], 1) == 3", "assert total([4, 5, 6], 3) == 15"],
        "constraints": [
            {"type": "length_equals", "container": 0, "scalar": 1},
            {"type": "none_output_allowed", "allowed": False},
        ],
        "generation": {"requested_test_count": 2},
    }


def test_validate_record_accepts_complete_constrained_tests() -> None:
    """Accept exact, unique, constraint-preserving tests that pass the oracle."""
    # Validate a fully correct local artifact record.
    assert validate_record(valid_record(), tests_per_task=2, timeout_seconds=2.0) == []


def test_validate_record_reports_shape_count_signature_and_duplicates() -> None:
    """Report independent structural failures without stopping at the first one."""
    # Introduce a wrong function, duplicate assertion, and insufficient count.
    record = valid_record()
    record["generated_tests"] = ["assert other([3], 1) == 3", "assert other([3], 1) == 3"]
    errors = validate_record(record, tests_per_task=3, timeout_seconds=2.0)
    codes = [error["code"] for error in errors]
    assert "test_count" in codes
    assert "function" in codes
    assert "duplicate" in codes


def test_validate_record_rejects_constraint_none_and_oracle_failures() -> None:
    """Reject invalid domains, accidental None expectations, and wrong outputs."""
    # Break the declared relationship and expected result in separate tests.
    record = valid_record()
    record["generated_tests"] = ["assert total([3], 2) == None", "assert total([4, 5], 2) == 100"]
    errors = validate_record(record, tests_per_task=2, timeout_seconds=2.0)
    codes = [error["code"] for error in errors]
    assert "constraint" in codes
    assert "accidental_none" in codes
    assert codes.count("oracle") == 2


def test_validate_record_rejects_argument_type_and_unsupported_constraint() -> None:
    """Reject changed argument types and unknown declarative constraints."""
    # Change a list to a tuple and declare an unsupported rule.
    record = valid_record()
    record["generated_tests"] = ["assert total((3,), 1) == 3", "assert total([4], 1) == 4"]
    record["constraints"] = [{"type": "mystery", "arg": 0}, {"type": "none_output_allowed", "allowed": False}]
    errors = validate_record(record, tests_per_task=2, timeout_seconds=2.0)
    codes = [error["code"] for error in errors]
    assert "argument_types" in codes
    assert codes.count("constraint_definition") == 2


def test_validate_artifact_and_main_emit_strict_json_summary(tmp_path, capsys) -> None:
    """Return nonzero and write JSON when any artifact record fails validation."""
    # Write one valid record and one record missing required fields.
    artifact = tmp_path / "tests.jsonl"
    artifact.write_text(json.dumps(valid_record()) + "\n" + json.dumps({"task_id": 2}) + "\n", encoding="utf-8")
    summary_path = tmp_path / "summary.json"
    assert main([str(artifact), "--tests-per-task", "2", "--summary", str(summary_path)]) == 1
    printed = json.loads(capsys.readouterr().out)
    persisted = json.loads(summary_path.read_text(encoding="utf-8"))
    assert printed == persisted
    assert persisted["valid"] is False
    assert persisted["record_count"] == 2
    assert persisted["error_counts"]["record_shape"] == 1


def test_validate_artifact_accepts_valid_jsonl(tmp_path) -> None:
    """Return a successful summary when every record passes all checks."""
    # Persist and validate one complete record.
    artifact = tmp_path / "tests.jsonl"
    artifact.write_text(json.dumps(valid_record()) + "\n", encoding="utf-8")
    summary = validate_artifact(artifact, tests_per_task=2, timeout_seconds=2.0)
    assert summary["valid"] is True
    assert summary["error_count"] == 0


def test_validate_record_allows_setup_lines_and_isolates_oracle_tests() -> None:
    """Ignore setup statements and prevent reference state from leaking across tests."""
    # Use a global counter that succeeds only when each assertion has a fresh process.
    record = {
        "task_id": 3,
        "test_code": "import math\nassert counter(1) == 1",
        "reference_code": "seen = 0\ndef counter(value):\n    global seen\n    seen += value\n    return seen",
        "generated_tests": ["assert counter(1) == 1", "assert counter(1) == 1"],
        "constraints": [{"type": "none_output_allowed", "allowed": False}],
        "generation": {"requested_test_count": 2},
    }
    errors = validate_record(record, tests_per_task=2, timeout_seconds=2.0)
    assert [error["code"] for error in errors] == ["duplicate"]


def test_validate_record_checks_constructor_shapes_and_zero_based_indices() -> None:
    """Inspect constructor-containing containers and enforce zero-based indices."""
    # Preserve Pair calls structurally while checking list length and index bounds.
    record = {
        "task_id": 4,
        "test_code": "assert select([Pair(1, 2)], 0) == 1",
        "reference_code": "class Pair:\n    def __init__(self, a, b):\n        self.a = a\n        self.b = b\ndef select(values, index):\n    return values[index].a",
        "generated_tests": ["assert select([Pair(3, 4)], 0) == 3"],
        "constraints": [
            {"type": "arg_type", "arg": 0, "type_name": "list"},
            {"type": "zero_based_index", "container": 0, "index": 1},
            {"type": "none_output_allowed", "allowed": False},
        ],
        "generation": {"requested_test_count": 1},
    }
    assert validate_record(record, tests_per_task=1, timeout_seconds=2.0) == []
