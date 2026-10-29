"""Select the clean-validation champion, then train on a balanced synthetic pilot.

The flow requires complete evidence from the active regularization run, compares its clean
validation metrics with the saved baseline, checks the generated label counts, then runs one
synthetic-only epoch and adds checkpoint-selection provenance to the saved metrics.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

BASE_CHECKPOINT = "outputs/qwen-when2call-fullpool-base-seed20261055/epoch-02"
BASE_ACCURACY = 0.962
BASE_MACRO_F1 = 0.48832640709774233


def read_json(path: Path) -> dict:
    """Load one completed JSON artifact and fail if it is missing or invalid."""
    # Require durable evidence before any follow-up training begins.
    if not path.is_file():
        raise FileNotFoundError(f"Required completed artifact is missing: {path}")
    # Parse the complete artifact so later selection never relies on partial output.
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    """Choose a checkpoint using clean validation and train one balanced pilot epoch."""
    # Parse the completed-run artifacts and output location before selecting a model.
    parser = argparse.ArgumentParser()
    parser.add_argument("--regularization-metrics", type=Path, required=True)
    parser.add_argument("--generation-metrics", type=Path, required=True)
    parser.add_argument("--pilot-data", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    # Require the prior experiment to have training, clean-validation, and aggregate test evidence.
    previous = read_json(args.regularization_metrics)
    epochs = previous.get("epoch_records") or []
    if previous.get("status") not in (None, "completed") or not epochs:
        raise ValueError("The regularization run is not complete.")
    # Keep the evidence gate strict before a new model experiment starts.
    evidence = epochs[-1]
    if not evidence.get("training_metrics") or not evidence.get("heldout_validation_metrics") or not evidence.get("black_box_test_metrics"):
        raise ValueError("The regularization run is missing required evidence.")
    # Require a completed and sufficiently balanced generated pool.
    generated = read_json(args.generation_metrics)
    if generated.get("status") != "completed" or not args.pilot_data.is_file():
        raise ValueError("The balanced synthetic pilot is not ready.")
    # Read only the aggregate data-generation counts and training examples.
    rows = [json.loads(line) for line in args.pilot_data.read_text(encoding="utf-8").splitlines() if line.strip()]
    counts = {str(label): sum(int(row["label"]) == label for row in rows) for label in (0, 1, 2)}
    if len(rows) < 200 or min(counts.values()) < 50:
        raise ValueError(f"Generated class counts are not suitable for the planned pilot: {counts}")
    # Compare the completed checkpoint with the baseline using clean validation only.
    validation = evidence["heldout_validation_metrics"]
    candidate_key = (float(validation["accuracy"]), float(validation["macro_f1"]))
    baseline_key = (BASE_ACCURACY, BASE_MACRO_F1)
    use_candidate = candidate_key > baseline_key
    checkpoint = str(Path(args.regularization_metrics).parent / "epoch-01") if use_candidate else BASE_CHECKPOINT
    selected_metrics = validation if use_candidate else {"accuracy": BASE_ACCURACY, "macro_f1": BASE_MACRO_F1}
    # Build one fixed training command that changes only the synthetic data recipe.
    command = [sys.executable, "-u", "-m", "experiments.train_qwen_when2call_fullpool", "--output-dir", str(args.output_dir), "--adapter-checkpoint", checkpoint, "--synthetic-only", "--augmentation-jsonl", str(args.pilot_data), "--validation-source", "sft", "--validation-sample-size", "500", "--validation-seed", "20261053", "--training-eval-sample-size", "500", "--training-eval-seed", "20261059", "--eval-batch-size", "8", "--epochs", "1", "--learning-rate", "5e-6", "--weight-decay", "0.01", "--baseline-validation-accuracy", str(selected_metrics["accuracy"]), "--baseline-validation-macro-f1", str(selected_metrics["macro_f1"]), "--seed", "20261197"]
    # Save the clean-validation selection decision before training starts.
    args.output_dir.mkdir(parents=True, exist_ok=True)
    selection = {"selected_checkpoint": checkpoint, "selection_metric": "clean validation accuracy then macro F1", "selected_validation_metrics": selected_metrics, "regularization_candidate_validation_metrics": validation, "baseline_validation_metrics": {"accuracy": BASE_ACCURACY, "macro_f1": BASE_MACRO_F1}, "generated_class_counts": counts, "test_metrics_used_for_selection": False, "training_command": command}
    (args.output_dir / "checkpoint-selection.json").write_text(json.dumps(selection, indent=2) + "\n", encoding="utf-8")
    # Run the trainer and preserve its exit status for the research watchdog.
    completed = subprocess.run(command, check=False)
    if completed.returncode != 0:
        return completed.returncode
    # Attach the checkpoint choice and generation counts to the final training result.
    metrics_path = args.output_dir / "metrics.json"
    result = read_json(metrics_path)
    result["parent_checkpoint_selection"] = selection
    metrics_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
