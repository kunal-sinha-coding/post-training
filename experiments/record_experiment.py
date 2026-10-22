"""Record one completed experiment without blocking the research worker loop.

The flow reads the declared experiment metadata and optional metrics artifact, appends an
append-only machine record, adds a research-log entry, updates the validation leaderboard, and
records failures as incomplete experiments when the training artifact is missing.
"""
from __future__ import annotations

import argparse
import fcntl
import json
from datetime import datetime, timezone
from pathlib import Path


def timestamp() -> str:
    """Return a UTC timestamp for the durable experiment record."""
    # Use timezone-aware timestamps so records remain comparable across processes.
    return datetime.now(timezone.utc).isoformat()


def load_metrics(output_dir: Path) -> dict:
    """Load the optional clean-validation metrics artifact."""
    # Treat missing metrics as a recoverable failed or incomplete experiment.
    metrics_path = output_dir / "metrics.json"
    if not metrics_path.exists():
        return {}
    try:
        return json.loads(metrics_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def append_locked(path: Path, text: str, lock_path: Path) -> None:
    """Append text while serializing concurrent recorder processes."""
    # Use a separate lock file so markdown and JSON updates cannot interleave.
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("w", encoding="utf-8") as lock_stream:
        fcntl.flock(lock_stream.fileno(), fcntl.LOCK_EX)
        with path.open("a", encoding="utf-8") as stream:
            stream.write(text)


def record(repo: Path, args: argparse.Namespace) -> dict:
    """Write durable records for one experiment."""
    # Build a complete result or a minimal failure record before updating human-readable files.
    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = repo / output_dir
    metrics = load_metrics(output_dir)
    development = metrics.get("development_metrics") or {}
    # Preserve aggregate official test metrics when the worker is a black-box evaluator.
    official_test = metrics.get("official_test_metrics") or {}
    if args.development_accuracy is not None:
        development["accuracy"] = float(args.development_accuracy)
    if args.development_macro_f1 is not None:
        development["macro_f1"] = float(args.development_macro_f1)
    status = args.status or ("completed" if development or official_test else "failed_or_incomplete")
    record = {
        "experiment_id": args.experiment_id,
        "timestamp": timestamp(),
        "status": status,
        "command": json.loads(args.command_json),
        "output_dir": str(output_dir),
        "started_at": args.started_at,
        "exit_code": args.exit_code,
        "metrics_path": str(output_dir / "metrics.json"),
        "development_metrics": development,
        "train_metrics": metrics.get("train_metrics", {}),
        "wandb_run_id": args.wandb_run_id or metrics.get("wandb_run_id"),
        "wandb_run_url": args.wandb_run_url or metrics.get("wandb_run_url"),
        "official_test_loaded": metrics.get("official_test_loaded"),
        "official_test_metrics": official_test,
    }
    journal = repo / "logs/experiment_records.jsonl"
    lock = repo / "logs/experiment_records.lock"
    append_locked(journal, json.dumps(record, sort_keys=True) + "\n", lock)
    accuracy = development.get("accuracy", "—")
    macro_f1 = development.get("macro_f1", "—")
    run_text = record["wandb_run_id"] or "not available"
    log_entry = (
        f"\n## {args.experiment_id}\n\n"
        f"Timestamp: {record['timestamp']}. Status: {status}.\n\n"
        f"Setup: {json.dumps(record['command'])}. Output: {output_dir}. "
        f"W&B run: {run_text}.\n\n"
        f"Clean development accuracy: {accuracy}. Clean development macro F1: {macro_f1}. "
        f"Official test loaded: {record['official_test_loaded']}. Official test metrics: {json.dumps(official_test)}.\n\n"
        "This record was written automatically. Candidate selection must use clean validation only.\n"
    )
    append_locked(repo / "logs/research_log.md", log_entry, repo / "logs/research_log.lock")
    leaderboard_entry = (
        f"| Candidate | {args.experiment_id} | {accuracy} | {macro_f1} | "
        f"[metrics]({output_dir}/metrics.json) | {status} |\n"
    )
    append_locked(repo / "logs/leaderboard.md", leaderboard_entry, repo / "logs/leaderboard.lock")
    # Append a separate aggregate-only test row without changing validation ranking.
    if official_test:
        test_entry = f"\n| {args.experiment_id} | {official_test.get('accuracy', '—')} | {official_test.get('macro_f1', '—')} | {record['wandb_run_id'] or 'not available'} | Aggregate-only Qwen test measurement |\n"
        append_locked(repo / "logs/leaderboard.md", test_entry, repo / "logs/leaderboard.lock")
    return record


def main() -> int:
    """Parse recorder inputs and write the non-blocking completion record."""
    # Keep the recorder independent so its failure cannot prevent the next worker launch.
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--experiment-id", required=True)
    parser.add_argument("--command-json", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--started-at", required=True)
    parser.add_argument("--exit-code", default="unknown")
    parser.add_argument("--wandb-run-id")
    parser.add_argument("--wandb-run-url")
    parser.add_argument("--development-accuracy")
    parser.add_argument("--development-macro-f1")
    parser.add_argument("--status")
    args = parser.parse_args()
    record(args.repo, args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
