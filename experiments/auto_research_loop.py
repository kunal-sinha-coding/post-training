"""Run the configured When2Call research step continuously.

The supervisor launches one leakage-safe inference evaluation, records its output,
waits for the configured interval, and repeats until it receives a termination signal.
"""
from __future__ import annotations

import argparse
import signal
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path


STOP = False


def stop_loop(signum: int, frame: object) -> None:
    """Request clean shutdown after the current child process exits."""
    # Set a shared flag so the loop does not start another experiment.
    global STOP
    STOP = True


def run_step(repo: Path, log_path: Path) -> int:
    """Run the current best inference route and append its output to the log."""
    # Keep the step deterministic and free of ground-truth prediction inputs.
    command = [
        "python",
        "-u",
        "experiments/ensemble_when2call.py",
        "--ranker",
        "outputs/when2call-auto-research/candidate_ranker_binary_9000_len1024.json",
        "--jev",
        "outputs/when2call-inference-best/predictions.jsonl",
        "--switch-complete-request",
        "--invalid-tool-to-cannot",
        "--invalid-non-tool-to-cannot",
        "--valid-cannot-to-tool",
        "--argument-evidence-to-tool",
        "--normalized-value-evidence-to-tool",
        "--route-label",
        "request_for_info,tool_call,direct",
        "--output",
        "outputs/when2call-auto-research/ensemble_best.json",
    ]
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as stream:
        stamp = datetime.now(timezone.utc).isoformat()
        stream.write(f"\n[{stamp}] starting research step\n")
        stream.flush()
        result = subprocess.run(command, cwd=repo, stdout=stream, stderr=subprocess.STDOUT, check=False)
        stream.write(f"[{datetime.now(timezone.utc).isoformat()}] step exit code {result.returncode}\n")
    return result.returncode


def main() -> int:
    """Run research steps until an explicit stop signal arrives."""
    # Parse the repository, interval, and durable log locations.
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--interval-seconds", type=int, default=900)
    parser.add_argument("--log", type=Path, default=Path("logs/auto_research_loop.log"))
    args = parser.parse_args()
    signal.signal(signal.SIGTERM, stop_loop)
    signal.signal(signal.SIGINT, stop_loop)
    log_path = args.log if args.log.is_absolute() else args.repo / args.log
    while not STOP:
        run_step(args.repo, log_path)
        for _ in range(max(1, args.interval_seconds)):
            if STOP:
                break
            time.sleep(1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
