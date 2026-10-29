"""Continue balanced synthetic training only when clean validation improves.

The flow requires complete evidence from the first balanced-pilot epoch, compares its clean
validation metrics with the recorded baseline, skips without training on a tie or regression,
and otherwise trains one more epoch with the same data and fixed optimization settings.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def read_metrics(path: Path) -> dict:
    """Load the completed pilot artifact and require all measured evidence."""
    # Fail before any continuation if the prior checkpoint evidence is unavailable.
    if not path.is_file():
        raise FileNotFoundError(f"Required metrics are missing: {path}")
    # Parse the full artifact so selection uses the saved epoch metrics.
    metrics = json.loads(path.read_text(encoding="utf-8"))
    epochs = metrics.get("epoch_records") or []
    if not epochs:
        raise ValueError("The balanced pilot has no completed epoch record.")
    # Require training, clean validation, and aggregate test measurements before another epoch.
    latest = epochs[-1]
    if not latest.get("training_metrics") or not latest.get("heldout_validation_metrics") or not latest.get("black_box_test_metrics"):
        raise ValueError("The completed balanced pilot is missing a required measurement.")
    return metrics


def main() -> int:
    """Gate one continuation epoch on clean-validation improvement only."""
    # Parse the previous run, baseline, and next output locations.
    parser = argparse.ArgumentParser()
    parser.add_argument("--pilot-metrics", type=Path, required=True)
    parser.add_argument("--pilot-checkpoint", type=Path, required=True)
    parser.add_argument("--pilot-data", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--baseline-accuracy", type=float, required=True)
    parser.add_argument("--baseline-macro-f1", type=float, required=True)
    args = parser.parse_args()
    # Read the completed result and compare clean-validation accuracy then macro F1.
    metrics = read_metrics(args.pilot_metrics)
    previous = metrics["epoch_records"][-1]
    validation = previous["heldout_validation_metrics"]
    candidate_score = (float(validation["accuracy"]), float(validation["macro_f1"]))
    baseline_score = (args.baseline_accuracy, args.baseline_macro_f1)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    # Preserve complete source evidence if validation does not justify another training epoch.
    if candidate_score <= baseline_score:
        result = {"status": "skipped", "reason": "Clean validation did not improve over baseline.", "training_metrics_status": "not applicable because no continuation training was run", "train_metrics": previous["training_metrics"], "development_metrics": validation, "official_test_metrics": previous["black_box_test_metrics"], "test_status": "measured", "selection_metric": "clean validation accuracy then macro F1", "test_metrics_used_for_selection": False, "source_metrics_path": str(args.pilot_metrics)}
        (args.output_dir / "metrics.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(result, indent=2), flush=True)
        return 0
    # Fix the same balanced data and optimization setup for one more epoch.
    command = [sys.executable, "-u", "-m", "experiments.train_qwen_when2call_fullpool", "--output-dir", str(args.output_dir), "--adapter-checkpoint", str(args.pilot_checkpoint), "--synthetic-only", "--augmentation-jsonl", str(args.pilot_data), "--validation-source", "sft", "--validation-sample-size", "500", "--validation-seed", "20261053", "--training-eval-sample-size", "500", "--training-eval-seed", "20261059", "--eval-batch-size", "8", "--epochs", "1", "--learning-rate", "5e-6", "--weight-decay", "0.01", "--baseline-validation-accuracy", str(validation["accuracy"]), "--baseline-validation-macro-f1", str(validation["macro_f1"]), "--stop-on-validation-non-improvement", "--seed", "20261198"]
    # Run the next epoch and preserve its exact parent selection in the final artifact.
    completed = subprocess.run(command, check=False)
    if completed.returncode != 0:
        return completed.returncode
    # Link the continuation result to the clean-validation-selected parent.
    result_path = args.output_dir / "metrics.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    result["continuation_gate"] = {"parent_metrics_path": str(args.pilot_metrics), "parent_checkpoint": str(args.pilot_checkpoint), "parent_validation_metrics": validation, "baseline_validation_metrics": {"accuracy": args.baseline_accuracy, "macro_f1": args.baseline_macro_f1}, "selection_metric": "clean validation accuracy then macro F1", "test_metrics_used_for_selection": False}
    result_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
