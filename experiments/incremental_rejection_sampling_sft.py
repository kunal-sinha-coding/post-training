# This experiment loads original and harder MBPP tasks, samples candidates in fixed batches, and stores one passing solution per task in an append-only JSON map.
# It runs an eight-task pilot until greedy pass@1 reaches adaptive pass@20 coverage, then collects full-data solutions and trains a separate LoRA model with resumable checkpoints.

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import secrets
import sys
import string
import time
from pathlib import Path
from typing import Any

# Add the repository root so direct execution can import the shared training code.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def load_config(path: Path) -> dict[str, Any]:
    """Load the dedicated rejection-sampling YAML configuration."""
    import yaml

    # Parse the YAML file and reject an empty configuration.
    with path.open(encoding="utf-8") as handle:
        config = yaml.safe_load(handle) or {}
    if not isinstance(config, dict):
        raise ValueError(f"Expected a YAML mapping in {path}.")
    return config


def load_training_tasks(config: dict[str, Any]) -> list[dict[str, Any]]:
    """Load the configured task pool from cached MBPP Arrow files and the synthetic artifact."""
    from datasets import Dataset
    from datasets.config import HF_DATASETS_CACHE
    from data import _normalize_task_text, _task_description_from_prompt, load_generated_training_tasks, normalize_record

    # Read the valid local Arrow splits because a separate cached Hub Parquet file is empty.
    cache_root = Path(HF_DATASETS_CACHE)
    split_names = config.get("mbpp_splits", ["train", "validation", "test"])
    tasks = []
    for split in split_names:
        matches = sorted(cache_root.glob(f"google-research-datasets___mbpp/full/0.0.0/*/mbpp-{split}.arrow"))
        if not matches:
            raise FileNotFoundError(f"No cached MBPP Arrow file exists for split {split!r} under {cache_root}.")
        raw_dataset = Dataset.from_file(str(matches[0]))
        # Normalize every original row with the same prompt and visible-test logic as training.
        tasks.extend(normalize_record(dict(row), bool(config.get("include_generic_arguments", False)), config.get("visible_test_count")) for row in raw_dataset)
    synthetic_path = config.get("synthetic_training_tasks_path")
    if synthetic_path:
        synthetic_tasks = load_generated_training_tasks(synthetic_path, bool(config.get("include_generic_arguments", False)), config.get("visible_test_count"))
        tasks.extend(dict(synthetic_tasks[index]) for index in range(len(synthetic_tasks)))
    # Apply the canonical EvalPlus ID and task-text exclusion to both data sources.
    from evalplus.data import get_mbpp_plus

    evalplus_records = get_mbpp_plus()
    evalplus_ids = {str(int(task_id.split("/")[-1])) for task_id in evalplus_records}
    evalplus_texts = {
        normalized
        for record in evalplus_records.values()
        if (normalized := _normalize_task_text(_task_description_from_prompt(record.get("prompt", ""))))
    }
    tasks = [task for task in tasks if str(task["task_id"]) not in evalplus_ids and _normalize_task_text(task.get("task_text", "")) not in evalplus_texts]
    allowed_ids = config.get("train_task_ids")
    if allowed_ids is not None:
        allowed = {str(task_id) for task_id in allowed_ids}
        tasks = [task for task in tasks if str(task["task_id"]) in allowed]
    max_train = config.get("max_train_samples")
    if max_train:
        tasks = tasks[:int(max_train)]
    if config.get("synthetic_tests_enabled", False):
        from data import add_synthetic_tests, load_synthetic_tests

        test_map = load_synthetic_tests(config["synthetic_tests_path"], int(config.get("synthetic_tests_per_task", 20)), float(config.get("synthetic_tests_validation_timeout_seconds", 5)))
        tasks = add_synthetic_tests(tasks, test_map, bool(config.get("synthetic_tests_require_all", True)))
    # Enforce the expected full-pool size before any pilot sampling begins.
    expected = config.get("expected_train_samples")
    if expected is not None and len(tasks) != int(expected):
        raise ValueError(f"Expected {expected} training tasks, but loaded {len(tasks)}.")
    if not tasks:
        raise ValueError("The configured training dataset is empty.")
    return tasks


def start_wandb(config: dict[str, Any], phase: str, output_dir: Path) -> Any | None:
    """Start or resume one named W&B run for the current experiment phase."""
    if config.get("report_to") != "wandb":
        return None
    from dotenv import load_dotenv
    import wandb

    # Load the local API key without printing or copying it into the experiment records.
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    if not os.getenv("WANDB_API_KEY"):
        raise RuntimeError("W&B logging is enabled, but WANDB_API_KEY is not available.")
    # Reuse a stable phase run ID so a supervisor restart resumes the same W&B history.
    run_id_path = output_dir / f"{phase}-wandb-run-id.json"
    if run_id_path.exists():
        run_id = str(json.loads(run_id_path.read_text(encoding="utf-8"))["run_id"])
    else:
        run_id = "".join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(8))
        write_json(run_id_path, {"run_id": run_id})
    run = wandb.init(
        project=str(config["wandb_project"]),
        entity=str(config["wandb_entity"]),
        name=str(config[f"wandb_{phase.replace('-', '_')}_run_name"]),
        id=run_id,
        resume="allow",
        job_type=f"incremental-rejection-sampling-{phase}",
        config={key: value for key, value in config.items() if not key.endswith("_run_name")},
    )
    print(f"W&B run: {run.url}", flush=True)
    return run


def task_fingerprint(task: dict[str, Any]) -> str:
    """Hash the exact prompt and tests that define one task identity."""
    # Bind a saved solution to both the prompt and the complete test program.
    payload = json.dumps([task["prompt"], task["test_code"]], ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def load_solution_store(path: Path) -> dict[str, dict[str, Any]]:
    """Load the persistent task-to-solution map without modifying it."""
    # Treat a missing store as an empty map and validate every stored record.
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as handle:
        store = json.load(handle)
    if not isinstance(store, dict) or not all(isinstance(value, dict) for value in store.values()):
        raise ValueError(f"The solution store is not a task-to-record JSON map: {path}.")
    return store


def save_solution_store(path: Path, store: dict[str, dict[str, Any]], previous_keys: set[str]) -> None:
    """Atomically save new solutions while proving that no prior key was removed."""
    import fcntl

    # Keep a permanent lock file so concurrent experiment processes cannot lose updates.
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_suffix(path.suffix + ".lock")
    with lock_path.open("a", encoding="utf-8") as lock_handle:
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)
        current = load_solution_store(path)
        if not previous_keys.issubset(current.keys() | store.keys()):
            raise RuntimeError("The solution store update would remove a prior task key.")
        # Preserve any entries added by another writer after this process loaded the map.
        current.update({key: value for key, value in store.items() if key not in current})
        temporary_path = path.with_name(f"{path.name}.tmp-{os.getpid()}")
        with temporary_path.open("w", encoding="utf-8") as output_handle:
            json.dump(current, output_handle, ensure_ascii=False, indent=2, sort_keys=True)
            output_handle.write("\n")
            output_handle.flush()
            os.fsync(output_handle.fileno())
        os.replace(temporary_path, path)
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)


def write_json(path: Path, value: Any) -> None:
    """Write one replaceable experiment-state file atomically."""
    # Use a same-directory temporary file so a restart never reads a partial state file.
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_name(f"{path.name}.tmp-{os.getpid()}")
    with temporary_path.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary_path, path)


def append_jsonl(path: Path, value: dict[str, Any]) -> None:
    """Append one timestamped JSON record to an experiment trace."""
    # Keep cycle and training metrics in append-only local logs.
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), **value}, ensure_ascii=False) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def load_model(config: dict[str, Any]) -> tuple[Any, Any]:
    """Load the configured base model and attach the pilot's LoRA adapter."""
    import torch
    from peft import LoraConfig, get_peft_model
    from transformers import AutoModelForCausalLM, AutoTokenizer

    # Load the configured base model from the local cache without resolving a training checkpoint.
    model_path = str(config["model_name_or_path"])
    tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=False, local_files_only=True)
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    dtype = torch.bfloat16 if bool(config.get("bf16", True)) else torch.float16
    model = AutoModelForCausalLM.from_pretrained(model_path, torch_dtype=dtype, device_map=str(config.get("device", "cuda")), trust_remote_code=False, local_files_only=True)
    # Apply only the separately configured LoRA adapter to the base model.
    model = get_peft_model(model, LoraConfig(
        task_type="CAUSAL_LM",
        r=int(config["lora_r"]),
        lora_alpha=int(config["lora_alpha"]),
        lora_dropout=float(config["lora_dropout"]),
        target_modules=list(config["lora_target_modules"]),
    ))
    tokenizer.padding_side = "left"
    model.eval()
    return model, tokenizer


def generate_and_score(model: Any, tokenizer: Any, tasks: list[dict[str, Any]], config: dict[str, Any], sample_count: int) -> list[dict[str, Any]]:
    """Generate a bounded candidate batch for each task and execute all original assertions."""
    from experiments.rejection_sampling_sft import clean_completion
    from experiments.rejection_sampling_sft_batch import generate_candidates
    from sandbox import score_completion_batch

    # Generate the configured number of candidates for each task in shared GPU batches.
    generated = generate_candidates(
        model,
        tokenizer,
        tasks,
        sample_count,
        int(config["generation_batch_size"]),
        int(config["max_new_tokens"]),
        float(config["temperature"]),
    )
    # Score each generated program against its unchanged task tests with bounded CPU concurrency.
    task_by_id = {str(task["task_id"]): task for task in tasks}
    completions = [f"Code:\n```python\n{clean_completion(item['completion'])}\n```" for item in generated]
    tests = [str(task_by_id[str(item["task_id"])]["test_code"]) for item in generated]
    scores = score_completion_batch(
        completions,
        tests,
        timeout_seconds=float(config["sandbox_timeout_seconds"]),
        reward_function="test_pass",
        reward_scoring_workers=int(config["reward_scoring_workers"]),
        visible_test_count=int(config["visible_test_count"]),
    )
    # Keep all task-level assertion details for the pilot and compact records for full collection.
    return [
        {
            **item,
            **details,
            "passed_all": bool(details.get("total_tests", 0) > 0 and details.get("passed_tests") == details.get("total_tests")),
        }
        for item, (_, details) in zip(generated, scores)
    ]


def accept_first_solutions(scored: list[dict[str, Any]], tasks_by_id: dict[str, dict[str, Any]], store_path: Path) -> int:
    """Add only the first fully passing completion for each task to the permanent solution map."""
    # Load the full store and remember its keys so the write can verify append-only behavior.
    store = load_solution_store(store_path)
    previous_keys = set(store)
    added = 0
    for item in scored:
        task_id = str(item["task_id"])
        task = tasks_by_id[task_id]
        fingerprint = task_fingerprint(task)
        existing = store.get(task_id)
        if existing is not None and existing.get("task_fingerprint") != fingerprint:
            raise ValueError(f"Stored solution task {task_id} has a different prompt or test fingerprint.")
        if item["passed_all"] and existing is None:
            store[task_id] = {
                "solution": item["completion"],
                "task_fingerprint": fingerprint,
                "model_name_or_path": str(task.get("model_name_or_path", "Qwen/Qwen2.5-Coder-0.5B-Instruct")),
                "selection": "first sampled candidate passing every unchanged task assertion",
                "passed_tests": int(item["passed_tests"]),
                "total_tests": int(item["total_tests"]),
                "sample_index": int(item["sample_index"]),
                "accepted_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
            added += 1
    if added:
        save_solution_store(store_path, store, previous_keys)
    return added


def build_sft_records(tasks: list[dict[str, Any]], store_path: Path) -> list[dict[str, Any]]:
    """Select stored passing solutions and place them in the shared SFT record schema."""
    # Include only tasks with a matching task fingerprint and a stored complete solution.
    store = load_solution_store(store_path)
    records = []
    for task in tasks:
        task_id = str(task["task_id"])
        saved = store.get(task_id)
        if saved is None:
            continue
        if saved.get("task_fingerprint") != task_fingerprint(task):
            raise ValueError(f"Stored solution task {task_id} has a different prompt or test fingerprint.")
        records.append({**task, "reference_code": str(saved["solution"])})
    return records


def train_one_epoch(model: Any, tokenizer: Any, tasks: list[dict[str, Any]], store_path: Path, config: dict[str, Any], output_dir: Path, cycle: int) -> float | None:
    """Train one response-only SFT epoch with the configured per-device batch size."""
    import torch
    from data import build_sft_dataset
    from transformers import DataCollatorForSeq2Seq, Trainer, TrainingArguments

    # Build training examples only from the persistent accepted-solution map.
    records = build_sft_records(tasks, store_path)
    if not records:
        return None
    sft_dataset = build_sft_dataset(records, tokenizer, config)
    # Disable checkpoint writes for the pilot and keep all cycle artifacts outside GRPO paths.
    training_args = TrainingArguments(
        output_dir=str(output_dir / f"pilot-cycle-{cycle}"),
        learning_rate=float(config["learning_rate"]),
        num_train_epochs=1,
        per_device_train_batch_size=int(config["sft_per_device_train_batch_size"]),
        gradient_accumulation_steps=int(config["gradient_accumulation_steps"]),
        logging_steps=1,
        save_strategy="no",
        report_to=[str(config["report_to"])],
        bf16=bool(config.get("bf16", True)) and torch.cuda.is_available(),
        fp16=bool(config.get("fp16", False)) and torch.cuda.is_available(),
        dataloader_num_workers=int(config["dataloader_num_workers"]),
        seed=int(config["seed"]),
        disable_tqdm=True,
        remove_unused_columns=False,
    )
    # Train on full-pass completions and return the mean loss for this epoch.
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=sft_dataset,
        data_collator=DataCollatorForSeq2Seq(tokenizer=tokenizer, model=model, padding=True),
    )
    result = trainer.train()
    model.eval()
    return float(result.training_loss)


def evaluate_greedy(model: Any, tokenizer: Any, tasks: list[dict[str, Any]], config: dict[str, Any]) -> dict[str, Any]:
    """Measure one deterministic pass@1 completion for every fixed evaluation task."""
    from experiments.rejection_sampling_sft import clean_completion
    from experiments.rejection_sampling_sft_batch import generate_candidates
    from sandbox import score_completion_batch

    # Generate one greedy completion per task without changing prompts or assertions.
    candidates = generate_candidates(model, tokenizer, tasks, 1, int(config["generation_batch_size"]), int(config["max_new_tokens"]), float(config["temperature"]), greedy=True)
    task_by_id = {str(task["task_id"]): task for task in tasks}
    completions = [f"Code:\n```python\n{clean_completion(item['completion'])}\n```" for item in candidates]
    tests = [str(task_by_id[str(item["task_id"])]["test_code"]) for item in candidates]
    scores = score_completion_batch(
        completions,
        tests,
        timeout_seconds=float(config["sandbox_timeout_seconds"]),
        reward_function="test_pass",
        reward_scoring_workers=int(config["reward_scoring_workers"]),
        visible_test_count=int(config["visible_test_count"]),
    )
    # Return the pass rate and the per-task details for the pilot report.
    rows = []
    for candidate, (_, details) in zip(candidates, scores):
        rows.append({**candidate, **details, "passed_all": bool(details.get("total_tests", 0) > 0 and details.get("passed_tests") == details.get("total_tests"))})
    passed = sum(row["passed_all"] for row in rows)
    return {"pass_count": passed, "task_count": len(rows), "pass_rate": passed / len(rows) if rows else 0.0, "details": rows}


def collect_round(tasks: list[dict[str, Any]], model: Any, tokenizer: Any, config: dict[str, Any], store_path: Path, state_path: Path, trace_path: Path, progress_callback: Any | None = None) -> dict[str, Any]:
    """Generate one configurable candidate batch for each unresolved task and persist progress."""
    # Load per-task generation counts and restrict work to tasks without a saved passing solution.
    state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {"attempts": {}}
    attempts = {str(key): int(value) for key, value in state.get("attempts", {}).items()}
    store = load_solution_store(store_path)
    max_tries = int(config["max_generation_batches_per_task"])
    cached_tasks = [task for task in tasks if str(task["task_id"]) in store]
    # Treat each requested sample for a cached task as the saved passing solution response.
    for task in cached_tasks:
        record = store[str(task["task_id"])]
        if record.get("task_fingerprint") != task_fingerprint(task):
            raise ValueError(f"Stored solution task {task['task_id']} has a different prompt or test fingerprint.")
    cached_candidate_total = len(cached_tasks) * int(config["candidate_batch_size"])
    active = [task for task in tasks if str(task["task_id"]) not in store and attempts.get(str(task["task_id"]), 0) < max_tries]
    added_total = generated_total = passed_total = 0
    chunk_size = int(config["collection_task_batch_size"])
    # Work through bounded task chunks so full-data candidate details stay within host memory.
    for chunk_start in range(0, len(active), chunk_size):
        chunk = active[chunk_start:chunk_start + chunk_size]
        for task in chunk:
            task_id = str(task["task_id"])
            attempts[task_id] = attempts.get(task_id, 0) + 1
        # Save attempt counts before generation so a restart cannot exceed the configured try limit.
        write_json(state_path, {"attempts": attempts, "max_generation_batches_per_task": max_tries})
        scored = generate_and_score(model, tokenizer, chunk, config, int(config["candidate_batch_size"]))
        generated_total += len(scored)
        passed_total += sum(item["passed_all"] for item in scored)
        added = accept_first_solutions(scored, {str(task["task_id"]): task for task in chunk}, store_path)
        added_total += added
        # Keep pilot failures auditable and full-data traces compact.
        if bool(config.get("save_candidate_details", False)):
            for item in scored:
                append_jsonl(trace_path, {key: value for key, value in item.items() if key != "completion" or bool(item["passed_all"])})
        else:
            append_jsonl(trace_path, {"tasks_in_chunk": len(chunk), "candidates": len(scored), "full_passes": sum(item["passed_all"] for item in scored), "new_solutions": added})
        print(f"collection progress: tasks {min(chunk_start + len(chunk), len(active))}/{len(active)}, new solutions {added_total}", flush=True)
        # Publish full-data progress as each bounded task chunk finishes.
        if progress_callback is not None:
            progress_callback({"tasks_processed": min(chunk_start + len(chunk), len(active)), "active_task_count": len(active), "chunk_candidates": len(scored), "chunk_full_passes": sum(item["passed_all"] for item in scored), "generated_candidates": generated_total, "full_passes": passed_total, "new_solutions": added_total})
    # Return actual generation counts and cache-equivalent candidate counts for this round.
    return {"active_tasks": len(active), "cached_tasks": len(cached_tasks), "cached_candidates": cached_candidate_total, "cached_full_passes": cached_candidate_total, "candidate_equivalents": generated_total + cached_candidate_total, "sample_passes_with_cache": passed_total + cached_candidate_total, "generated_candidates": generated_total, "full_passes": passed_total, "new_solutions": added_total, "attempts": attempts}


def run_pilot(config: dict[str, Any], output_dir: Path, solution_store_path: Path) -> None:
    """Train the fixed eight-task pilot until three consecutive epochs plateau."""
    import torch

    # Load the filtered data and keep one prompt-only random draw from original tasks.
    all_tasks = load_training_tasks(config)
    original_tasks = [task for task in all_tasks if not str(task["task_id"]).startswith("synthetic-")]
    if len(original_tasks) < 8:
        raise ValueError(f"The original task pool has only {len(original_tasks)} rows.")
    ids_path = output_dir / "pilot-task-ids.json"
    if ids_path.exists():
        pilot_ids = [str(value) for value in json.loads(ids_path.read_text(encoding="utf-8"))]
    else:
        pilot_ids = [str(task["task_id"]) for task in random.Random(int(config["seed"])).sample(original_tasks, 8)]
        write_json(ids_path, pilot_ids)
    tasks_by_id = {str(task["task_id"]): task for task in original_tasks}
    tasks = [tasks_by_id[task_id] for task_id in pilot_ids]
    # Start a dedicated W&B run for this eight-task plateau pilot.
    wandb_run = start_wandb(config, "pilot_ceiling", output_dir)
    # Load the configured base model and keep pilot checkpoints disabled.
    torch.set_num_threads(int(config["torch_num_threads"]))
    model, tokenizer = load_model(config)
    state_path = output_dir / "pilot-state.json"
    trace_path = output_dir / "pilot-candidates.jsonl"
    state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {"attempts": {}, "evaluations": [], "cycles_completed": 0}
    history = list(state.get("evaluations", []))
    plateau_window = int(config.get("pilot_plateau_evaluations", 3))
    plateau_tolerance = float(config.get("pilot_plateau_tolerance", 0.01))
    # Evaluate the loaded model and log the first pass-rate point.
    baseline = evaluate_greedy(model, tokenizer, tasks, config)
    append_jsonl(output_dir / "pilot-evaluations.jsonl", {"cycle": 0, "kind": "loaded_model_baseline", **baseline})
    if wandb_run is not None:
        wandb_run.log({"rs/greedy_pass_rate": baseline["pass_rate"], "rs/greedy_pass_at_1": baseline["pass_rate"], "rs/greedy_pass_count": baseline["pass_count"], "rs/task_count": baseline["task_count"], "rs/cycle": 0, "rs/sample_pass_rate_is_fresh": 0})
    cycle = 0
    max_tries = int(config["max_generation_batches_per_task"])
    last_sample_pass_rate = state.get("last_sample_pass_rate")
    epoch_pass_rates: list[float] = []
    # Sample unresolved tasks, train once, and log both requested rates after every epoch.
    while True:
        cycle += 1
        cycle_started = time.perf_counter()
        counts = collect_round(tasks, model, tokenizer, config, solution_store_path, state_path, trace_path)
        attempts = counts.pop("attempts")
        if counts["candidate_equivalents"]:
            last_sample_pass_rate = counts["sample_passes_with_cache"] / counts["candidate_equivalents"]
        loss = train_one_epoch(model, tokenizer, tasks, solution_store_path, config, output_dir / "pilot-no-checkpoints", cycle)
        evaluation = evaluate_greedy(model, tokenizer, tasks, config)
        epoch_pass_rates.append(evaluation["pass_rate"])
        store = load_solution_store(solution_store_path)
        solved_count = sum(str(task["task_id"]) in store for task in tasks)
        sampling_complete = all(str(task["task_id"]) in store or int(attempts.get(str(task["task_id"]), 0)) >= max_tries for task in tasks)
        ceiling = solved_count / len(tasks)
        plateau_rates = epoch_pass_rates[-plateau_window:]
        plateau_reached = len(plateau_rates) == plateau_window and max(plateau_rates) - min(plateau_rates) <= plateau_tolerance
        sample_is_fresh = bool(counts["generated_candidates"])
        record = {
            "cycle": cycle,
            **counts,
            "sample_pass_rate": last_sample_pass_rate,
            "sample_pass_rate_is_fresh": bool(counts["candidate_equivalents"]),
            "model_sampling_is_fresh": sample_is_fresh,
            "candidate_equivalents": counts["candidate_equivalents"],
            "cached_candidates": counts["cached_candidates"],
            "cached_tasks": counts["cached_tasks"],
            "model_generated_sample_pass_rate": counts["full_passes"] / counts["generated_candidates"] if counts["generated_candidates"] else None,
            "pass_at_20_ceiling": ceiling if sampling_complete else None,
            "sampling_complete": sampling_complete,
            "solution_coverage": solved_count / len(tasks),
            "sft_loss": loss,
            "greedy_pass_rate": evaluation["pass_rate"],
            "greedy_pass_count": evaluation["pass_count"],
            "greedy_task_count": evaluation["task_count"],
            "plateau_reached": plateau_reached,
            "plateau_evaluations": plateau_window,
            "plateau_tolerance": plateau_tolerance,
            "elapsed_seconds": time.perf_counter() - cycle_started,
        }
        append_jsonl(output_dir / "pilot-evaluations.jsonl", {**record, "details": evaluation["details"]})
        # Log sample rate every epoch and flag carried-forward values when no batch was sampled.
        if wandb_run is not None:
            wandb_metrics = {
                "rs/greedy_pass_rate": evaluation["pass_rate"],
                "rs/greedy_pass_at_1": evaluation["pass_rate"],
                "rs/greedy_pass_count": evaluation["pass_count"],
                "rs/task_count": evaluation["task_count"],
                "rs/sample_pass_rate_is_fresh": int(bool(counts["candidate_equivalents"])),
                "rs/model_sampling_is_fresh": int(sample_is_fresh),
                "rs/generated_candidates": counts["generated_candidates"],
                "rs/cached_candidates": counts["cached_candidates"],
                "rs/cached_tasks": counts["cached_tasks"],
                "rs/candidate_equivalents": counts["candidate_equivalents"],
                "rs/cache_full_passes": counts["cached_full_passes"],
                "rs/full_passes": counts["full_passes"],
                "rs/accepted_new": counts["new_solutions"],
                "rs/solution_coverage": record["solution_coverage"],
                "rs/pass_at_20_ceiling": ceiling if sampling_complete else 0.0,
                "rs/sampling_complete": int(sampling_complete),
                "rs/sft_loss": loss,
                "rs/plateau_reached": int(plateau_reached),
                "rs/cycle": cycle,
                "rs/elapsed_seconds": record["elapsed_seconds"],
            }
            if last_sample_pass_rate is not None:
                wandb_metrics["rs/sample_pass_rate"] = last_sample_pass_rate
            if counts["generated_candidates"]:
                wandb_metrics["rs/model_generated_sample_pass_rate"] = counts["full_passes"] / counts["generated_candidates"]
            wandb_run.log(wandb_metrics)
        history.append(evaluation["pass_rate"])
        state = {"attempts": attempts, "evaluations": history, "cycles_completed": cycle, "last_sample_pass_rate": last_sample_pass_rate, "pass_at_20_ceiling": ceiling if sampling_complete else None, "plateau_reached": plateau_reached}
        write_json(state_path, state)
        print(json.dumps(record, ensure_ascii=False), flush=True)
        if plateau_reached:
            break
    # Save the fixed pilot outcomes and the requested stopping decision.
    plateau_result = {"task_ids": pilot_ids, "evaluations": history, "pass_at_20_ceiling": ceiling, "greedy_pass_at_1": evaluation["pass_rate"], "plateau_reached": True, "plateau_evaluations": plateau_window, "plateau_tolerance": plateau_tolerance, "max_candidates_per_task": int(config["candidate_batch_size"]) * max_tries, "adaptive_stop_on_first_pass": True}
    write_json(output_dir / "pilot-plateau.json", plateau_result)
    if wandb_run is not None:
        wandb_run.summary["rs/pass_at_20_ceiling"] = ceiling
        wandb_run.summary["rs/plateau_reached"] = True
        wandb_run.finish()
    print(f"PILOT PLATEAU REACHED after {cycle} epochs on task IDs {pilot_ids}.", flush=True)


def run_full_collection(config: dict[str, Any], output_dir: Path, solution_store_path: Path) -> None:
    """Collect one passing solution per task from the full original plus harder synthetic dataset."""
    import torch

    # Start a phase-specific W&B run before recording full-data collection metrics.
    wandb_run = start_wandb(config, "full_collect", output_dir)
    # Load and validate the exact full-data pool before starting base-model generation.
    tasks = load_training_tasks(config)
    expected = config.get("expected_train_samples")
    if expected is not None and len(tasks) != int(expected):
        raise ValueError(f"Expected {expected} full training tasks, but loaded {len(tasks)}.")
    torch.set_num_threads(int(config["torch_num_threads"]))
    model, tokenizer = load_model(config)
    state_path = output_dir / "full-collection-state.json"
    trace_path = output_dir / "full-collection-progress.jsonl"
    # Retry unresolved tasks in configured batches until all tasks pass or reach the try limit.
    round_index = 0
    while True:
        round_index += 1
        # Count all prior passing records as cached slots at the start of this round.
        round_store = load_solution_store(solution_store_path)
        cached_task_count = sum(str(task["task_id"]) in round_store for task in tasks)
        cached_candidates = cached_task_count * int(config["candidate_batch_size"])
        # Log solution coverage and candidate yield after every completed task chunk.
        def log_chunk_progress(progress: dict[str, Any]) -> None:
            store = load_solution_store(solution_store_path)
            covered_tasks = sum(str(task["task_id"]) in store for task in tasks)
            metrics = {"rs/full_round": round_index, "rs/full_collection_tasks_processed": progress["tasks_processed"], "rs/full_collection_active_tasks": progress["active_task_count"], "rs/full_solution_coverage": covered_tasks / len(tasks), "rs/full_solutions_added": progress["new_solutions"], "rs/full_candidates_generated": progress["generated_candidates"], "rs/full_passes": progress["full_passes"], "rs/full_cached_candidates": cached_candidates, "rs/full_candidate_equivalents": cached_candidates + progress["generated_candidates"]}
            # Log fresh model yield separately from the cache-inclusive response-slot rate.
            if progress["chunk_candidates"]:
                metrics["rs/full_candidate_pass_rate"] = progress["chunk_full_passes"] / progress["chunk_candidates"]
            progress_denominator = cached_candidates + progress["generated_candidates"]
            if progress_denominator:
                metrics["rs/full_sample_pass_rate"] = (cached_candidates + progress["full_passes"]) / progress_denominator
            if wandb_run is not None:
                wandb_run.log(metrics)
            append_jsonl(output_dir / "full-collection-rounds.jsonl", {"event": "chunk_progress", **metrics})

        counts = collect_round(tasks, model, tokenizer, config, solution_store_path, state_path, trace_path, log_chunk_progress)
        counts.pop("attempts")
        store = load_solution_store(solution_store_path)
        covered = sum(str(task["task_id"]) in store for task in tasks)
        record = {**counts, "covered_tasks": covered, "total_tasks": len(tasks), "coverage_rate": covered / len(tasks)}
        append_jsonl(output_dir / "full-collection-rounds.jsonl", record)
        if wandb_run is not None:
            full_metrics = {"rs/full_solution_coverage": record["coverage_rate"], "rs/full_solutions_added": counts["new_solutions"], "rs/full_round": round_index, "rs/full_candidate_equivalents": counts["candidate_equivalents"], "rs/full_cached_candidates": counts["cached_candidates"], "rs/full_generated_candidates": counts["generated_candidates"], "rs/full_cache_full_passes": counts["cached_full_passes"]}
            # Keep model-only yield separate and include cached passing slots in the overall sample rate.
            if counts["generated_candidates"]:
                full_metrics["rs/full_candidate_pass_rate"] = counts["full_passes"] / counts["generated_candidates"]
            if counts["candidate_equivalents"]:
                full_metrics["rs/full_sample_pass_rate"] = counts["sample_passes_with_cache"] / counts["candidate_equivalents"]
            wandb_run.log(full_metrics)
        print(json.dumps(record), flush=True)
        if counts["active_tasks"] == 0:
            break
    # Record the final coverage and persistent solution-store path for the training stage.
    write_json(output_dir / "full-collection-summary.json", {"total_tasks": len(tasks), "covered_tasks": covered, "coverage_rate": covered / len(tasks), "solution_store": str(solution_store_path), "attempt_limit": int(config["max_generation_batches_per_task"])})
    if wandb_run is not None:
        wandb_run.summary["rs/full_solution_coverage"] = covered / len(tasks)
        wandb_run.summary["rs/full_solutions"] = covered
        wandb_run.finish()


def run_full_training(config: dict[str, Any], output_dir: Path, solution_store_path: Path, resume_from_checkpoint: str | None) -> None:
    """Train on cached passing original-task solutions and evaluate both full sets each epoch."""
    import torch
    from data import build_sft_dataset
    from transformers import DataCollatorForSeq2Seq, Trainer, TrainerCallback, TrainingArguments
    from train import evaluate_training_mbpp, run_qwen_evalplus

    # Start a phase-specific W&B run that resumes across monitor restarts.
    wandb_run = start_wandb(config, "full_train", output_dir)
    # Bind live full-evaluation metrics to optimizer steps in the W&B history.
    if wandb_run is not None:
        wandb_run.define_metric("optimizer_step")
        wandb_run.define_metric("sft/*", step_metric="optimizer_step")
        wandb_run.define_metric("evalplus/*", step_metric="optimizer_step")
        wandb_run.define_metric("training_set/*", step_metric="optimizer_step")
    # Load the original task pool and select its accepted solution records for SFT.
    tasks = load_training_tasks(config)
    records = build_sft_records(tasks, solution_store_path)
    if not records:
        raise RuntimeError("No passing solutions exist for SFT, so full-data training cannot start.")
    if len(records) < int(config["sft_per_device_train_batch_size"]):
        print(f"The accepted set has {len(records)} rows, so the final SFT batch will be smaller than the configured batch size.", flush=True)
    torch.set_num_threads(int(config["torch_num_threads"]))
    model, tokenizer = load_model(config)
    train_dataset = build_sft_dataset(records, tokenizer, config)
    training_dir = output_dir / "full-training"
    checkpoint_dir = training_dir / "checkpoints"
    metrics_path = training_dir / "training-metrics.jsonl"
    # Evaluate canonical EvalPlus and every original training task after each saved epoch.
    class ProgressCallback(TrainerCallback):
        """Write live SFT metrics and full evaluation results to JSONL and W&B."""

        def evaluate_saved_epoch(self, state: Any) -> None:
            """Evaluate a saved epoch checkpoint once and persist its completion marker."""
            epoch = int(round(float(state.epoch or 0)))
            if epoch <= 0:
                return
            checkpoint_path = checkpoint_dir / f"checkpoint-{int(state.global_step)}"
            marker_path = training_dir / f"epoch-{epoch:06d}.complete.json"
            if not checkpoint_path.is_dir() or marker_path.exists():
                return
            started = time.perf_counter()
            model.eval()
            model.to("cpu")
            torch.cuda.empty_cache()
            try:
                evalplus = run_qwen_evalplus(checkpoint_path, training_dir, f"epoch-{epoch:06d}")
                training_eval = evaluate_training_mbpp(checkpoint_path, tasks, config, f"training-epoch-{epoch:06d}")
                result = {"kind": "full_epoch_evaluation", "epoch": epoch, "step": int(state.global_step), "evalplus": evalplus["metrics"], "training_set": training_eval["metrics"], "elapsed_seconds": time.perf_counter() - started, "checkpoint": str(checkpoint_path)}
                append_jsonl(training_dir / "evaluations.jsonl", result)
                if wandb_run is not None:
                    payload = {"optimizer_step": int(state.global_step), "sft/epoch": epoch, "evaluation/elapsed_seconds": result["elapsed_seconds"]}
                    payload.update({f"evalplus/{key}": value for key, value in evalplus["metrics"].items() if isinstance(value, (int, float))})
                    payload.update({f"training_set/{key}": value for key, value in training_eval["metrics"].items() if isinstance(value, (int, float))})
                    wandb_run.log(payload)
                write_json(marker_path, result)
                print(f"Completed epoch {epoch} evaluation at step {state.global_step}: EvalPlus={evalplus['metrics']} training={training_eval['metrics']}", flush=True)
            finally:
                import gc
                gc.collect()
                torch.cuda.empty_cache()
                model.to("cuda")
                model.train()

        def on_log(self, args: Any, state: Any, control: Any, logs: dict[str, Any] | None = None, **kwargs: Any) -> Any:
            """Append all available Trainer metrics with the optimizer step."""
            if logs:
                append_jsonl(metrics_path, {"kind": "training", "step": int(state.global_step), "epoch": float(state.epoch or 0), **logs})
                if wandb_run is not None:
                    wandb_run.log({"optimizer_step": int(state.global_step), **{f"sft/{key}": value for key, value in logs.items() if isinstance(value, (int, float))}})
            return control

        def on_train_begin(self, args: Any, state: Any, control: Any, **kwargs: Any) -> Any:
            """Finish evaluation for the last checkpoint if a restart interrupted it."""
            self.evaluate_saved_epoch(state)
            return control

        def on_save(self, args: Any, state: Any, control: Any, **kwargs: Any) -> Any:
            """Evaluate the checkpoint that Trainer saved at the end of this epoch."""
            self.evaluate_saved_epoch(state)
            return control

    # Configure one million response-only SFT epochs and retain every epoch checkpoint.
    training_args = TrainingArguments(
        output_dir=str(checkpoint_dir),
        learning_rate=float(config["learning_rate"]),
        max_steps=-1,
        num_train_epochs=int(config["target_epochs"]),
        per_device_train_batch_size=int(config["sft_per_device_train_batch_size"]),
        gradient_accumulation_steps=int(config["gradient_accumulation_steps"]),
        logging_steps=int(config["logging_steps"]),
        save_strategy="epoch",
        save_total_limit=None,
        report_to="none",
        bf16=bool(config.get("bf16", True)) and torch.cuda.is_available(),
        fp16=bool(config.get("fp16", False)) and torch.cuda.is_available(),
        dataloader_num_workers=int(config["dataloader_num_workers"]),
        seed=int(config["seed"]),
        disable_tqdm=True,
        remove_unused_columns=False,
    )
    # Start or resume the full-data run while writing only to its dedicated checkpoint path.
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        data_collator=DataCollatorForSeq2Seq(tokenizer=tokenizer, model=model, padding=True),
        callbacks=[ProgressCallback()],
    )
    trainer.train(resume_from_checkpoint=resume_from_checkpoint or None)
    # Save a completion sentinel only after the configured epoch limit has finished.
    write_json(training_dir / "training-complete.json", {"global_step": int(trainer.state.global_step), "target_epochs": int(config["target_epochs"]), "solution_count": len(records), "checkpoint_dir": str(checkpoint_dir)})
    trainer.save_model(str(training_dir / "final-model"))
    if wandb_run is not None:
        wandb_run.summary["rs/full_training_epochs"] = int(round(float(trainer.state.epoch or 0)))
        wandb_run.finish()


def main() -> None:
    """Dispatch pilot sampling, full-data collection, or resumable SFT from the YAML config."""
    # Parse phase arguments and resolve all paths against the repository root.
    parser = argparse.ArgumentParser(description="Incremental rejection sampling and SFT.")
    parser.add_argument("--config", required=True)
    parser.add_argument("--phase", choices=["pilot", "full-collect", "full-train"], required=True)
    parser.add_argument("--resume-from-checkpoint")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = root / config_path
    config = load_config(config_path)
    model_path = Path(config["model_name_or_path"])
    if not model_path.is_absolute():
        config["model_name_or_path"] = str(root / model_path)
    output_dir = Path(config["output_dir"])
    if not output_dir.is_absolute():
        output_dir = root / output_dir
    store_path = Path(config["solution_store_path"])
    if not store_path.is_absolute():
        store_path = root / store_path
    # Run the requested phase without importing or modifying GRPO checkpoints.
    if args.phase == "pilot":
        run_pilot(config, output_dir, store_path)
    elif args.phase == "full-collect":
        run_full_collection(config, output_dir, store_path)
    else:
        run_full_training(config, output_dir, store_path, args.resume_from_checkpoint)


if __name__ == "__main__":
    # Execute the selected experiment phase from the command line.
    main()
