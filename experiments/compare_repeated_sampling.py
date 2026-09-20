# This script selects fixed MBPP training tasks, samples both models with identical settings, scores every completion, and writes paired diversity metrics.

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import random
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any

import torch
import yaml

from data import prepare_datasets
from experiments.run_qwen_official_greedy_eval import QWEN_EVALPLUS_STOP_STRINGS, apply_stops, merge_adapter
from sandbox import score_completion, wrap_qwen_continuation


def select_tasks(config: dict[str, Any], task_count: int, seed: int) -> list[dict[str, Any]]:
    """Select a reproducible subset of disjoint MBPP training tasks."""
    # Load the complete training partition before applying the fixed random selection.
    train_dataset, _ = prepare_datasets(config)
    indices = random.Random(seed).sample(range(len(train_dataset)), task_count)
    return [train_dataset[index] for index in indices]


def generate_samples(model_name: str, prompts: list[str], samples_per_task: int, seed: int) -> list[list[str]]:
    """Generate repeated temperature samples for every prompt with vLLM."""
    # Import vLLM inside the generation function so scoring and task selection remain lightweight.
    from vllm import LLM, SamplingParams

    # Request all repeated samples in one prompt batch so every model uses the same rollout geometry.
    sampling = SamplingParams(
        n=samples_per_task,
        temperature=1.0,
        top_p=1.0,
        max_tokens=2048,
        seed=seed,
        stop=list(QWEN_EVALPLUS_STOP_STRINGS),
    )
    # Load one model at a time so the base and merged adapter fit on the available GPU.
    llm = LLM(model=model_name, dtype="bfloat16", tensor_parallel_size=1, gpu_memory_utilization=0.90, max_model_len=4096, enforce_eager=True)
    outputs = llm.generate(prompts, sampling, use_tqdm=True)
    # Extract the same stopped Python continuations used by the official evaluation wrapper.
    generations = [[apply_stops(output.text) for output in result.outputs] for result in outputs]
    # Release the vLLM engine before loading the comparison model.
    del llm
    gc.collect()
    torch.cuda.empty_cache()
    return generations


def score_samples(records: list[dict[str, Any]], generations: list[list[str]], name: str) -> dict[str, Any]:
    """Score every sampled completion and summarize task-level reward diversity."""
    # Score each completion against only the original MBPP tests used by GRPO.
    task_results = []
    all_results = []
    for record, candidates in zip(records, generations, strict=True):
        scored = []
        for candidate_index, raw_completion in enumerate(candidates):
            reward, detail = score_completion(
                wrap_qwen_continuation(raw_completion),
                record["test_code"],
                timeout_seconds=3.0,
                reward_function="hybrid",
                reward_coefficient=0.5,
            )
            row = {
                "candidate": candidate_index,
                "reward": reward,
                "passed_tests": detail["passed_tests"],
                "total_tests": detail["total_tests"],
                "status": detail["status"],
                "completion_sha256": hashlib.sha256(raw_completion.encode()).hexdigest(),
            }
            scored.append(row)
            all_results.append(row)
        # Summarize whether repeated completions provide distinct reward and code signals for this task.
        rewards = [row["reward"] for row in scored]
        test_fractions = [row["passed_tests"] / row["total_tests"] if row["total_tests"] else 0.0 for row in scored]
        full_passes = [row["status"] == "passed" for row in scored]
        task_results.append({
            "task_id": str(record["task_id"]),
            "mean_reward": sum(rewards) / len(rewards),
            "mean_test_fraction": sum(test_fractions) / len(test_fractions),
            "full_pass_fraction": sum(full_passes) / len(full_passes),
            "zero_test_fraction": sum(row["passed_tests"] == 0 for row in scored) / len(scored),
            "flat_reward": len(set(rewards)) == 1,
            "flat_test_fraction": len(set(test_fractions)) == 1,
            "unique_completion_fraction": len({row["completion_sha256"] for row in scored}) / len(scored),
            "full_pass_count": sum(full_passes),
            "statuses": dict(Counter(row["status"] for row in scored)),
            "candidates": scored,
        })
    # Aggregate completion and group metrics for the model comparison.
    completion_count = len(all_results)
    return {
        "model": name,
        "tasks": len(task_results),
        "samples_per_task": len(generations[0]) if generations else 0,
        "completions": completion_count,
        "mean_reward": sum(row["reward"] for row in all_results) / completion_count,
        "mean_test_fraction": sum(row["passed_tests"] / row["total_tests"] if row["total_tests"] else 0.0 for row in all_results) / completion_count,
        "full_pass_fraction": sum(row["status"] == "passed" for row in all_results) / completion_count,
        "zero_test_fraction": sum(row["passed_tests"] == 0 for row in all_results) / completion_count,
        "flat_reward_group_fraction": sum(row["flat_reward"] for row in task_results) / len(task_results),
        "flat_test_fraction_group_fraction": sum(row["flat_test_fraction"] for row in task_results) / len(task_results),
        "mean_unique_completion_fraction": sum(row["unique_completion_fraction"] for row in task_results) / len(task_results),
        "full_pass_count_histogram": dict(Counter(row["full_pass_count"] for row in task_results)),
        "task_results": task_results,
    }


def main() -> None:
    """Run the paired base and adapter sampling experiment."""
    # Parse the fixed comparison settings from the command line.
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--task-count", type=int, default=32)
    parser.add_argument("--samples-per-task", type=int, default=16)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--adapter", type=Path, default=Path("outputs/grpo-mbpp-canonical-split-hybrid-lr3e6/best_checkpoints/step-50"))
    parser.add_argument("--base", default="Qwen/Qwen2.5-Coder-3B-Instruct")
    args = parser.parse_args()
    # Load the canonical fixed training subset and construct identical prompts for both models.
    config = yaml.safe_load(Path("configs/default.yaml").read_text(encoding="utf-8"))
    records = select_tasks(config, args.task_count, args.seed)
    prompts = [record["prompt"] for record in records]
    # Generate and score the base model samples first.
    print("Generating base model samples.", flush=True)
    base_generations = generate_samples(args.base, prompts, args.samples_per_task, args.seed)
    base_results = score_samples(records, base_generations, "base")
    # Merge the saved adapter into a temporary checkpoint before generating its paired samples.
    print("Generating adapter samples.", flush=True)
    with tempfile.TemporaryDirectory(prefix="grpo-repeated-") as temporary_directory:
        merged_path = merge_adapter(str(args.adapter), Path(temporary_directory) / "merged")
        adapter_generations = generate_samples(str(merged_path), prompts, args.samples_per_task, args.seed)
    adapter_results = score_samples(records, adapter_generations, "step-50")
    # Persist the complete paired metrics and per-task results for later review.
    result = {
        "experiment": "repeated-sampling-base-vs-step50",
        "seed": args.seed,
        "task_ids": [str(record["task_id"]) for record in records],
        "sampling": {"temperature": 1.0, "top_p": 1.0, "max_tokens": 2048, "samples_per_task": args.samples_per_task, "stop_strings": list(QWEN_EVALPLUS_STOP_STRINGS)},
        "base_model": args.base,
        "adapter": str(args.adapter),
        "base_results": base_results,
        "adapter_results": adapter_results,
    }
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    # Print the paired aggregate metrics for quick experiment monitoring.
    for key in ("mean_reward", "mean_test_fraction", "full_pass_fraction", "zero_test_fraction", "flat_reward_group_fraction", "flat_test_fraction_group_fraction", "mean_unique_completion_fraction"):
        delta = adapter_results[key] - base_results[key]
        print(f"{key}: base={base_results[key]:.6f} adapter={adapter_results[key]:.6f} delta={delta:+.6f}", flush=True)
    print(f"Saved {args.output}", flush=True)


if __name__ == "__main__":
    main()
