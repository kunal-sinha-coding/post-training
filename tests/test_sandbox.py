import pytest

from sandbox import execute_code, expected_interface, extract_code, reward_for_completion, score_completion, split_test_cases, summarize_reward_groups, validate_interface


def test_extract_code_supports_fences():
    assert extract_code("Code: ```python\nprint(1)\n```") == "print(1)"
    assert extract_code("```python\nprint(1)\n```") == "print(1)"


def test_extract_code_removes_thinking_blocks():
    assert extract_code("<think>Reason about it.</think>\nCode: ```python\ndef add(a, b):\n    return a + b\n```") == "def add(a, b):\n    return a + b"


def test_extract_code_rejects_invalid_format():
    try:
        extract_code("def add(a, b):\n    return a + b")
    except ValueError as exc:
        assert str(exc) == "Did not follow proper output formatting"
    else:
        raise AssertionError("Expected a formatting error.")


def test_execute_code_passes_and_rewards():
    result = execute_code("def add(a, b):\n    return a + b", "assert add(1, 2) == 3")
    assert result.passed is True
    assert result.status == "passed"
    assert reward_for_completion("Code: ```python\ndef add(a, b):\n    return a + b\n```", "assert add(1, 2) == 3") == 1.0


def test_dense_reward_counts_partial_assertion_progress():
    """Reward a candidate that passes some but not all assertions."""
    reward, detail = score_completion(
        "Code: ```python\ndef add(a, b):\n    return a + b\n```",
        "assert add(1, 2) == 3\nassert add(1, 2) == 4",
    )
    assert reward == pytest.approx(0.625)
    assert detail["status"] == "partial"
    assert detail["interface_valid"] is True
    assert detail["reward_components"] == {"format": 0.05, "syntax": 0.10, "interface": 0.05, "execution": 0.05, "tests": 0.375}


def test_interface_validation_checks_name_and_arity():
    """Reject nested, renamed, and incorrectly parameterized task functions."""
    tests = "assert add(1, 2) == 3"
    assert expected_interface(tests) == ("add", {2})
    assert validate_interface("def add(a, b):\n    return a + b", tests) is True
    assert validate_interface("def example(a, b):\n    return a + b", tests) is False
    assert validate_interface("def add(a):\n    return a", tests) is False


def test_split_test_cases_preserves_shared_imports():
    """Keep imports in every independently executed assertion."""
    cases = split_test_cases("import math\nassert math.sqrt(4) == 2\nassert math.sqrt(9) == 3")
    assert len(cases) == 2
    assert all(case.startswith("import math") for case in cases)


def test_reward_group_summary_reports_variation():
    """Report flat and mixed reward groups for training diagnostics."""
    diagnostics = summarize_reward_groups(
        [0.2, 0.2, 0.6, 0.2, 1.0, 1.0, 1.0, 1.0],
        [
            {"status": "partial", "passed_tests": 0, "total_tests": 1, "reward_components": {"format": 0.05, "syntax": 0.10, "interface": 0.0, "execution": 0.05, "tests": 0.0}},
            {"status": "partial", "passed_tests": 0, "total_tests": 1, "reward_components": {"format": 0.05, "syntax": 0.10, "interface": 0.0, "execution": 0.05, "tests": 0.0}},
            {"status": "partial", "passed_tests": 1, "total_tests": 1, "reward_components": {"format": 0.05, "syntax": 0.10, "interface": 0.05, "execution": 0.05, "tests": 0.75}},
            {"status": "partial", "passed_tests": 0, "total_tests": 1, "reward_components": {"format": 0.05, "syntax": 0.10, "interface": 0.0, "execution": 0.05, "tests": 0.0}},
            {"status": "passed", "passed_tests": 1, "total_tests": 1, "reward_components": {"format": 0.05, "syntax": 0.10, "interface": 0.05, "execution": 0.05, "tests": 0.75}},
            {"status": "passed", "passed_tests": 1, "total_tests": 1, "reward_components": {"format": 0.05, "syntax": 0.10, "interface": 0.05, "execution": 0.05, "tests": 0.75}},
            {"status": "passed", "passed_tests": 1, "total_tests": 1, "reward_components": {"format": 0.05, "syntax": 0.10, "interface": 0.05, "execution": 0.05, "tests": 0.75}},
            {"status": "passed", "passed_tests": 1, "total_tests": 1, "reward_components": {"format": 0.05, "syntax": 0.10, "interface": 0.05, "execution": 0.05, "tests": 0.75}},
        ],
    )
    assert diagnostics["reward/flat_group_fraction"] == 0.5
    assert diagnostics["reward/mixed_group_fraction"] == 0.5
    assert diagnostics["reward/components/tests/mean"] > 0.0


def test_execute_code_reports_assertion_failure():
    result = execute_code("def add(a, b):\n    return 0", "assert add(1, 2) == 3")
    assert result.passed is False
    assert result.status == "failed"


def test_execute_code_reports_syntax_error():
    result = execute_code("def broken(:\n    pass", "")
    assert result.passed is False
    assert result.status == "syntax_error"


def test_execute_code_reports_timeout():
    result = execute_code("while True:\n    pass", "", timeout_seconds=0.1)
    assert result.passed is False
    assert result.status == "timeout"
