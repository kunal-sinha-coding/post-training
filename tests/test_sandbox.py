from sandbox import execute_code, extract_code, reward_for_completion


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
