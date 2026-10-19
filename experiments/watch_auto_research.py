"""Keep the When2Call auto research supervisor alive.

The watchdog checks the supervisor PID every five minutes, starts a detached
replacement when needed, and records each check and restart in a durable log.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path


def write_log(path: Path, message: str) -> None:
    """Append one timestamped watchdog event to the runtime log."""
    # Keep the monitor history durable and easy to inspect with tail.
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(f"[{datetime.now(timezone.utc).isoformat()}] {message}\n")


def process_alive(pid: int) -> bool:
    """Return whether the supervisor process currently exists."""
    # Signal zero checks process existence without changing process state.
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def start_supervisor(repo: Path, log_path: Path) -> int:
    """Start a detached supervisor and return its process identifier."""
    # Launch the restartable shell supervisor in a new session with inherited logs.
    output = (repo / "logs/auto_research_supervisor.out").open("a", encoding="utf-8")
    command = ["bash", "-c", "trap 'exit 0' TERM INT; while true; do python -u experiments/auto_research_loop.py --interval-seconds 900 --log logs/auto_research_loop.log; code=$?; echo \"$(date -u +%FT%TZ) supervisor exited code $code, restarting\" >> logs/auto_research_loop.log; sleep 5; done"]
    process = subprocess.Popen(command, cwd=repo, stdin=subprocess.DEVNULL, stdout=output, stderr=subprocess.STDOUT, start_new_session=True)
    output.close()
    (repo / "logs/auto_research_loop.pid").write_text(f"{process.pid}\n", encoding="utf-8")
    write_log(log_path, f"started supervisor pid {process.pid}")
    return process.pid


def main() -> int:
    """Check the supervisor forever at the configured interval."""
    # Parse paths and the five-minute watchdog interval.
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--interval-seconds", type=int, default=300)
    parser.add_argument("--log", type=Path, default=Path("logs/auto_research_watchdog.log"))
    args = parser.parse_args()
    log_path = args.log if args.log.is_absolute() else args.repo / args.log
    pid_path = args.repo / "logs/auto_research_loop.pid"
    while True:
        pid = int(pid_path.read_text(encoding="utf-8").strip()) if pid_path.exists() else 0
        if pid and process_alive(pid):
            write_log(log_path, f"supervisor pid {pid} is alive")
        else:
            write_log(log_path, "supervisor is not alive; restarting")
            start_supervisor(args.repo, log_path)
        time.sleep(max(30, args.interval_seconds))


if __name__ == "__main__":
    raise SystemExit(main())
