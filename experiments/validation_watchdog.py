"""Monitor the clean When2Call research worker and recover stalled validation work.

The flow reads durable state, checks the worker process and heartbeat, records each five minute
check, and starts only the command declared in the state file when recovery is required.
"""
from __future__ import annotations

import argparse
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
    # Signal zero checks process existence without changing process state.
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except (ProcessLookupError, PermissionError):
        return False
    return True


def load_state(path: Path) -> dict:
    """Load the atomic research state document."""
    # Parse the complete state on every check so external workers can update it.
    return json.loads(path.read_text(encoding="utf-8"))


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
    temporary = state_path.with_suffix(".tmp")
    temporary.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    temporary.replace(state_path)
    write_log(log_path, f"started validation worker pid {process.pid}")
    return process.pid


def main() -> int:
    """Check the clean worker forever at the configured interval."""
    # Parse paths and enforce a minimum interval that is compatible with the five minute policy.
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--interval-seconds", type=int, default=300)
    args = parser.parse_args()
    state_path = args.repo / "logs/research_state.json"
    log_path = args.repo / "logs/validation_watchdog.log"
    while True:
        # Inspect the worker and heartbeat before deciding whether recovery is needed.
        state = load_state(state_path)
        active = state.get("active_experiment") or {}
        pid = int(active.get("pid", 0) or 0)
        heartbeat = state.get("last_heartbeat")
        alive = process_alive(pid)
        stale = heartbeat is None
        write_log(log_path, f"check pid={pid} alive={alive} heartbeat={heartbeat} stale={stale}")
        if state.get("status") == "active" and (not alive or stale):
            start_worker(args.repo, state_path, log_path)
        time.sleep(max(300, args.interval_seconds))


if __name__ == "__main__":
    raise SystemExit(main())
