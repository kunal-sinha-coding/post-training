# This experiment compares one rejection-sampling batch with and without saved correct solutions.
# It uses the fixed eight original MBPP pilot tasks and reports timing and test results to W&B.

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any

# Add the repository root so this file can import the experiment helpers.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from experiments.incremental_rejection_sampling_sft import (
    generate_and_score,
    load_config,
    load_model,
    load_solution_store,
    load_training_tasks,
    task_fingerprint,
)


def score_cached_solutions(tasks: list[dict[str, Any]], store: dict[str, dict[str, Any]], config: dict[str, Any]) -> list[dict[str, Any]]:
    """Run each saved solution against its unchanged original task tests."""
    from experiments.rejection_sampling_sft import clean_completion
    from sandbox import score_completion_batch

    # Build one sandbox request for each valid task-to-solution cache hit.
    completions = [f"Code:\n```python\n{clean_completion(store[str(task['task_id'])]['solution'])}\n```" for task in tasks]
    tests = [str(task["test_code"]) for task in tasks]
    results = score_completion_batch(
        completions,
        tests,
        timeout_seconds=float(config["sandbox_timeout_seconds"]),
        reward_function="test_pass",
        reward_scoring_workers=int(config["reward_scoring_workers"]),
        visible_test_count=int(config["visible_test_count"]),
    )
    # Return the full-pass flag and test counts for cache-hit accounting.
    return [
        {"task_id": str(task["task_id"]), "passed_all": bool(details.get("total_tests", 0) > 0 and details.get("passed_tests") == details.get("total_tests")), **details}
        for task, (_, details) in zip(tasks, results)
    ]


def run(config_path: Path, output_dir: Path) -> dict[str, Any]:
    """Run one paired eight-task batch and log each phase to a dedicated W&B run."""
    import torch
    import wandb
    from dotenv import load_dotenv

    # Load experiment settings and keep the test limited to the original fixed pilot tasks.
    config = load_config(config_path)
    config["expected_train_samples"] = None
    task_ids = [str(value) for value in json.loads((Path(config["output_dir"]) / "pilot-task-ids.json").read_text(encoding="utf-8"))]
    tasks_by_id = {str(task["task_id"]): task for task in load_training_tasks(config)}
    tasks = [tasks_by_id[task_id] for task_id in task_ids]
    store_path = Path(config["solution_store_path"])
    store = load_solution_store(store_path)
    # Require an even cached and uncached split so both paths use the same task set.
    cached_tasks = [task for task in tasks if str(task["task_id"]) in store]
    uncached_tasks = [task for task in tasks if str(task["task_id"]) not in store]
    if len(cached_tasks) != 4 or len(uncached_tasks) != 4:
        raise ValueError(f"Expected four generated-cache hits and four misses, got {len(cached_tasks)} hits and {len(uncached_tasks)} misses.")
    # Reject a cache entry if its prompt or original tests differ from the selected task.
    for task in cached_tasks:
        record = store[str(task["task_id"])]
        if record.get("task_fingerprint") != task_fingerprint(task):
            raise ValueError(f"Generated cache fingerprint mismatch for task {task['task_id']}.")

    # Open a fresh, dedicated W&B run and immediately log a smoke-test point.
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    run_handle = wandb.init(
        project=str(config["wandb_project"]),
        entity=str(config["wandb_entity"]),
        name="mbpp-single-batch-generated-cache-check-20261011",
        job_type="rejection-sampling-single-batch-cache-test",
        config={
            "task_ids": task_ids,
            "cached_task_ids": [str(task["task_id"]) for task in cached_tasks],
            "uncached_task_ids": [str(task["task_id"]) for task in uncached_tasks],
            "samples_per_task": int(config["candidate_batch_size"]),
            "generated_solution_store": str(store_path),
            "model_name_or_path": str(config["model_name_or_path"]),
            "tests": "unchanged original MBPP assertions",
            "training": False,
        },
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"W&B run: {run_handle.url}", flush=True)
    run_handle.log({"rs/test_started": 1, "rs/wandb_logging_check": 1, "rs/cache_hit_tasks": len(cached_tasks), "rs/cache_miss_tasks": len(uncached_tasks)})

    # Load the configured base model once so model startup time does not enter either batch timing.
    model_started = time.perf_counter()
    model, tokenizer = load_model(config)
    tokenizer.padding_side = "left"
    model_load_seconds = time.perf_counter() - model_started
    run_handle.log({"rs/model_load_seconds": model_load_seconds})

    # Measure the cache-disabled baseline by generating one full candidate batch for all eight tasks.
    torch.cuda.synchronize()
    uncached_started = time.perf_counter()
    uncached_scores = generate_and_score(model, tokenizer, tasks, config, int(config["candidate_batch_size"]))
    torch.cuda.synchronize()
    uncached_seconds = time.perf_counter() - uncached_started
    uncached_passes = sum(bool(item["passed_all"]) for item in uncached_scores)
    run_handle.log({
        "rs/cache_disabled_elapsed_seconds": uncached_seconds,
        "rs/cache_disabled_generated_candidates": len(uncached_scores),
        "rs/cache_disabled_full_passes": uncached_passes,
        "rs/cache_disabled_candidate_pass_rate": uncached_passes / len(uncached_scores) if uncached_scores else 0.0,
        "rs/cache_disabled_tasks": len(tasks),
    })

    # Measure cache-enabled work by validating four saved solutions and generating only for four misses.
    torch.cuda.synchronize()
    cached_started = time.perf_counter()
    cached_results = score_cached_solutions(cached_tasks, store, config)
    miss_scores = generate_and_score(model, tokenizer, uncached_tasks, config, int(config["candidate_batch_size"]))
    torch.cuda.synchronize()
    cached_seconds = time.perf_counter() - cached_started
    cached_passes = sum(bool(item["passed_all"]) for item in cached_results) + sum(bool(item["passed_all"]) for item in miss_scores)
    cache_speedup = uncached_seconds / cached_seconds if cached_seconds else 0.0
    time_saved = uncached_seconds - cached_seconds
    cache_metrics = {
        "rs/cache_enabled_elapsed_seconds": cached_seconds,
        "rs/cache_enabled_generated_candidate_pass_rate": sum(bool(item["passed_all"]) for item in miss_scores) / len(miss_scores) if miss_scores else 0.0,
        "rs/cache_enabled_generated_candidates": len(miss_scores),
        "rs/cache_enabled_cache_hits": len(cached_results),
        "rs/cache_enabled_cache_hit_passes": sum(bool(item["passed_all"]) for item in cached_results),
        "rs/cache_enabled_full_passes": cached_passes,
        "rs/cache_enabled_tasks": len(tasks),
        "rs/cache_time_saved_seconds": time_saved,
        "rs/cache_speedup_ratio": cache_speedup,
        "rs/cache_time_saved_percent": 100.0 * time_saved / uncached_seconds if uncached_seconds else 0.0,
    }
    run_handle.log(cache_metrics)
    # Save the paired measurements and candidate outcomes for local audit.
    result = {
        "task_ids": task_ids,
        "cache_hit_task_ids": [str(task["task_id"]) for task in cached_tasks],
        "cache_miss_task_ids": [str(task["task_id"]) for task in uncached_tasks],
        "samples_per_task": int(config["candidate_batch_size"]),
        "model_load_seconds": model_load_seconds,
        "cache_disabled_elapsed_seconds": uncached_seconds,
        "cache_disabled_generated_candidates": len(uncached_scores),
        "cache_disabled_full_passes": uncached_passes,
        "cache_enabled_elapsed_seconds": cached_seconds,
        "cache_enabled_generated_candidates": len(miss_scores),
        "cache_enabled_full_passes": cached_passes,
        "cache_speedup_ratio": cache_speedup,
        "cache_time_saved_seconds": time_saved,
        "wandb_run_url": run_handle.url,
        "cache_disabled_candidates": uncached_scores,
        "cache_enabled_cache_hits": cached_results,
        "cache_enabled_miss_candidates": miss_scores,
    }
    result_path = output_dir / "single-batch-generated-cache-test.json"
    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    run_handle.summary.update(cache_metrics)
    run_handle.summary["rs/test_result_path"] = str(result_path)
    run_handle.finish()
    print(json.dumps({"wandb_run_url": result["wandb_run_url"], **cache_metrics}, indent=2), flush=True)
    return result


def main() -> None:
    """Parse paths and launch the single-batch cache comparison."""
    root = Path(__file__).resolve().parents[1]
    config_path = root / "configs/rejection-sampling-sft-incremental.yaml"
    output_dir = root / "outputs/rejection-sampling-sft-incremental-20261011"
    run(config_path, output_dir)


if __name__ == "__main__":
    # Run the bounded comparison when this file is called as a script.
    main()
