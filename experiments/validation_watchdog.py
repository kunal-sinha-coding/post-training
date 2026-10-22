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
from datetime import datetime, timedelta, timezone
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


def notify_codex_planning(repo: Path, state_path: Path, state: dict, log_path: Path, message: str | None = None) -> None:
    """Notify the configured parent Codex thread that planning is required."""
    # Queue one durable planning request so the parent agent can refill work without restarting stale training.
    thread = os.getenv("CODEX_THREAD") or discover_codex_thread() or state.get("codex_thread")
    if not thread:
        write_log(log_path, "planning handoff not sent because codex_thread is absent")
        return
    message = message or (
        "The research worker queue is exhausted. Inspect the latest clean-validation results, "
        "form new hypotheses, append distinct commands to logs/research_state.json worker_queue, "
        "set planning_required to false, set status to active, and verify the next launch. "
        "Do not use test labels for selection."
    )
    result = subprocess.run(
        ["codex", "queue", "--thread", thread, "--message", message],
        cwd=repo,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode == 0:
        state["planning_notified_at"] = timestamp()
        state["planning_ack_deadline"] = (datetime.now(timezone.utc) + timedelta(seconds=120)).isoformat()
        state["planning_attempts"] = int(state.get("planning_attempts", 0) or 0) + 1
        temporary = state_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
        temporary.replace(state_path)
        write_log(log_path, f"sent planning handoff to Codex thread {thread}")
    else:
        write_log(log_path, f"planning handoff failed return_code={result.returncode} stderr={result.stderr.strip()}")


def discover_codex_thread() -> str | None:
    """Find the active Codex resume thread from the process table."""
    # Prefer the live parent session so a restarted session never receives an old handoff.
    output = subprocess.check_output(["ps", "-eo", "args="], text=True)
    for command in output.splitlines():
        fields = command.strip().split()
        if len(fields) >= 3 and fields[0].endswith("codex") and fields[1] == "resume":
            return fields[2]
    return None


def worker_heartbeat_fresh(repo: Path, active: dict) -> bool:
    """Return whether the active worker has written a recent heartbeat."""
    # Use the trainer heartbeat when available and retain launch-state compatibility for older jobs.
    command = active.get("command") or []
    if "--output-dir" not in command:
        return True
    heartbeat = repo / command[command.index("--output-dir") + 1] / "heartbeat.json"
    if not heartbeat.exists():
        return True
    return time.time() - heartbeat.stat().st_mtime < 120


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


def start_recorder(repo: Path, active: dict, log_path: Path) -> dict | None:
    """Start asynchronous result recording for an exited worker."""
    # Record completion in parallel so bookkeeping never delays the next experiment launch.
    command = active.get("command") or []
    if "--output-dir" not in command:
        write_log(log_path, "completion recorder skipped because output directory is absent")
        return None
    output_dir = command[command.index("--output-dir") + 1]
    experiment_id = Path(output_dir).name
    recorder_command = [
        "python",
        "-u",
        "-m",
        "experiments.record_experiment",
        "--repo",
        str(repo),
        "--experiment-id",
        experiment_id,
        "--command-json",
        json.dumps(command),
        "--output-dir",
        output_dir,
        "--started-at",
        active.get("started_at", "unknown"),
    ]
    output = (repo / "logs/experiment_recorder.out").open("a", encoding="utf-8")
    process = subprocess.Popen(recorder_command, cwd=repo, stdout=output, stderr=subprocess.STDOUT, start_new_session=True)
    output.close()
    write_log(log_path, f"started asynchronous recorder pid {process.pid} for {experiment_id}")
    return {"pid": process.pid, "experiment_id": experiment_id}


def recording_is_complete(repo: Path, experiment_id: str) -> bool:
    """Return whether the experiment has an append-only journal record."""
    # Use the machine journal as the durable completion marker.
    journal = repo / "logs/experiment_records.jsonl"
    if not journal.exists():
        return False
    return f'"experiment_id": "{experiment_id}"' in journal.read_text(encoding="utf-8")


def check_recording_jobs(repo: Path, state_path: Path, state: dict, log_path: Path) -> None:
    """Detect failed asynchronous recorders and notify Codex without blocking."""
    # Remove completed recorder jobs and report failed jobs for later Codex repair.
    remaining = []
    changed = False
    for job in state.get("recording_jobs", []):
        if recording_is_complete(repo, job["experiment_id"]):
            changed = True
            continue
        if process_alive(int(job["pid"])):
            remaining.append(job)
            continue
        changed = True
        message = (
            f"The asynchronous recorder failed for experiment {job['experiment_id']}. "
            "Repair the record from the manifest, worker output, watchdog log, and W&B data. "
            "Write a complete or minimal failure record, update the research log and leaderboard, "
            "then continue the research loop. Do not block new experiments on this repair."
        )
        notify_codex_planning(repo, state_path, state, log_path, message)
        write_log(log_path, f"recorder failed for {job['experiment_id']}; Codex repair requested")
    if changed:
        state["recording_jobs"] = remaining
        temporary = state_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
        temporary.replace(state_path)


def advance_worker_command(state_path: Path, state: dict, log_path: Path) -> bool:
    """Promote the next queued experiment before starting recovery."""
    # Consume one predeclared command so a completed experiment cannot repeat indefinitely.
    queue = state.get("worker_queue") or []
    if not queue:
        state["status"] = "awaiting_codex_planning"
        state["planning_required"] = True
        state["active_experiment"] = {}
        state["next_experiment"] = None
        state["last_action"] = "Watchdog handed planning control to the primary Codex process."
        temporary = state_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
        temporary.replace(state_path)
        write_log(log_path, "queue exhausted; handed control to primary Codex for planning")
        notify_codex_planning(state_path.parent.parent, state_path, state, log_path)
        return False
    next_command = queue.pop(0)
    previous_command = state.get("worker_command")
    state["worker_queue"] = queue
    state["worker_command"] = next_command
    state["next_experiment"] = next_command
    state["planning_required"] = False
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
                check_recording_jobs(args.repo, state_path, state, log_path)
                if state.get("status") == "awaiting_codex_planning" and state.get("planning_required"):
                    deadline = state.get("planning_ack_deadline")
                    if deadline and datetime.now(timezone.utc) >= datetime.fromisoformat(deadline):
                        notify_codex_planning(args.repo, state_path, state, log_path)
                active = state.get("active_experiment") or {}
                pid = int(active.get("pid", 0) or 0)
                heartbeat = state.get("last_heartbeat")
                alive = process_alive(pid)
                stale = heartbeat is None or not worker_heartbeat_fresh(args.repo, active)
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
                        recorder_job = start_recorder(args.repo, active, log_path)
                        if recorder_job:
                            state.setdefault("recording_jobs", []).append(recorder_job)
                        if advance_worker_command(state_path, state, log_path):
                            start_worker(args.repo, state_path, log_path)
            except Exception as error:
                # Record a tick failure and keep the watchdog alive for the next check.
                write_log(log_path, f"tick error {type(error).__name__}: {error}")
            time.sleep(max(1, args.interval_seconds))


if __name__ == "__main__":
    raise SystemExit(main())
