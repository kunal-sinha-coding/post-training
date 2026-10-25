"""Check safe worker recovery and supervision without starting experiment processes.

The tests simulate zombie and reused process identifiers, malformed state recovery, empty queues,
and stale watchdog heartbeats so monitoring failures cannot duplicate or terminate training.
"""
from pathlib import Path
from unittest.mock import patch
import json

from experiments import validation_watchdog as watchdog
from experiments import watchdog_supervisor as supervisor


# Reject zombies even when their process identifier still exists.
def test_zombie_is_not_alive():
    with patch.object(watchdog.os, "kill"), patch.object(watchdog.subprocess, "check_output", return_value="Z"):
        assert not watchdog.process_alive(123)


# Reject a reused identifier whose actual command is unrelated to the declared worker.
def test_worker_identifier_requires_matching_command():
    with patch.object(watchdog, "process_alive", return_value=True), patch.object(Path, "read_bytes", return_value=b"python\0-u\0-m\0unrelated\0"):
        assert not watchdog.worker_matches(123, ["python", "-u", "-m", "experiment"])


# Recover malformed primary state from the last valid backup.
def test_malformed_state_uses_backup(tmp_path):
    state = tmp_path / "research_state.json"
    state.write_text("{")
    state.with_suffix(".bak").write_text(json.dumps({"status": "active"}))
    assert watchdog.load_state(state) == {"status": "active"}


# Hand an exhausted queue to planning instead of repeating the previous worker.
def test_empty_queue_never_relaunches_previous_worker(tmp_path):
    logs = tmp_path / "logs"
    logs.mkdir()
    state_path = logs / "research_state.json"
    state = {"worker_queue": [], "worker_command": ["python", "old_worker"], "active_experiment": {"pid": 123}}
    with patch.object(watchdog, "notify_codex_planning") as notify, patch.object(watchdog, "start_worker") as start:
        assert not watchdog.advance_worker_command(state_path, state, logs / "watchdog.log")
    saved = json.loads(state_path.read_text())
    assert saved["status"] == "awaiting_codex_planning"
    assert saved["active_experiment"] == {}
    assert saved["planning_required"]
    notify.assert_called_once()
    start.assert_not_called()


# Detect a stale watchdog after its startup grace period without inspecting training workers.
def test_watchdog_stale_log_has_startup_grace(tmp_path):
    with patch.object(supervisor.time, "time", return_value=200):
        assert supervisor.watchdog_stale(tmp_path / "missing", 0)
        assert not supervisor.watchdog_stale(tmp_path / "missing", 150)


# Reject shell command text that mentions the watchdog module.
def test_supervisor_requires_exact_watchdog_process():
    with patch.object(supervisor, "process_alive", return_value=True), patch.object(Path, "read_bytes", return_value=b"bash\0-c\0python -u -m experiments.validation_watchdog\0"):
        assert not supervisor.is_watchdog(123)
