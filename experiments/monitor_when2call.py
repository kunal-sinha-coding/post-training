"""Monitor a When2Call W&B run and launch the next configured experiment after plateau.

The monitor reads completed test evaluations from W&B, tracks the best macro F1 and
accuracy independently, kills the run after three evaluations without either gain,
then starts the next training command and follows its newly written run identifier.
"""

from __future__ import annotations

import argparse
import os
import signal
import subprocess
import time
from pathlib import Path

import wandb


def read_run_evaluations(run: object) -> list[dict[str, float]]:
    """Read distinct test evaluation points from the W&B run history."""
    # Keep only rows that contain both monitored metrics and deduplicate by optimizer step.
    points: dict[int, dict[str, float]] = {}
    for row in run.scan_history(keys=["optimizer_step", "test_eval/macro_f1", "test_eval/accuracy"]):
        step = row.get("optimizer_step")
        macro_f1 = row.get("test_eval/macro_f1")
        accuracy = row.get("test_eval/accuracy")
        if step is None or macro_f1 is None or accuracy is None:
            continue
        points[int(step)] = {"step": int(step), "macro_f1": float(macro_f1), "accuracy": float(accuracy)}
    return [points[step] for step in sorted(points)]


def wait_for_run_id(path: Path, timeout_seconds: int = 600) -> str:
    """Wait for the next training process to publish its W&B run identifier."""
    # Poll a small metadata file so the monitor can follow a newly created W&B run.
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if path.exists():
            value = path.read_text(encoding="utf-8").strip()
            if value:
                return value
        time.sleep(5)
    raise TimeoutError(f"Timed out waiting for W&B run ID at {path}.")


def monitor_run(api: wandb.Api, run_id: str, pid: int, patience: int, poll_seconds: int) -> tuple[bool, int]:
    """Monitor one process until it plateaus or exits."""
    # Stop only after three new evaluations with no improvement in either metric.
    run = api.run(run_id)
    seen_steps: set[int] = set()
    best_macro_f1 = float("-inf")
    best_accuracy = float("-inf")
    stagnant = 0
    while True:
        evaluations = read_run_evaluations(run)
        for point in evaluations:
            if int(point["step"]) in seen_steps:
                continue
            seen_steps.add(int(point["step"]))
            improved = point["macro_f1"] > best_macro_f1 or point["accuracy"] > best_accuracy
            best_macro_f1 = max(best_macro_f1, point["macro_f1"])
            best_accuracy = max(best_accuracy, point["accuracy"])
            stagnant = 0 if improved else stagnant + 1
            print({"run": run_id, "step": point["step"], "best_macro_f1": best_macro_f1, "best_accuracy": best_accuracy, "stagnant_evaluations": stagnant}, flush=True)
            if stagnant >= patience:
                if pid > 0:
                    os.kill(pid, signal.SIGKILL)
                return True, len(seen_steps)
        if pid > 0:
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                return False, len(seen_steps)
        time.sleep(poll_seconds)


def main() -> int:
    """Monitor the current pairwise run, then monitor the combined-data cross-entropy run."""
    # Keep the next command and data selection explicit in the monitor invocation.
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", default="kunal-personal/post-training")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--pid", type=int, required=True)
    parser.add_argument("--next-run-id-file", required=True)
    parser.add_argument("--next-log", required=True)
    parser.add_argument("--poll-seconds", type=int, default=30)
    parser.add_argument("--patience", type=int, default=3)
    parser.add_argument("--no-restart", action="store_true")
    args = parser.parse_args()
    api = wandb.Api()
    stopped, _ = monitor_run(api, f"{args.project}/{args.run_id}", args.pid, args.patience, args.poll_seconds)
    if not stopped or args.no_restart:
        return 0
    command = ["python", "-u", "experiments/train_when2call_jina.py", "--loss-function", "cross_entropy", "--dataset", "combined"]
    log_path = Path(args.next_log)
    with log_path.open("a", encoding="utf-8") as log_file:
        child_environment = os.environ.copy()
        child_environment.setdefault("HF_HOME", "/tmp/jina_hf_cache_pairwise")
        child_environment.setdefault("HF_MODULES_CACHE", "/tmp/jina_modules_cache_pairwise")
        process = subprocess.Popen(command, cwd=Path(__file__).resolve().parents[1], stdout=log_file, stderr=subprocess.STDOUT, env=child_environment)
    next_run_id = wait_for_run_id(Path(args.next_run_id_file))
    monitor_run(api, f"{args.project}/{next_run_id}", process.pid, args.patience, args.poll_seconds)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
