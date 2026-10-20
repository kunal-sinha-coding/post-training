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


def existing_watchdog() -> int | None:
    """Return the first live watchdog process identifier."""
    # Adopt an existing watchdog so the supervisor never creates a duplicate lock holder.
    output = subprocess.check_output(["pgrep", "-f", "experiments.validation_watchdog"], text=True)
    for value in output.split():
        pid = int(value)
        if pid != 0:
            return pid
    return None


def main() -> int:
    """Run and restart the validation watchdog forever."""
    # Keep the watchdog independent from the training worker.
    repo = Path(__file__).resolve().parents[1]
    log_path = repo / "logs/validation_supervisor.log"
    command = [sys.executable, "-u", "-m", "experiments.validation_watchdog", "--interval-seconds", "300"]
    while True:
        # Adopt one existing watchdog or start one child and capture its output.
        try:
            pid = existing_watchdog()
        except subprocess.CalledProcessError:
            pid = None
        if pid is not None:
            write_log(log_path, f"adopting watchdog pid={pid}")
            while True:
                time.sleep(5)
                if subprocess.run(["kill", "-0", str(pid)], check=False).returncode != 0:
                    break
            return_code = 0
        else:
            write_log(log_path, f"starting watchdog command={command}")
            with (repo / "logs/validation_watchdog.out").open("a", encoding="utf-8") as output:
                process = subprocess.Popen(command, cwd=repo, stdout=output, stderr=subprocess.STDOUT, start_new_session=True)
            return_code = process.wait()
        # Record the exit before restarting the watchdog.
        write_log(log_path, f"watchdog exited return_code={return_code}")
        time.sleep(2)


if __name__ == "__main__":
    raise SystemExit(main())
