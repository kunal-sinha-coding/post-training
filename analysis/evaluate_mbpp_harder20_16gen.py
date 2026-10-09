"""Sample and score sixteen Qwen completions for the first twenty harder tasks.

The script loads the ordered synthetic task file, builds the repository's Qwen
EvalPlus prompts, samples sixteen completions per task, scores each completion
against its saved assertions, and writes task-level group outcomes and metrics.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import math
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["HF_HOME"] = "/tmp/mbpp-qwen05-hf-home"
os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "0"

from data import build_qwen_evalplus_prompt
from experiments.run_qwen_official_greedy_eval import QWEN_EVALPLUS_STOP_STRINGS, apply_stops, build_prompt
from sandbox import score_completion_batch, wrap_qwen_continuation


MODEL = "Qwen/Qwen2.5-Coder-0.5B-Instruct"


def load_tasks(path: Path, task_count: int) -> list[dict[str, Any]]:
    """Load the first requested task rows in their saved order."""
    # Keep the dataset order so this preview always uses the same first twenty tasks.
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()][:task_count]


def build_task_prompt(task: dict[str, Any], visible_test_count: int) -> str:
    """Build a task prompt with the requested number of visible assertions."""
    # Reuse the prior task-only prompt when no assertions are requested.
    if visible_test_count == 0:
        # Use the saved reference header to preserve the exact function contract.
        function = ast.parse(task["reference_solution"]).body[0]
        signature = ast.unparse(function).splitlines()[0]
        return build_prompt(f"{task['task_text'].strip()}\n\nImplement this function:\n{signature}")
    # Match the original MBPP training prompt, which exposes the first assertions in its code docstring.
    record = {
        "task_id": task["prompt_id"],
        "text": task["task_text"],
        "code": task["reference_solution"],
        "test_list": task["tests"],
        "test_setup_code": "",
    }
    return build_qwen_evalplus_prompt(record, visible_test_count=visible_test_count)


def generate_samples(prompts: list[str], samples_per_task: int, seed: int) -> list[list[str]]:
    """Generate repeated temperature samples with the base Qwen model."""
    # Import vLLM only when generation starts so task inspection stays lightweight.
    from vllm import LLM, SamplingParams

    # Match the repository's established repeated-sampling settings.
    sampling = SamplingParams(
        n=samples_per_task,
        temperature=1.0,
        top_p=1.0,
        max_tokens=2048,
        seed=seed,
        stop=list(QWEN_EVALPLUS_STOP_STRINGS),
    )
    # Load the same base model and runtime settings as the greedy preview.
    llm = LLM(model=MODEL, dtype="bfloat16", tensor_parallel_size=1, gpu_memory_utilization=0.90, max_model_len=4096, enforce_eager=True)
    outputs = llm.generate(prompts, sampling, use_tqdm=True)
    # Apply the official stopping strings before sandbox scoring.
    return [[apply_stops(output.text) for output in result.outputs] for result in outputs]


def evaluate(tasks: list[dict[str, Any]], generations: list[list[str]], timeout_seconds: float, seed: int, visible_test_count: int) -> dict[str, Any]:
    """Score all completions and classify each task by full-pass outcomes."""
    # Score every completion against all saved assertions in the isolated sandbox.
    task_rows = []
    flat_rows = []
    for task, candidates in zip(tasks, generations, strict=True):
        candidate_rows = []
        test_code = "\n".join(task["tests"])
        # Score this task's independent generations concurrently with the training reward.
        scored = score_completion_batch(
            [wrap_qwen_continuation(completion) for completion in candidates],
            [test_code] * len(candidates),
            timeout_seconds=timeout_seconds,
            reward_function="hybrid",
            reward_coefficient=0.75,
            reward_scoring_workers=8,
        )
        for candidate_index, (completion, (reward, metrics)) in enumerate(zip(candidates, scored, strict=True)):
            row = {
                "candidate": candidate_index,
                "completion": completion,
                "completion_sha256": hashlib.sha256(completion.encode()).hexdigest(),
                "expected_tests": len(task["tests"]),
                "training_reward": reward,
                **metrics,
            }
            candidate_rows.append(row)
            flat_rows.append(row)
        # Label groups by the number of completions that pass every saved assertion.
        pass_count = sum(row["status"] == "passed" for row in candidate_rows)
        group = "none" if pass_count == 0 else "all" if pass_count == len(candidate_rows) else "mixed"
        rewards = [row["training_reward"] for row in candidate_rows]
        reward_mean = sum(rewards) / len(rewards)
        reward_std = math.sqrt(sum((reward - reward_mean) ** 2 for reward in rewards) / len(rewards))
        task_rows.append({
            "prompt_id": task["prompt_id"],
            "category": task["category"],
            "entry_point": task["entry_point"],
            "full_pass_count": pass_count,
            "group_outcome": group,
            "mean_test_fraction": sum(row["passed_tests"] / row["expected_tests"] for row in candidate_rows) / len(candidate_rows),
            "mean_training_reward": reward_mean,
            "training_reward_std": reward_std,
            "flat_training_reward": reward_std == 0.0,
            "zero_test_count": sum(row["passed_tests"] == 0 for row in candidate_rows),
            "unique_completion_count": len({row["completion_sha256"] for row in candidate_rows}),
            "generations": candidate_rows,
        })
    # Summarize task groups and all 960 expected assertion outcomes.
    group_counts = {name: sum(row["group_outcome"] == name for row in task_rows) for name in ("none", "all", "mixed")}
    assertion_total = sum(row["expected_tests"] for row in flat_rows)
    assertion_passed = sum(row["passed_tests"] for row in flat_rows)
    full_passes = sum(row["status"] == "passed" for row in flat_rows)
    return {
        "model": MODEL,
        "checkpoint": "base model, no fine-tuned checkpoint or adapter",
        "sampling": {"samples_per_task": len(generations[0]) if generations else 0, "temperature": 1.0, "top_p": 1.0, "seed": seed, "max_tokens": 2048},
        "visible_test_count": visible_test_count,
        "prompt_protocol": "original MBPP Qwen EvalPlus prompt with visible assertions" if visible_test_count else "task text and reference signature only",
        "reward": {"function": "hybrid", "coefficient": 0.75, "formula": "0.75 * full_pass + 0.25 * passed_test_fraction", "scoring_workers": 8},
        "task_selection": "first twenty rows, in file order, from mbpp_category_synthetic_tasks_harder100.jsonl",
        "task_count": len(task_rows),
        "group_outcomes": {name: {"tasks": count, "fraction": count / len(task_rows) if task_rows else 0.0} for name, count in group_counts.items()},
        "full_pass_completions": full_passes,
        "completion_count": len(flat_rows),
        "full_pass_fraction": full_passes / len(flat_rows) if flat_rows else 0.0,
        "assertions_passed": assertion_passed,
        "assertion_count": assertion_total,
        "assertion_pass_fraction": assertion_passed / assertion_total if assertion_total else 0.0,
        "mean_task_test_fraction": sum(row["mean_test_fraction"] for row in task_rows) / len(task_rows) if task_rows else 0.0,
        "mixed_reward_group_fraction": sum(not row["flat_training_reward"] for row in task_rows) / len(task_rows) if task_rows else 0.0,
        "flat_reward_groups": sum(row["flat_training_reward"] for row in task_rows),
        "mean_training_reward_group_std": sum(row["training_reward_std"] for row in task_rows) / len(task_rows) if task_rows else 0.0,
        "tasks": task_rows,
    }


def main() -> None:
    """Run sampling, sandbox scoring, and save the full evaluation record."""
    # Parse reproducible input, output, sample count, seed, and timeout settings.
    parser = argparse.ArgumentParser(description="Sample sixteen completions on the first twenty harder synthetic MBPP tasks.")
    parser.add_argument("--tasks", type=Path, default=ROOT / "analysis" / "mbpp_category_synthetic_tasks_harder100.jsonl")
    parser.add_argument("--output", type=Path, default=ROOT / "analysis" / "mbpp_category_synthetic_harder20_16gen_eval.json")
    parser.add_argument("--task-count", type=int, default=20)
    parser.add_argument("--samples-per-task", type=int, default=16)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--visible-test-count", type=int, default=0)
    parser.add_argument("--timeout-seconds", type=float, default=3.0)
    args = parser.parse_args()
    tasks = load_tasks(args.tasks, args.task_count)
    prompts = [build_task_prompt(task, args.visible_test_count) for task in tasks]
    generations = generate_samples(prompts, args.samples_per_task, args.seed)
    result = evaluate(tasks, generations, args.timeout_seconds, args.seed, args.visible_test_count)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in result.items() if key != "tasks"}, indent=2), flush=True)


if __name__ == "__main__":
    # Start the requested evaluation from the command line.
    main()
