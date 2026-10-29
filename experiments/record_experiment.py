"""Record one completed experiment without blocking the research worker loop.

The flow reads the declared experiment metadata and optional metrics artifact, appends an
append-only machine record, adds a research-log entry, updates the validation leaderboard, and
records explicit failures, preserves source-specific validation results, and commits the result files
under a repository lock before pushing the configured branch.
"""
from __future__ import annotations

import argparse
import fcntl
import json
import subprocess
import time
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


def git_command(repo: Path, arguments: list[str], check: bool = True) -> subprocess.CompletedProcess:
    """Run Git against the configured repository without changing ownership settings."""
    # Capture output so commit and push failures can be recorded without exposing environment secrets.
    return subprocess.run(["git", "-c", f"safe.directory={repo}", *arguments], cwd=repo, text=True, capture_output=True, check=check)


def commit_records(repo: Path, experiment_id: str) -> dict:
    """Commit result records and push them under one repository lock."""
    # Skip Git only when the supplied directory is not a repository.
    discovery = git_command(repo, ["rev-parse", "--git-dir"], check=False)
    if discovery.returncode:
        return {"status": "not a git repository"}
    git_dir = Path(discovery.stdout.strip())
    if not git_dir.is_absolute():
        git_dir = repo / git_dir
    with (git_dir / "research-commit.lock").open("w", encoding="utf-8") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        title = f"Record research experiment {experiment_id}"
        notes = repo / "logs/notes.txt"
        files = ["logs/experiment_records.jsonl", "logs/research_log.md", "logs/leaderboard.md", "logs/results.txt", "logs/notes.txt"]
        # Include the tracked research state so queue changes remain durable with experiment records.
        if git_command(repo, ["ls-files", "--error-unmatch", "logs/research_state.json"], check=False).returncode == 0:
            files.append("logs/research_state.json")
        append_locked(notes, f"\n{timestamp()}: Commit `{title}` preserves the full experiment setup, metrics artifact, source-specific validation, explicit failure or test status, and aggregate official test measurement. The asynchronous recorder commits these records and tracked research state without delaying the next worker.\n", repo / "logs/experiment_records.lock")
        try:
            git_command(repo, ["add", "--", *files])
            git_command(repo, ["commit", "-m", title])
            # Retry a GitHub DNS failure twice and preserve all other push errors immediately.
            for attempt in range(3):
                pushed = git_command(repo, ["push"], check=False)
                if pushed.returncode == 0:
                    return {"status": "pushed"}
                error = pushed.stderr.strip() or pushed.stdout.strip()
                dns_failure = "Could not resolve host" in error or "Could not resolve hostname" in error or "Temporary failure in name resolution" in error
                if not dns_failure or attempt == 2:
                    raise RuntimeError(error)
                time.sleep(10)
        except (subprocess.CalledProcessError, RuntimeError) as error:
            # Save an explicit local failure record after the bounded push attempt fails.
            detail = getattr(error, "stderr", None) or str(error)
            failure = {"timestamp": timestamp(), "experiment_id": experiment_id, "error": detail}
            append_locked(repo / "logs/experiment_recorder_errors.jsonl", json.dumps(failure) + "\n", repo / "logs/experiment_records.lock")
            append_locked(notes, f"\n{timestamp()}: Commit `Record experiment synchronization failure` records the failed commit or push for {experiment_id}: {detail}. The result remains local and the worker queue continues.\n", repo / "logs/experiment_records.lock")
            git_command(repo, ["add", "--", "logs/experiment_recorder_errors.jsonl", "logs/notes.txt"], check=False)
            git_command(repo, ["commit", "-m", "Record experiment synchronization failure"], check=False)
            return {"status": "failed", "error": detail}
    return {"status": "failed", "error": "Git synchronization did not complete."}


def record(repo: Path, args: argparse.Namespace) -> dict:
    """Write durable records for one experiment."""
    # Normalize the supported training artifact schemas before updating durable result files.
    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = repo / output_dir
    metrics = load_metrics(output_dir)
    development = metrics.get("development_metrics") or {}
    selected_method = metrics.get("selected_fusion_by_clean_validation")
    if not development and selected_method and selected_method in (metrics.get("validation_metrics") or {}):
        # Preserve the selected inference candidate's clean-validation score.
        development = metrics["validation_metrics"][selected_method]
    source_validation = {key: value for key, value in metrics.items() if key.endswith("_validation_metrics") and value}
    checkpoint_records = metrics.get("epoch_records") or metrics.get("checkpoint_evaluations") or []
    latest_checkpoint = checkpoint_records[-1] if checkpoint_records else {}
    train_metrics = metrics.get("train_metrics") or latest_checkpoint.get("training_metrics") or {}
    if not development:
        development = latest_checkpoint.get("balanced_heldout_validation_metrics") or latest_checkpoint.get("heldout_validation_metrics") or {}
    if not source_validation:
        source_validation = {
            key: latest_checkpoint[key]
            for key in ("bfcl_heldout_validation_metrics", "original_heldout_validation_metrics", "source_validation_metrics")
            if latest_checkpoint.get(key)
        }
        if latest_checkpoint.get("heldout_validation_metrics"):
            source_validation["heldout_validation_metrics"] = latest_checkpoint["heldout_validation_metrics"]
    # Preserve aggregate official test metrics when the worker is a black-box evaluator.
    official_test = metrics.get("official_test_metrics") or {}
    if not official_test and selected_method and selected_method in (metrics.get("test_metrics") or {}):
        # Record the selected frozen candidate while keeping all candidates in metadata.
        official_test = metrics["test_metrics"][selected_method]
    if not official_test and latest_checkpoint.get("black_box_test_metrics"):
        official_test = latest_checkpoint["black_box_test_metrics"]
    aggregate_only = bool((metrics.get("test_measurement_only") and metrics.get("black_box")) or (metrics.get("test_black_box") and official_test))
    if not official_test and aggregate_only:
        official_test = {key: metrics.get("metrics", {}).get(key) for key in ("accuracy", "macro_f1") if key in metrics.get("metrics", {})}
    if args.development_accuracy is not None:
        development["accuracy"] = float(args.development_accuracy)
    if args.development_macro_f1 is not None:
        development["macro_f1"] = float(args.development_macro_f1)
    status = args.status or metrics.get("status")
    if not status:
        has_experiment_evidence = bool(development or source_validation or official_test or train_metrics)
        status = "failed" if str(args.exit_code) not in ("0", "unknown", "None") else ("completed" if has_experiment_evidence else "failed_or_incomplete")
    test_status = metrics.get("test_status") or ("measured" if official_test else "not measured")
    if status in ("failed", "test skipped", "test_skipped"):
        test_status = "failed" if status == "failed" else "test skipped"
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
        "train_metrics": train_metrics,
        "wandb_run_id": args.wandb_run_id or metrics.get("wandb_run_id"),
        "wandb_run_url": args.wandb_run_url or metrics.get("wandb_run_url"),
        "official_test_loaded": metrics.get("official_test_loaded", True if aggregate_only else None),
        "official_test_metrics": official_test,
        "source_validation_metrics": source_validation,
        "test_status": test_status,
        "failure_reason": metrics.get("failure_reason") or metrics.get("error") or metrics.get("reason"),
        "metadata": metrics,
    }
    journal = repo / "logs/experiment_records.jsonl"
    lock = repo / "logs/experiment_records.lock"
    append_locked(journal, json.dumps(record, sort_keys=True) + "\n", lock)
    # Preserve the complete setup and artifact metadata in the repository results file.
    result_entry = f"\n## {args.experiment_id}\n\nThe complete setup and observed results are recorded below. Source validation splits are separate and are not ranked together.\n\n```json\n{json.dumps(record, indent=2, sort_keys=True)}\n```\n"
    append_locked(repo / "logs/results.txt", result_entry, lock)
    accuracy = development.get("accuracy", "—")
    macro_f1 = development.get("macro_f1", "—")
    run_text = record["wandb_run_id"] or "not available"
    log_entry = (
        f"\n## {args.experiment_id}\n\n"
        f"Timestamp: {record['timestamp']}. Status: {status}.\n\n"
        f"Setup: {json.dumps(record['command'])}. Output: {output_dir}. "
        f"W&B run: {run_text}.\n\n"
        f"Clean development accuracy: {accuracy}. Clean development macro F1: {macro_f1}. "
        f"Official test loaded: {record['official_test_loaded']}. Test status: {test_status}. Official test metrics: {json.dumps(official_test)}.\n\n"
        f"Separate source validation metrics: {json.dumps(source_validation)}. Failure reason: {record['failure_reason']}.\n\n"
        "This record was written automatically. Candidate selection must use clean validation only.\n"
    )
    append_locked(repo / "logs/research_log.md", log_entry, repo / "logs/research_log.lock")
    leaderboard_entry = (
        f"| Candidate | {args.experiment_id} | {accuracy} | {macro_f1} | "
        f"[metrics]({output_dir}/metrics.json) | {status} |\n"
    )
    if development or not source_validation:
        append_locked(repo / "logs/leaderboard.md", leaderboard_entry, repo / "logs/leaderboard.lock")
    else:
        # Keep source-specific results outside the unified validation ranking.
        source_entry = f"\nSource-specific result `{args.experiment_id}` has status {status}. Its separate validation metrics are {json.dumps(source_validation)}. These values are not ranked against other splits.\n"
        append_locked(repo / "logs/leaderboard.md", source_entry, repo / "logs/leaderboard.lock")
    # Append a separate aggregate-only test row without changing validation ranking.
    if official_test:
        test_entry = f"\n| {args.experiment_id} | {official_test.get('accuracy', '—')} | {official_test.get('macro_f1', '—')} | {record['wandb_run_id'] or 'not available'} | Aggregate-only frozen test measurement |\n"
        append_locked(repo / "logs/leaderboard.md", test_entry, repo / "logs/leaderboard.lock")
    # Synchronize only recorder outputs while the watchdog can launch the next experiment independently.
    if not getattr(args, "no_git", False):
        record["git_sync"] = commit_records(repo, args.experiment_id)
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
    parser.add_argument("--no-git", action="store_true", help="Write isolated records without committing or pushing.")
    args = parser.parse_args()
    record(args.repo, args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
