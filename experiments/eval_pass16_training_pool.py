"""Measure the pass@16 histogram of one model on the full reference training pool.

The script loads the same task pool, prompt format, and test reward that the reference SFT run uses.
It generates 16 samples at temperature 1.0 for every task with one isolated vLLM process and scores them with the training reward.
It writes the per-task pass counts, the full histogram, and the aggregate coverage metrics to one JSON file.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# Point the datasets cache at the workspace copy that already holds the MBPP Arrow splits.
os.environ.setdefault("TRAINING_HF_DATASETS_CACHE", "/workspace/.cache/huggingface/datasets")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.incremental_rejection_sampling_sft import load_config, load_training_tasks  # noqa: E402
from train import evaluate_training_mbpp_sampled  # noqa: E402


def main() -> None:
    """Run the sampled pass@16 evaluation for one model on the training pool."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--num-samples", type=int, default=16)
    parser.add_argument("--temperature", type=float, default=1.0)
    args = parser.parse_args()
    config = load_config(args.config)
    # Load the same fixed pool and prompt format that the reference training run uses.
    tasks = load_training_tasks(config)
    print(f"Loaded {len(tasks)} training tasks.", flush=True)
    # Override the sampled settings for a standalone run and keep the scorer quiet.
    args.output.parent.mkdir(parents=True, exist_ok=True)
    config["log_path"] = os.devnull
    config["training_eval_num_samples"] = int(args.num_samples)
    config["training_eval_temperature"] = float(args.temperature)
    # Generate and score the sampled completions with the training test reward.
    result = evaluate_training_mbpp_sampled(Path(args.model), tasks, config, args.output.stem)
    metrics = result["metrics"]
    payload = {
        "model": args.model,
        "config": str(args.config),
        "num_samples": int(args.num_samples),
        "temperature": float(args.temperature),
        "task_count": len(tasks),
        "metrics": metrics,
        "pass_counts": result["pass_counts"],
    }
    # Persist the histogram and the per-task pass counts for later analysis.
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(
        f"coverage={metrics.get('coverage')} mean_pass_count={metrics.get('mean_pass_count')} "
        f"zero={metrics.get('zero_pass_fraction')} saturated={metrics.get('saturated_fraction')} "
        f"estimated_pass_probability={metrics.get('estimated_pass_probability')}",
        flush=True,
    )
    print(f"Wrote {args.output}", flush=True)


if __name__ == "__main__":
    main()
