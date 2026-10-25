"""Check complete experiment recording without launching Git or experiment workers.

The tests write temporary result artifacts, verify source-specific schema compatibility and explicit
failure states, and simulate bounded Git push retries without network access or persistent changes.
"""
import argparse
import json
from unittest.mock import patch
import subprocess

from experiments import record_experiment as recorder


# Build a temporary recorder invocation with synchronization disabled.
def arguments(output, **overrides):
    values = dict(output_dir=str(output), experiment_id="example", command_json='["python", "experiment"]', started_at="2026-10-25", exit_code="0", status=None, development_accuracy=None, development_macro_f1=None, wandb_run_id=None, wandb_run_url=None, no_git=True)
    values.update(overrides)
    return argparse.Namespace(**values)


# Preserve source validation metrics without treating different splits as a unified leaderboard.
def test_source_mix_records_complete_metadata(tmp_path):
    output = tmp_path / "outputs/example"
    output.mkdir(parents=True)
    metrics = {"pref_validation_metrics": {"accuracy": 0.9, "macro_f1": 0.8}, "train_metrics": {"accuracy": 1.0}, "seed": 42}
    (output / "metrics.json").write_text(json.dumps(metrics))
    result = recorder.record(tmp_path, arguments(output))
    assert result["status"] == "completed"
    assert result["metadata"] == metrics
    assert result["development_metrics"] == {}
    assert result["source_validation_metrics"]["pref_validation_metrics"]["macro_f1"] == 0.8
    assert '"seed": 42' in (tmp_path / "logs/results.txt").read_text()
    assert "not ranked against other splits" in (tmp_path / "logs/leaderboard.md").read_text()


# Respect a failed worker status even when partial validation metrics exist.
def test_explicit_failure_preserves_reason(tmp_path):
    output = tmp_path / "output"
    output.mkdir()
    (output / "metrics.json").write_text(json.dumps({"status": "failed", "error": "out of memory", "development_metrics": {"accuracy": 0.5}}))
    result = recorder.record(tmp_path, arguments(output))
    assert result["status"] == "failed"
    assert result["test_status"] == "failed"
    assert result["failure_reason"] == "out of memory"


# Distinguish a skipped official measurement from an incomplete experiment.
def test_explicit_test_skip(tmp_path):
    output = tmp_path / "output"
    output.mkdir()
    (output / "metrics.json").write_text(json.dumps({"status": "test skipped", "reason": "validation collapse"}))
    result = recorder.record(tmp_path, arguments(output))
    assert result["status"] == "test skipped"
    assert result["test_status"] == "test skipped"
    assert result["failure_reason"] == "validation collapse"


# Recognize aggregate-only official measurements and retain the complete raw setup.
def test_official_measurement_is_completed(tmp_path):
    output = tmp_path / "output"
    output.mkdir()
    metrics = {"official_test_metrics": {"accuracy": 0.7, "macro_f1": 0.6}, "mode": "test", "weights": [0.5, 0.5]}
    (output / "metrics.json").write_text(json.dumps(metrics))
    result = recorder.record(tmp_path, arguments(output))
    assert result["status"] == "completed"
    assert result["test_status"] == "measured"
    assert result["metadata"]["weights"] == [0.5, 0.5]


# Stop a repeated DNS failure after three pushes and preserve a local error record.
def test_dns_retry_is_bounded(tmp_path):
    (tmp_path / ".git").mkdir()
    calls = []

    # Simulate successful local commits and unresolved GitHub DNS during pushes.
    def fake_git(repo, command, check=True):
        calls.append(command)
        if command == ["rev-parse", "--git-dir"]:
            return subprocess.CompletedProcess(command, 0, ".git\n", "")
        if command == ["push"]:
            return subprocess.CompletedProcess(command, 1, "", "Could not resolve host: github.com")
        return subprocess.CompletedProcess(command, 0, "", "")

    with patch.object(recorder, "git_command", side_effect=fake_git), patch.object(recorder.time, "sleep") as sleep:
        result = recorder.commit_records(tmp_path, "example")
    assert calls.count(["push"]) == 3
    assert sleep.call_count == 2
    assert result["status"] == "failed"
    assert (tmp_path / "logs/experiment_recorder_errors.jsonl").exists()


# Recognize a flat aggregate metric block only when the worker declares a black-box test measurement.
def test_flat_blackbox_measurement_stays_out_of_development(tmp_path):
    output = tmp_path / "output"
    output.mkdir()
    metrics = {"test_measurement_only": True, "black_box": True, "status": "completed", "metrics": {"accuracy": 0.7, "macro_f1": 0.6}}
    (output / "metrics.json").write_text(json.dumps(metrics))
    result = recorder.record(tmp_path, arguments(output))
    assert result["official_test_metrics"] == metrics["metrics"]
    assert result["official_test_loaded"] is True
    assert result["test_status"] == "measured"
    assert result["development_metrics"] == {}


# Avoid interpreting an unmarked metric block as an official test result.
def test_unmarked_flat_metrics_are_not_test_results(tmp_path):
    output = tmp_path / "output"
    output.mkdir()
    (output / "metrics.json").write_text(json.dumps({"metrics": {"accuracy": 0.7, "macro_f1": 0.6}}))
    result = recorder.record(tmp_path, arguments(output))
    assert result["official_test_metrics"] == {}
    assert result["development_metrics"] == {}
    assert result["test_status"] == "not measured"
