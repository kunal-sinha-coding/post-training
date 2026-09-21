import os

import pytest
import torch

from evaluate import aggregate_results, append_evaluation_result, cleanup_run_logs, code_fence_stopping_criteria, evaluate_texts, mask_completion_tokens_after_stop, start_run_log


def test_stop_criterion_marks_each_finished_completion():
    """Return a per-row stop decision so finished samples are padded independently."""
    class Tokenizer:
        """Map the one test stop string to a fixed token sequence."""

        def __call__(self, text, add_special_tokens=False):
            """Return the stop token IDs expected by the criterion."""
            del text, add_special_tokens
            return {"input_ids": [7, 8]}

    criterion = code_fence_stopping_criteria(Tokenizer(), prompt_width=2, stop_strings=("stop",))[0]
    finished = criterion(torch.tensor([[1, 2, 7, 8], [1, 2, 3, 4]]), None)

    assert torch.equal(finished, torch.tensor([True, False]))


def test_reward_stop_mask_removes_each_unscored_suffix():
    """Mask stop tokens and tails while retaining code tokens for every completion."""
    completion_ids = torch.tensor([[3, 7, 8, 9, 0], [4, 5, 6, 0, 0]])
    completion_mask = torch.tensor([[1, 1, 1, 1, 0], [1, 1, 1, 0, 0]])

    masked = mask_completion_tokens_after_stop(completion_ids, completion_mask, [[7, 8]])

    assert torch.equal(masked, torch.tensor([[1, 0, 0, 0, 0], [1, 1, 1, 0, 0]]))


def test_reward_stop_mask_uses_contextual_token_offsets():
    """Verify that context-dependent tokenization follows reward text truncation."""
    # Use a tiny tokenizer fixture whose offsets reproduce the contextual boundary behavior.
    class ContextTokenizer:
        """Represent the decoded completion with one offset per character."""

        def decode(self, ids, skip_special_tokens=False):
            """Return the fixed completion represented by the fixture IDs."""
            del ids, skip_special_tokens
            return "return x\nprint(x)"

        def __call__(self, text, add_special_tokens=False, return_offsets_mapping=False):
            """Return character offsets for the fixture text."""
            del add_special_tokens
            if return_offsets_mapping:
                return {"offset_mapping": [(index, index + 1) for index in range(len(text))]}
            return {"input_ids": [1] * len(text)}

    completion_ids = torch.ones((1, len("return x\nprint(x)")), dtype=torch.long)
    completion_mask = torch.ones_like(completion_ids)
    masked = mask_completion_tokens_after_stop(
        completion_ids,
        completion_mask,
        [[1]],
        tokenizer=ContextTokenizer(),
    )

    assert int(masked.sum()) == len("return x")


def test_aggregate_results_reports_pass_rate_and_statuses():
    metrics = aggregate_results([
        {"passed": True, "reward": 0.9, "status": "passed", "passed_tests": 2, "total_tests": 2},
        {"passed": False, "reward": 0.3, "status": "failed", "passed_tests": 0, "total_tests": 2},
    ])
    assert metrics["examples"] == 2
    assert metrics["pass_at_1"] == 0.5
    assert metrics["average_reward"] == pytest.approx(0.6)
    assert metrics["tests_pass_fraction"] == 0.5
    assert metrics["status_counts"] == {"passed": 1, "failed": 1}


def test_evaluate_texts_uses_dense_training_reward_and_separate_pass_rate(tmp_path):
    """Use partial test progress for reward without counting it as a pass."""
    # Evaluate one valid function that passes one of two assertions.
    metrics, details = evaluate_texts(
        ["```python\ndef increment(value):\n    return value + 1\n```"],
        [{"task_id": 1, "prompt": "Increment a value.", "test_code": "assert increment(1) == 2\nassert increment(2) == 4"}],
        log_path=tmp_path / "logs.txt",
    )

    # Keep binary correctness separate from the shared dense reward.
    assert metrics["pass_at_1"] == 0.0
    assert metrics["average_reward"] == pytest.approx(0.5)
    assert details[0]["reward_components"]["tests"] == pytest.approx(0.5)


def test_start_run_log_keeps_only_newest_configured_logs(tmp_path, monkeypatch):
    monkeypatch.setattr("evaluate.MAX_RUN_LOGS", 2)
    log_directory = tmp_path / "logs"
    log_directory.mkdir()
    for index in range(3):
        log_path = log_directory / f"run-{index}.log"
        log_path.write_text(f"run {index}", encoding="utf-8")
        os.utime(log_path, (index, index))

    start_run_log(log_directory / "run-new.log")

    remaining_logs = sorted(path.name for path in log_directory.glob("*.log"))
    assert remaining_logs == ["run-2.log", "run-new.log"]


def test_cleanup_run_logs_keeps_all_logs_when_disabled(tmp_path, monkeypatch):
    monkeypatch.setattr("evaluate.MAX_RUN_LOGS", -1)
    log_directory = tmp_path / "logs"
    log_directory.mkdir()
    for index in range(3):
        (log_directory / f"run-{index}.txt").write_text(f"run {index}", encoding="utf-8")

    cleanup_run_logs(log_directory / "run-new.txt")

    assert len(list(log_directory.glob("*.txt"))) == 3


def test_cleanup_run_logs_keeps_newest_error_analysis_reports(tmp_path, monkeypatch):
    """Keep recent analysis reports while preserving the results log."""
    monkeypatch.setattr("evaluate.MAX_RUN_LOGS", 2)
    analysis_path = tmp_path / "error_analysis.txt"
    reports = []
    for index in range(3):
        reports.append(f"{'-' * 72}\nERROR ANALYSIS\nTimestamp: run-{index}\nReport {index}\n")
    analysis_path.write_text("\n".join(reports), encoding="utf-8")
    results_path = tmp_path / "results.txt"
    results_path.write_text("all historical results", encoding="utf-8")

    cleanup_run_logs(tmp_path / "logs.txt")

    contents = analysis_path.read_text(encoding="utf-8")
    assert "Report 0" not in contents
    assert "Report 1" in contents
    assert "Report 2" in contents
    assert results_path.read_text(encoding="utf-8") == "all historical results"


def test_results_log_records_header_metadata_and_metrics(tmp_path):
    """Record a reproducible evaluation result beside the detailed run log."""
    results_path = tmp_path / "results.txt"
    start_run_log(tmp_path / "logs.txt", results_path)
    append_evaluation_result(
        results_path,
        "baseline",
        {"examples": 2, "pass_at_1": 0.5},
        {
            "results_log_path": results_path,
            "training_context": "baseline",
            "_evaluation_epoch": "baseline",
            "_config_path": "configs/test.yaml",
            "_config_yaml": "max_steps: 1\n",
        },
    )
    contents = results_path.read_text(encoding="utf-8")
    assert "RUN STARTING" in contents
    assert "EVALUATION RESULTS" in contents
    assert "Training context: baseline" in contents
    assert "pass_at_1" in contents
    assert "max_steps: 1" in contents
