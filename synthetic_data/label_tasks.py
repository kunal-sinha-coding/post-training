"""Generate and sandbox-label ten Qwen candidates for every synthetic task.

The flow loads the GPT-generated task and reference records, splits tasks deterministically,
generates ten Qwen 0.5B candidates per task, labels each candidate in parallel through the
sandbox, and appends train and validation JSONL records immediately with ten-task progress.
"""

from __future__ import annotations

import argparse
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import torch

from sandbox import score_completion


def label_candidate(item: tuple[str, str, str, str, int]) -> dict[str, Any]:
    """Sandbox one generated candidate and return its durable label record."""
    # Convert a complete sandbox result into the binary correctness label used by the verifier.
    task_id, task, code, tests, candidate_index = item
    _, detail = score_completion(code, tests)
    return {"task_id": task_id, "task": task, "code": code.strip(), "label": float(detail["status"] == "passed"), "source": "generated", "candidate_index": candidate_index, "status": detail["status"]}


def write_records(path: Path, records: list[dict[str, Any]]) -> None:
    """Append labeled candidates and flush them to disk."""
    # Persist each completed task before the next task is generated.
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def generate_candidates(config: dict[str, Any]) -> dict[str, int]:
    """Generate and label ten candidates per synthetic task with batched GPU inference."""
    # Load the complete accepted task artifact without regenerating GPT tasks.
    tasks = [json.loads(line) for line in Path(config["tasks"]).read_text(encoding="utf-8").splitlines() if line.strip()]
    split_index = int(len(tasks) * float(config["train_fraction"]))
    train_tasks = tasks[:split_index]
    validation_tasks = tasks[split_index:]
    output_dir = Path(config["output_dir"])
    train_path = output_dir / "train.jsonl"
    validation_path = output_dir / "validation.jsonl"
    if bool(config["overwrite"]):
        # Remove only the two explicit candidate artifacts before a deliberate fresh labeling run.
        train_path.unlink(missing_ok=True)
        validation_path.unlink(missing_ok=True)
    completed_ids: set[str] = set()
    totals = {"tasks": 0, "candidates": 0, "positive": 0, "negative": 0, "sandbox_errors": 0}
    for path in (train_path, validation_path):
        if not path.exists():
            continue
        # Recover completed task IDs and label totals so interrupted runs resume accurately.
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    record = json.loads(line)
                    completed_ids.add(str(record["task_id"]))
                    totals["candidates"] += 1
                    totals["positive"] += int(record["label"] == 1)
                    totals["negative"] += int(record["label"] == 0)
                    totals["sandbox_errors"] += int(record["status"] not in {"passed", "failed"})
    totals["tasks"] = len(completed_ids)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    from transformers import AutoModelForCausalLM, AutoTokenizer

    # Load the local generation model once and keep it resident during labeling.
    tokenizer = AutoTokenizer.from_pretrained(config["model"])
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(config["model"]).to(device)
    model.eval()
    task_batch_size = max(1, int(config["generation_task_batch_size"]))
    with ThreadPoolExecutor(max_workers=max(1, int(config["label_workers"]))) as executor:
        # Process pending tasks in GPU batches while preserving deterministic train and validation assignment.
        pending = [task for task in [*train_tasks, *validation_tasks] if str(task["task_id"]) not in completed_ids]
        batch_start = 0
        while batch_start < len(pending):
            task_batch = pending[batch_start:batch_start + task_batch_size]
            prompts = [f"Task:\n{task['task']}\n\nWrite only the Python implementation.\n" for task in task_batch]
            try:
                # Attempt the largest currently available generation batch.
                encoded = tokenizer(prompts, return_tensors="pt", padding=True, truncation=True, max_length=int(config["max_prompt_tokens"])).to(device)
                with torch.inference_mode():
                    outputs = model.generate(**encoded, do_sample=True, temperature=float(config["temperature"]), top_p=float(config["top_p"]), num_return_sequences=int(config["candidates_per_task"]), max_new_tokens=int(config["max_new_tokens"]), pad_token_id=tokenizer.pad_token_id)
            except RuntimeError as exc:
                # Halve the task batch after CUDA memory failures and retry the same tasks.
                if task_batch_size == 1 or "out of memory" not in str(exc).lower():
                    raise
                task_batch_size = max(1, task_batch_size // 2)
                print(f"Reducing generation task batch size to {task_batch_size} after memory failure.", flush=True)
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                continue
            input_width = encoded["input_ids"].shape[1]
            decoded = tokenizer.batch_decode(outputs[:, input_width:], skip_special_tokens=True)
            # Group the model's task-major return order back into ten candidates per task.
            for task_offset, task_record in enumerate(task_batch):
                first = task_offset * int(config["candidates_per_task"])
                codes = decoded[first:first + int(config["candidates_per_task"])]
                items = [(str(task_record["task_id"]), str(task_record["task"]), code, str(task_record["test_code"]), index + 1) for index, code in enumerate(codes)]
                records = list(executor.map(label_candidate, items))
                output_path = train_path if task_record in train_tasks else validation_path
                write_records(output_path, records)
                completed_ids.add(str(task_record["task_id"]))
                totals["tasks"] += 1
                totals["candidates"] += len(records)
                totals["positive"] += sum(int(record["label"] == 1) for record in records)
                totals["negative"] += sum(int(record["label"] == 0) for record in records)
                totals["sandbox_errors"] += sum(int(record["status"] not in {"passed", "failed"}) for record in records)
                if totals["tasks"] % int(config["progress_every"]) == 0 or totals["tasks"] == len(tasks):
                    # Report task, candidate, label, and sandbox totals at the requested cadence.
                    print(json.dumps(totals, sort_keys=True), flush=True)
            batch_start += len(task_batch)
    del model
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    return totals


def parse_args() -> dict[str, Any]:
    """Parse labeling model, data, batching, and progress configuration."""
    # Keep all operational parameters explicit so the run can be resumed or reproduced.
    parser = argparse.ArgumentParser(description="Generate and sandbox-label synthetic tasks with Qwen.")
    parser.add_argument("--tasks", default="outputs/synthetic-tasks/tasks.jsonl")
    parser.add_argument("--model", default="Qwen/Qwen2.5-Coder-0.5B-Instruct")
    parser.add_argument("--output-dir", default="outputs/synthetic-verifier")
    parser.add_argument("--candidates-per-task", type=int, default=10)
    parser.add_argument("--label-workers", type=int, default=16)
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--top-p", type=float, default=0.95)
    parser.add_argument("--max-new-tokens", type=int, default=512)
    parser.add_argument("--max-prompt-tokens", type=int, default=512)
    parser.add_argument("--train-fraction", type=float, default=0.8)
    parser.add_argument("--progress-every", type=int, default=10)
    parser.add_argument("--generation-task-batch-size", type=int, default=16)
    parser.add_argument("--overwrite", action="store_true")
    return vars(parser.parse_args())


if __name__ == "__main__":
    # Start the configured candidate generation and labeling run.
    generate_candidates(parse_args())
