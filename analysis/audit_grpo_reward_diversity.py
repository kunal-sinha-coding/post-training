# This file audits a completed GRPO run without loading models or changing training.
# It reads step-indexed trainer history and greedy training and EvalPlus evaluations.
# It groups updates into fixed intervals and compares reward variation with metric changes.
# It saves a CSV table, provenance, correlations, and a figure for reproduction.

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr
import yaml


def load_json(path: Path, provenance: dict[str, str]) -> dict:
    """Read one source artifact and record its content hash."""
    # Hash the exact bytes used in the analysis.
    raw = path.read_bytes()
    provenance[str(path)] = hashlib.sha256(raw).hexdigest()
    return json.loads(raw)


def endpoint(root: Path, step: int, provenance: dict[str, str]) -> dict[str, float]:
    """Read greedy training and canonical benchmark metrics for one checkpoint."""
    # Read training metrics and count benchmark results from the canonical task records.
    train = load_json(root / f"training-step-{step}-metrics.json", provenance)
    evaluation = load_json(root / "evalplus" / f"step-{step}" / "mbpp" / "qwen2_chat_temp_0.0" / "eval_results.json", provenance)["eval"]
    results = [samples[0] for samples in evaluation.values()]
    assert all(len(samples) == 1 for samples in evaluation.values())
    return {
        "train_dense_reward": train["average_reward"],
        "train_pass_at_1": train["pass_at_1"],
        "evalplus_mbpp_pass_at_1": sum(row["base_status"] == "pass" for row in results) / len(results),
        "evalplus_mbpp_plus_pass_at_1": sum(row["base_status"] == row["plus_status"] == "pass" for row in results) / len(results),
    }


def correlations(rows: list[dict]) -> dict:
    """Compare interval diversity with contemporaneous and subsequent metric changes."""
    # Compute descriptive correlations without treating intervals as independent experiments.
    output = {}
    steps = np.asarray([row["end_step"] for row in rows], dtype=float)
    design = np.column_stack([np.ones(len(rows)), steps])
    for predictor in ["mixed_group_fraction", "mean_within_task_reward_std"]:
        x = np.asarray([row[predictor] for row in rows])
        for metric in ["delta_train_dense_reward", "delta_train_reconstructed_hybrid_reward", "delta_train_pass_at_1", "delta_evalplus_mbpp_pass_at_1"]:
            y = np.asarray([row[metric] for row in rows])
            # Remove a linear step trend for an additional sensitivity check.
            residual_x = x - design @ np.linalg.lstsq(design, x, rcond=None)[0]
            residual_y = y - design @ np.linalg.lstsq(design, y, rcond=None)[0]
            output[f"{predictor} versus {metric}"] = {
                "intervals": len(rows),
                "pearson": float(np.corrcoef(x, y)[0, 1]),
                "spearman": float(spearmanr(x, y).statistic),
                "pearson_after_linear_step_adjustment": float(np.corrcoef(residual_x, residual_y)[0, 1]),
                "pearson_predicting_next_interval": float(np.corrcoef(x[:-1], y[1:])[0, 1]),
            }
    return output


def plot(rows: list[dict], path: Path) -> None:
    """Save the progression of reward diversity and measured performance."""
    # Use a standalone plotting backend for a reproducible image.
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    steps = [row["end_step"] for row in rows]
    figure, axes = plt.subplots(3, 1, figsize=(10, 10), sharex=True, constrained_layout=True)
    axes[0].plot(steps, [100 * row["mixed_group_fraction"] for row in rows], marker="o")
    axes[0].set_ylabel("Varied task groups (%)")
    axes[0].set_title("Original MBPP GRPO: reward diversity and performance")
    # Show checkpoint metrics separately from stochastic rollout rewards.
    for key, label in [("train_pass_at_1", "Training pass@1"), ("evalplus_mbpp_pass_at_1", "EvalPlus MBPP pass@1")]:
        axes[1].plot(steps, [100 * row[key] for row in rows], marker="o", label=label)
        axes[2].plot(steps, [100 * row[f"delta_{key}"] for row in rows], marker="o", label=label)
    axes[1].set_ylabel("Checkpoint pass@1 (%)")
    axes[2].set_ylabel("Gain per interval (pp)")
    axes[2].set_xlabel("Optimizer steps")
    axes[2].axhline(0, color="black", linewidth=0.8)
    # Add labels and grids before writing the figure.
    for axis in axes:
        axis.grid(alpha=0.25)
    axes[1].legend()
    axes[2].legend()
    figure.savefig(path, dpi=160)
    plt.close(figure)


def main() -> None:
    """Build and save the complete audit from existing experiment artifacts."""
    # Select the source run and interval without affecting any live training process.
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--checkpoint-step", type=int, default=1300)
    parser.add_argument("--interval", type=int, default=100)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    provenance = {}
    raw_config = args.config.read_bytes()
    provenance[str(args.config)] = hashlib.sha256(raw_config).hexdigest()
    config = yaml.safe_load(raw_config)
    state_path = args.run_dir / f"checkpoint-{args.checkpoint_step}" / "trainer_state.json"
    state = load_json(state_path, provenance)
    history = {int(row["step"]): row for row in state["log_history"]}
    assert len(history) == len(state["log_history"])
    assert sorted(history) == list(range(1, args.checkpoint_step + 1))
    tasks_per_step = int(config["generation_batch_size"]) // int(config["num_generations"])
    coefficient = float(config["reward_coefficient"])
    rows = []
    previous = endpoint(args.run_dir, 0, provenance)
    previous["train_reconstructed_hybrid_reward"] = coefficient * previous["train_pass_at_1"] + (1 - coefficient) * previous["train_dense_reward"]
    # Aggregate logged task variation and compute changes between checkpoint endpoints.
    for end in range(args.interval, args.checkpoint_step + 1, args.interval):
        start = end - args.interval + 1
        window = [history[step] for step in range(start, end + 1)]
        varied_counts = [(1 - row["frac_reward_zero_std"]) * tasks_per_step for row in window]
        assert all(abs(count - round(count)) < 1e-5 for count in varied_counts)
        row = {
            "start_step": start,
            "end_step": end,
            "task_group_occurrences": len(window) * tasks_per_step,
            "mixed_groups": sum(round(count) for count in varied_counts),
            "mixed_group_fraction": float(np.mean([1 - entry["frac_reward_zero_std"] for entry in window])),
            "flat_group_fraction": float(np.mean([entry["frac_reward_zero_std"] for entry in window])),
            "mean_within_task_reward_std": float(np.mean([entry["reward_std"] for entry in window])),
            "mean_rollout_hybrid_reward": float(np.mean([entry["reward"] for entry in window])),
        }
        row["delta_mean_rollout_hybrid_reward"] = row["mean_rollout_hybrid_reward"] - rows[-1]["mean_rollout_hybrid_reward"] if rows else None
        current = endpoint(args.run_dir, end, provenance)
        current["train_reconstructed_hybrid_reward"] = coefficient * current["train_pass_at_1"] + (1 - coefficient) * current["train_dense_reward"]
        # Keep recorded dense reward distinct from reconstructed hybrid reward.
        for key, value in current.items():
            row[key] = value
            row[f"delta_{key}"] = value - previous[key]
        rows.append(row)
        previous = current
    args.output_dir.mkdir(parents=True, exist_ok=True)
    # Save full numerical results and explicit source definitions.
    with (args.output_dir / "intervals.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    report = {
        "source_run": str(args.run_dir),
        "interval_steps": args.interval,
        "tasks_per_optimizer_step": tasks_per_step,
        "candidates_per_task": config["num_generations"],
        "baseline": endpoint(args.run_dir, 0, provenance),
        "rows": rows,
        "correlations": correlations(rows),
        "source_sha256": provenance,
        "method": "Use step-indexed Trainer history; varied fraction is 1 minus frac_reward_zero_std. Greedy training reward is dense test-pass fraction. Hybrid greedy reward is reconstructed from full-pass fraction and dense reward. Deltas compare checkpoint endpoints; rollout mean deltas compare adjacent interval means.",
        "selection": "All 1300 recorded optimizer steps and every 100-step checkpoint endpoint, without outcome selection or task candidate selection.",
        "limitations": "13 serially dependent intervals from one run. Correlation is not causation. Time and task mastery confound both diversity and improvement. Reward normalization means nonzero standard deviation magnitude is not a direct measure of gradient strength. The unindexed candidate trace has1320 calls and cannot be mapped to steps by ordinal position alone.",
    }
    (args.output_dir / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    plot(rows, args.output_dir / "progression.png")
    # Print the requested compact interval table with percentage-point changes.
    print("Steps | Varied groups % | Rollout reward | Training reward delta | Train pass@1 delta pp | MBPP pass@1 delta pp")
    for row in rows:
        print(f"{row['start_step']}-{row['end_step']} | {100*row['mixed_group_fraction']:.2f} | {row['mean_rollout_hybrid_reward']:.4f} | {row['delta_train_dense_reward']:+.4f} | {100*row['delta_train_pass_at_1']:+.2f} | {100*row['delta_evalplus_mbpp_pass_at_1']:+.2f}")
    print(json.dumps(report["correlations"], indent=2))


if __name__ == "__main__":
    # Run the read-only audit when invoked as a command.
    main()
