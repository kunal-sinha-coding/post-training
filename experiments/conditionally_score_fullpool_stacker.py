"""Score a clean-validation-winning full-pool stacker on the aggregate test interface.

The flow reads the completed stacker validation record, compares its validation accuracy with
the frozen Qwen and ensemble baselines, and either records a validation-based skip or prepares
and measures the frozen stacker with aggregate-only test metrics. Test results never select it.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def main() -> int:
    """Run the stacker test only when clean validation supports it."""
    # Freeze the training record and output locations before deciding whether test data may load.
    parser = argparse.ArgumentParser()
    parser.add_argument("--training-metrics", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--qwen-checkpoint", required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    metrics_path = args.training_metrics
    if not metrics_path.exists():
        result = {"status": "skipped", "reason": "Stacker metrics are missing.", "official_test_loaded": False}
        (args.output_dir / "metrics.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        return 0
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    baselines = metrics.get("baseline_validation_metrics", {})
    validation = metrics.get("heldout_validation_metrics", {})
    baseline_accuracy = max((item.get("accuracy", -1.0) for item in baselines.values()), default=-1.0)
    selected_accuracy = validation.get("accuracy", -1.0)
    if metrics.get("official_test_loaded") or metrics.get("validation_examples", 501) > 500 or selected_accuracy <= baseline_accuracy:
        # Do not expose test data unless the stacker wins on the capped clean validation set.
        result = {"status": "skipped", "reason": "The stacker did not strictly beat every clean-validation baseline in accuracy or the training record indicates test access.", "official_test_loaded": False, "training_metrics_path": str(metrics_path), "training_metrics": metrics.get("training_metrics"), "heldout_validation_metrics": validation, "baseline_validation_metrics": baselines, "selection_metric": "clean validation accuracy"}
        (args.output_dir / "metrics.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(result, indent=2))
        return 0
    # Prepare a frozen stacker manifest using only the selected clean-validation artifact.
    stacker_artifact = str(metrics["stacker_artifact"])
    common = ["--work-dir", str(args.work_dir), "--suite", "single-stacker", "--qwen-checkpoint", args.qwen_checkpoint, "--stacker-artifact", stacker_artifact, "--methods", "single_stacker", "--primary-method", "single_stacker", "--batch-size", "4"]
    prepare = [sys.executable, "-u", "-m", "experiments.existing_when2call_hybrid", "prepare", *common, "--output-dir", str(args.output_dir / "prepare")]
    prepared = subprocess.run(prepare, check=False)
    if prepared.returncode != 0:
        raise RuntimeError(f"Frozen stacker preparation failed with exit code {prepared.returncode}.")
    # Measure the frozen stacker and baselines once after validation-based selection is complete.
    test = [sys.executable, "-u", "-m", "experiments.existing_when2call_hybrid", "test", *common, "--output-dir", str(args.output_dir)]
    measured = subprocess.run(test, check=False)
    if measured.returncode != 0:
        raise RuntimeError(f"Aggregate black-box measurement failed with exit code {measured.returncode}.")
    # Join the recorded fit and clean-validation evidence with the aggregate test result.
    result_path = args.output_dir / "metrics.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    result["training_metrics"] = metrics.get("training_metrics")
    result["heldout_validation_metrics"] = validation
    result["baseline_validation_metrics"] = baselines
    result["training_metrics_path"] = str(metrics_path)
    result["stacker_artifact"] = stacker_artifact
    result["selection_metric"] = "clean validation accuracy"
    result_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
