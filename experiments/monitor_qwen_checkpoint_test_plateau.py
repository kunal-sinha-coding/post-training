"""Monitor aggregate checkpoint test accuracy and stop one approved training run at a plateau.

The flow reads aggregate-only checkpoint records from one active Qwen run, reports each new
measurement to its Codex thread, and stops that run after the first non-improving checkpoint.
"""
from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import time
from pathlib import Path


def read_records(path: Path) -> list[dict]:
    """Read complete checkpoint records while ignoring a partially written final line."""
    # Parse each complete JSONL row independently so an active writer cannot corrupt the monitor.
    if not path.exists():
        return []
    records = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return sorted(records, key=lambda item: int(item.get("step", 0)))


def process_is_live(pid: int) -> bool:
    """Return whether the monitored training process is still running."""
    # Check process state so an exited zombie does not keep the monitor alive.
    try:
        state = subprocess.check_output(["ps", "-o", "stat=", "-p", str(pid)], text=True).strip()
    except subprocess.CalledProcessError:
        return False
    return bool(state) and not state.startswith("Z")


def notify_codex(thread: str, message: str, log_path: Path) -> None:
    """Send a checkpoint report to the active Codex thread and keep a local copy."""
    # Queue the aggregate result so the user receives it without waiting for a later status request.
    result = subprocess.run(["codex", "queue", "--thread", thread, "--message", message], text=True, capture_output=True, check=False)
    with log_path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps({"message": message, "queue_exit_code": result.returncode, "queue_error": result.stderr[-500:]}) + "\n")


def wait_until_training_resumes(heartbeat_path: Path, step: int, pid: int) -> None:
    """Wait until the checkpoint callback returns before stopping a plateaued run."""
    # Avoid interrupting the in-progress test evaluator or its checkpoint record write.
    while process_is_live(pid):
        try:
            heartbeat = json.loads(heartbeat_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            heartbeat = {}
        if heartbeat.get("phase") == "training" and int(heartbeat.get("step", 0)) >= step:
            return
        time.sleep(5)


def main() -> int:
    """Report each new aggregate test checkpoint and stop at the first plateau."""
    # Parse the active run, its established baseline, and the minimum step for early stopping.
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--pid", type=int, required=True)
    parser.add_argument("--thread", required=True)
    parser.add_argument("--baseline-step", type=int, default=1000)
    parser.add_argument("--minimum-stop-step", type=int, default=2000)
    parser.add_argument("--poll-seconds", type=int, default=5)
    args = parser.parse_args()
    checkpoint_path = args.output_dir / "checkpoint_validation.jsonl"
    heartbeat_path = args.output_dir / "heartbeat.json"
    log_path = args.output_dir / "checkpoint_test_plateau_monitor.jsonl"
    records = read_records(checkpoint_path)
    baseline = next((item for item in records if int(item.get("step", 0)) == args.baseline_step), None)
    previous_step = args.baseline_step
    previous_accuracy = (baseline or {}).get("aggregate_black_box_test_metrics", {}).get("accuracy")
    if previous_accuracy is None:
        raise RuntimeError(f"No aggregate test baseline exists at step {args.baseline_step}.")
    # Check only new completed records and compare each one with the immediately prior checkpoint.
    while process_is_live(args.pid):
        for record in read_records(checkpoint_path):
            step = int(record.get("step", 0))
            if step <= previous_step:
                continue
            test_metrics = record.get("aggregate_black_box_test_metrics") or {}
            if "accuracy" not in test_metrics:
                continue
            accuracy = float(test_metrics["accuracy"])
            training = record.get("training_probe_metrics", {})
            validation = record.get("preference_validation_metrics", {})
            message = (f"Full-Glaive checkpoint step {step} completed. Aggregate black-box test accuracy={accuracy:.6f}, "
                       f"macro_f1={float(test_metrics.get('macro_f1', 0.0)):.6f}; previous step {previous_step} accuracy={previous_accuracy:.6f}. "
                       f"Training probe accuracy={float(training.get('accuracy', 0.0)):.6f}, macro_f1={float(training.get('macro_f1', 0.0)):.6f}; "
                       f"clean preference validation accuracy={float(validation.get('accuracy', 0.0)):.6f}, macro_f1={float(validation.get('macro_f1', 0.0)):.6f}. "
                       "Test metrics are aggregate-only and are used only for the user-requested continuation rule.")
            notify_codex(args.thread, message, log_path)
            if step >= args.minimum_stop_step and accuracy <= previous_accuracy:
                wait_until_training_resumes(heartbeat_path, step, args.pid)
                if process_is_live(args.pid):
                    os.kill(args.pid, signal.SIGTERM)
                with log_path.open("a", encoding="utf-8") as stream:
                    stream.write(json.dumps({"stopped_at_step": step, "reason": "aggregate test accuracy did not improve", "accuracy": accuracy, "previous_accuracy": previous_accuracy}) + "\n")
                return 0
            previous_step = step
            previous_accuracy = accuracy
        time.sleep(max(1, args.poll_seconds))
    return 0


if __name__ == "__main__":
    # Return an error when the requested baseline is absent so an invalid stop rule cannot run silently.
    raise SystemExit(main())
