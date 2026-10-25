"""Supervise the 30-second validation watchdog and restart it after failures.

The flow holds one supervisor lock, adopts only a live matching watchdog, checks its log heartbeat,
and restarts only the watchdog after exit or a stale heartbeat without terminating experiment workers.
"""
from __future__ import annotations

import fcntl
import os
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from experiments.validation_watchdog import process_alive


def timestamp() -> str:
    """Return the current UTC timestamp."""
    # Use timezone aware records for reliable recovery audits.
    return datetime.now(timezone.utc).isoformat()


def write_log(path: Path, message: str) -> None:
    """Append one supervisor event."""
    # Preserve every watchdog launch and exit.
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(f"[{timestamp()}] {message}\n")


def is_watchdog(pid: int) -> bool:
    """Check the exact module identity of a live watchdog process."""
    # Read null separated proc arguments so shell command text cannot match the watchdog.
    if not process_alive(pid):
        return False
    try:
        arguments = Path(f"/proc/{pid}/cmdline").read_bytes().decode().rstrip("\0").split("\0")
    except (OSError, UnicodeError):
        return False
    return len(arguments) >= 4 and Path(arguments[0]).name.startswith("python") and arguments[1:4] == ["-u", "-m", "experiments.validation_watchdog"]


def existing_watchdog() -> int | None:
    """Return one live process with the exact watchdog module identity."""
    # Ignore zombies and unrelated commands before adopting an existing watchdog.
    for entry in Path("/proc").iterdir():
        if entry.name.isdigit() and is_watchdog(int(entry.name)):
            return int(entry.name)
    return None


def watchdog_stale(path: Path, started_at: float, timeout: float = 120) -> bool:
    """Check whether the watchdog has stopped writing its monitoring log."""
    # Allow a full startup interval before requiring the monitoring log heartbeat.
    try:
        heartbeat = max(started_at, path.stat().st_mtime)
    except FileNotFoundError:
        heartbeat = started_at
    return time.time() - heartbeat > timeout


def supervise(repo: Path) -> None:
    """Adopt or start the watchdog and recover its exit or stale heartbeat."""
    # Poll the watchdog itself while leaving every experiment worker untouched.
    log_path = repo / "logs/validation_supervisor.log"
    heartbeat_path = repo / "logs/validation_watchdog.log"
    command = [sys.executable, "-u", "-m", "experiments.validation_watchdog", "--interval-seconds", "30"]
    while True:
        process = None
        pid = existing_watchdog()
        if pid is not None:
            write_log(log_path, f"adopting watchdog pid={pid}")
        else:
            write_log(log_path, f"starting watchdog command={command}")
            with (repo / "logs/validation_watchdog.out").open("a", encoding="utf-8") as output:
                process = subprocess.Popen(command, cwd=repo, stdout=output, stderr=subprocess.STDOUT, start_new_session=True)
            pid = process.pid
        started_at = time.time()

        # Restart a stale watchdog only after confirming its exact identity again.
        while is_watchdog(pid):
            if watchdog_stale(heartbeat_path, started_at):
                write_log(log_path, f"watchdog heartbeat stale pid={pid}; restarting watchdog only")
                if is_watchdog(pid):
                    os.kill(pid, signal.SIGTERM)
                break
            time.sleep(5)
        if process is not None:
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                if is_watchdog(pid):
                    os.kill(pid, signal.SIGKILL)
                process.wait()
        write_log(log_path, f"watchdog exited pid={pid}")
        time.sleep(2)


def main() -> int:
    """Hold one supervisor lock and maintain the watchdog indefinitely."""
    # Prevent duplicate supervisors from adopting or restarting the same watchdog.
    repo = Path(__file__).resolve().parents[1]
    lock_path = repo / "logs/validation_supervisor.lock"
    with lock_path.open("w", encoding="utf-8") as stream:
        try:
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return 0
        supervise(repo)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
