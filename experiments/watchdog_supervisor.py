"""Supervise the five-minute validation watchdog and restart it after failures.

The flow starts the watchdog, records its launch and exit, waits briefly after an exit, and starts it again.
"""
from __future__ import annotations

import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


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


def main() -> int:
    """Run and restart the validation watchdog forever."""
    # Keep the watchdog independent from the training worker.
    repo = Path(__file__).resolve().parents[1]
    log_path = repo / "logs/validation_supervisor.log"
    command = [sys.executable, "-u", "-m", "experiments.validation_watchdog", "--interval-seconds", "300"]
    while True:
        # Start one watchdog child and capture its output.
        write_log(log_path, f"starting watchdog command={command}")
        with (repo / "logs/validation_watchdog.out").open("a", encoding="utf-8") as output:
            process = subprocess.Popen(command, cwd=repo, stdout=output, stderr=subprocess.STDOUT, start_new_session=True)
        return_code = process.wait()
        # Record the exit before restarting the watchdog.
        write_log(log_path, f"watchdog exited return_code={return_code}")
        time.sleep(2)


if __name__ == "__main__":
    raise SystemExit(main())
