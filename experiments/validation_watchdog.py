"""Monitor the clean When2Call research worker and recover stalled validation work.

The flow reads durable state, checks the worker process and heartbeat every 30 seconds, records
each check, and starts only the command declared in the state file when recovery is required.
"""
from __future__ import annotations

import argparse
import fcntl
import json
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path


def timestamp() -> str:
    """Return the current UTC time in a sortable format."""
    # Use timezone aware timestamps so recovery records remain comparable across hosts.
    return datetime.now(timezone.utc).isoformat()


def write_log(path: Path, message: str) -> None:
    """Append one durable watchdog event."""
    # Preserve every check and recovery action for later audit.
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(f"[{timestamp()}] {message}\n")


def process_alive(pid: int) -> bool:
    """Return whether a process identifier still exists."""
    # Check both process existence and process state so zombies do not block recovery.
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except (ProcessLookupError, PermissionError):
        return False
    try:
        state = subprocess.check_output(["ps", "-o", "stat=", "-p", str(pid)], text=True).strip()
    except subprocess.CalledProcessError:
        return False
    return bool(state) and not state.startswith("Z")


def command_matches(expected: list[str], actual: str) -> bool:
    """Return whether a process command contains the declared worker command."""
    # Match every declared argument so stale workers from an earlier experiment cannot be adopted.
    return bool(expected) and all(argument in actual for argument in expected)


def running_validation_workers(exclude_pid: int, expected_command: list[str]) -> list[int]:
    """Return matching validation worker process identifiers already running in the repository."""
    # Inspect command lines so recovery adopts only the declared worker before creating a duplicate.
    output = subprocess.check_output(["ps", "-eo", "pid=,args="], text=True)
    workers = []
    for line in output.splitlines():
        fields = line.strip().split(maxsplit=1)
        if len(fields) != 2:
            continue
        pid, command = int(fields[0]), fields[1]
        try:
            state = subprocess.check_output(["ps", "-o", "stat=", "-p", str(pid)], text=True).strip()
        except subprocess.CalledProcessError:
            continue
        if pid != exclude_pid and not state.startswith("Z") and command_matches(expected_command, command):
            workers.append(pid)
    return workers


def load_state(path: Path) -> dict:
    """Load the atomic research state document."""
    # Recover from a transient or malformed primary file by using the last valid backup.
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        backup = path.with_suffix(".bak")
        return json.loads(backup.read_text(encoding="utf-8"))


def audit_research_log(path: Path, previous_size: int | None) -> tuple[int, str | None]:
    """Check that the persistent research log still exists and does not shrink."""
    # Detect deletion or truncation before the watchdog performs recovery.
    try:
        current_size = path.stat().st_size
    except FileNotFoundError:
        return 0, "research_log.md is missing"
    if previous_size is not None and current_size < previous_size:
        return current_size, f"research_log.md shrank from {previous_size} to {current_size} bytes"
    return current_size, None


def start_worker(repo: Path, state_path: Path, log_path: Path) -> int:
    """Start the recovery command declared by the research state."""
    # Refuse recovery when no safe validation command has been registered.
    state = load_state(state_path)
    command = state.get("worker_command")
    if not command:
        write_log(log_path, "recovery skipped because worker_command is absent")
        return 0
    output = (repo / "logs/validation_worker.out").open("a", encoding="utf-8")
    process = subprocess.Popen(command, cwd=repo, stdout=output, stderr=subprocess.STDOUT, start_new_session=True)
    output.close()
    state["active_experiment"] = {"pid": process.pid, "command": command, "started_at": timestamp()}
    state["last_heartbeat"] = timestamp()
    state["last_action"] = f"Watchdog started validation worker pid {process.pid}."
    backup = state_path.with_suffix(".bak")
    if state_path.exists():
        state_path.replace(backup)
    temporary = state_path.with_suffix(".tmp")
    temporary.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    temporary.replace(state_path)
    write_log(log_path, f"started validation worker pid {process.pid}")
    return process.pid


def advance_worker_command(state_path: Path, state: dict, log_path: Path) -> bool:
    """Promote the next queued experiment before starting recovery."""
    # Consume one predeclared command so a completed experiment cannot repeat indefinitely.
    queue = state.get("worker_queue") or []
    if not queue:
        write_log(log_path, "queue exhausted; recovery skipped to prevent command repetition")
        return False
    next_command = queue.pop(0)
    previous_command = state.get("worker_command")
    state["worker_queue"] = queue
    state["worker_command"] = next_command
    state["next_experiment"] = next_command
    state["last_action"] = "Watchdog advanced the experiment queue after worker exit."
    temporary = state_path.with_suffix(".tmp")
    temporary.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    temporary.replace(state_path)
    write_log(log_path, f"advanced worker command from {previous_command} to {next_command}")
    return True


def main() -> int:
    """Check the clean worker forever at the configured interval."""
    # Parse paths and enforce a short minimum interval for rapid failure recovery.
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--interval-seconds", type=int, default=30)
    args = parser.parse_args()
    state_path = args.repo / "logs/research_state.json"
    log_path = args.repo / "logs/validation_watchdog.log"
    lock_path = args.repo / "logs/validation_watchdog.lock"
    with lock_path.open("w", encoding="utf-8") as lock_stream:
        fcntl.flock(lock_stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        while True:
            try:
                # Inspect the worker and heartbeat before deciding whether recovery is needed.
                state = load_state(state_path)
                # Preserve the largest observed research log size across watchdog restarts.
                log_size, log_error = audit_research_log(args.repo / "logs/research_log.md", state.get("research_log_size"))
                if log_error:
                    write_log(log_path, f"integrity failure: {log_error}")
                state["research_log_size"] = max(log_size, int(state.get("research_log_size", 0) or 0))
                active = state.get("active_experiment") or {}
                pid = int(active.get("pid", 0) or 0)
                heartbeat = state.get("last_heartbeat")
                alive = process_alive(pid)
                stale = heartbeat is None
                write_log(log_path, f"check pid={pid} alive={alive} heartbeat={heartbeat} stale={stale}")
                if state.get("status") == "active" and (not active or not alive or stale):
                    # Adopt a worker launched before the state update instead of competing for the GPU.
                    existing = running_validation_workers(os.getpid(), state.get("worker_command") or [])
                    if existing:
                        active_pid = existing[0]
                        state["active_experiment"] = {"pid": active_pid, "command": state.get("worker_command"), "started_at": timestamp()}
                        state["last_heartbeat"] = timestamp()
                        state["last_action"] = f"Watchdog adopted existing validation worker pid {active_pid}."
                        temporary = state_path.with_suffix(".tmp")
                        temporary.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
                        temporary.replace(state_path)
                        write_log(log_path, f"adopted existing validation worker pid {active_pid}")
                    else:
                        if advance_worker_command(state_path, state, log_path):
                            start_worker(args.repo, state_path, log_path)
            except Exception as error:
                # Record a tick failure and keep the watchdog alive for the next check.
                write_log(log_path, f"tick error {type(error).__name__}: {error}")
            time.sleep(max(1, args.interval_seconds))


if __name__ == "__main__":
    raise SystemExit(main())
