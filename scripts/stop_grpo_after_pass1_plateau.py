#!/usr/bin/env python3
"""Watch fixed-batch GRPO evaluation files and stop the isolated trainer after a pass@1 plateau."""

from __future__ import annotations

import argparse
import json
import os
import re
import signal
import time
from datetime import datetime, timezone
from pathlib import Path


def append_record(path: Path, record: dict[str, object]) -> None:
    """Append one durable JSON record to the monitor history."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as output_file:
        output_file.write(json.dumps(record, sort_keys=True) + "\n")
        output_file.flush()
        os.fsync(output_file.fileno())


def stop_process_group(process_group_id: int, timeout_seconds: float) -> None:
    """Stop the supervisor and its trainer children, then force-stop any stragglers."""
    try:
        os.killpg(process_group_id, signal.SIGTERM)
    except ProcessLookupError:
        return
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            os.killpg(process_group_id, 0)
        except ProcessLookupError:
            return
        time.sleep(0.5)
    try:
        os.killpg(process_group_id, signal.SIGKILL)
    except ProcessLookupError:
        return


def main() -> int:
    """Track scheduled pass@1 evaluations and stop after the configured plateau."""
    argument_parser = argparse.ArgumentParser(description=__doc__)
    argument_parser.add_argument("output_dir", type=Path)
    argument_parser.add_argument("--process-group-id", type=int, required=True)
    argument_parser.add_argument("--eval-interval", type=int, default=10)
    argument_parser.add_argument("--patience", type=int, default=3)
    argument_parser.add_argument("--poll-seconds", type=float, default=2.0)
    argument_parser.add_argument("--stop-timeout-seconds", type=float, default=15.0)
    arguments = argument_parser.parse_args()

    output_dir = arguments.output_dir.resolve()
    history_path = output_dir / "pass1-plateau-monitor.jsonl"
    stop_path = output_dir / "plateau-stop.json"
    evaluation_pattern = re.compile(r"training-step-(\d+)-metrics\.json$")
    best_score: float | None = None
    last_step = -1
    stagnant_evaluations = 0

    while True:
        if stop_path.exists():
            return 0
        if best_score is None:
            baseline_path = output_dir / "training-step-0-metrics.json"
            if baseline_path.is_file():
                baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
                best_score = float(baseline["pass_at_1"])
                last_step = 0
                append_record(history_path, {
                    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                    "step": 0,
                    "pass_at_1": best_score,
                    "best_pass_at_1": best_score,
                    "consecutive_non_improvements": 0,
                    "event": "baseline",
                })

        if best_score is not None:
            evaluations: list[tuple[int, Path]] = []
            for metrics_path in output_dir.glob("training-step-*-metrics.json"):
                match = evaluation_pattern.fullmatch(metrics_path.name)
                if match is None:
                    continue
                step = int(match.group(1))
                if step > last_step and step > 0 and step % arguments.eval_interval == 0:
                    evaluations.append((step, metrics_path))
            for step, metrics_path in sorted(evaluations):
                metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
                score = float(metrics["pass_at_1"])
                if score > best_score:
                    best_score = score
                    stagnant_evaluations = 0
                    event = "new_best"
                else:
                    stagnant_evaluations += 1
                    event = "no_improvement"
                last_step = step
                record = {
                    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                    "step": step,
                    "pass_at_1": score,
                    "best_pass_at_1": best_score,
                    "consecutive_non_improvements": stagnant_evaluations,
                    "event": event,
                }
                append_record(history_path, record)
                print(json.dumps(record, sort_keys=True), flush=True)
                if stagnant_evaluations >= arguments.patience:
                    stop_record = {**record, "stop_reason": "pass_at_1_plateau"}
                    stop_path.write_text(json.dumps(stop_record, indent=2) + "\n", encoding="utf-8")
                    append_record(history_path, stop_record)
                    stop_process_group(arguments.process_group_id, arguments.stop_timeout_seconds)
                    return 0

        try:
            os.killpg(arguments.process_group_id, 0)
        except ProcessLookupError:
            append_record(history_path, {
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "step": last_step,
                "event": "trainer_process_group_exited_before_plateau",
            })
            return 1
        time.sleep(arguments.poll_seconds)


if __name__ == "__main__":
    raise SystemExit(main())
