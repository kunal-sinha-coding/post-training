import os

from evaluate import aggregate_results, append_evaluation_result, cleanup_run_logs, start_run_log


def test_aggregate_results_reports_pass_rate_and_statuses():
    metrics = aggregate_results([
        {"passed": True, "reward": 1.0, "status": "passed"},
        {"passed": False, "reward": 0.0, "status": "failed"},
    ])
    assert metrics["examples"] == 2
    assert metrics["pass_at_1"] == 0.5
    assert metrics["status_counts"] == {"passed": 1, "failed": 1}


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
