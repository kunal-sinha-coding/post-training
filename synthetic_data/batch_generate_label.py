"""Generate and label synthetic tasks in five streaming batches.

The flow loads the clean verifier exemplars, generates three validated GPT-5.4 Mini tasks
from each exemplar, immediately samples ten Qwen 0.5B candidates with the copied EvalPlus
ChatML/vLLM wrapper, labels them in the sandbox, persists each batch, and reports cumulative
Pass@K and cost every five minutes and after every completed batch.
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from generate_tasks import generate_one_task
from sandbox import execute_code, extract_code, validate_interface


def load_exemplars(path: Path) -> list[dict[str, str]]:
    """Load one reference row per clean verifier task."""
    # Keep only positive reference rows so each exemplar represents a known-correct task.
    exemplars: dict[str, dict[str, str]] = {}
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("source", "reference") == "reference":
                exemplars[str(row["task_id"])] = {"task_id": str(row["task_id"]), "task": str(row["task"]), "code": str(row["code"])}
    return list(exemplars.values())


def reference_setup(reference_code: str, function_name: str) -> str:
    """Extract non-function support definitions for candidate execution."""
    # Preserve imports and helper definitions while preventing the reference function from becoming a fallback.
    tree = ast.parse(reference_code)
    return "\n".join(ast.unparse(node) for node in tree.body if not (isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function_name))


def pass_sweep(task_labels: dict[str, list[int]]) -> dict[str, float]:
    """Compute cumulative task-level Pass@K for every completed synthetic task."""
    # Count a task as solved at K when any of its first K candidates passes all tests.
    tasks = list(task_labels.values())
    if not tasks:
        return {str(k): 0.0 for k in range(1, 11)}
    return {str(k): sum(any(label for label in labels[:k]) for labels in tasks) / len(tasks) for k in range(1, 11)}


def format_sweep(task_labels: dict[str, list[int]]) -> str:
    """Format the cumulative Pass@K sweep for terminal progress reports."""
    # Keep the report compact while exposing every requested K value.
    return " ".join(f"P@{k}={value:.1%}" for k, value in pass_sweep(task_labels).items())


def generate_batch_tasks(client: Any, exemplars: list[dict[str, str]], model: str, batch_number: int, output_path: Path, stats: dict[str, Any], lock: threading.Lock, max_cost_usd: float) -> list[dict[str, Any]]:
    """Generate and persist three validated synthetic tasks per exemplar concurrently."""
    # Submit one worker per exemplar so independent GPT requests run concurrently.
    generated: list[dict[str, Any]] = []
    def worker(exemplar: dict[str, str]) -> list[dict[str, Any]]:
        """Generate three tasks from one clean exemplar."""
        # Retry rejected generations until this exemplar contributes exactly three accepted tasks.
        exemplar_text = f"Task description:\n{exemplar['task']}\n\nReference implementation:\n{exemplar['code']}"
        accepted: list[dict[str, Any]] = []
        attempts = 0
        while len(accepted) < 3 and attempts < 12:
            with lock:
                if stats["estimated_cost_usd"] >= max_cost_usd:
                    raise RuntimeError(f"GPT cost cap of ${max_cost_usd:.2f} reached.")
            attempts += 1
            task, tokens, reason = generate_one_task(client, model, exemplar_text)
            with lock:
                stats["requests"] += 1
                stats["input_tokens"] += tokens["input_tokens"]
                stats["output_tokens"] += tokens["output_tokens"]
                stats["rejected"] += int(task is None)
                stats["estimated_cost_usd"] = stats["input_tokens"] * 0.75 / 1_000_000 + stats["output_tokens"] * 4.50 / 1_000_000
            if task is None:
                continue
            task["exemplar_task_id"] = exemplar["task_id"]
            accepted.append(task)
        if len(accepted) < 3:
            raise RuntimeError(f"Could not validate three tasks from exemplar {exemplar["task_id"]} after {attempts} requests.")
        return accepted
    with ThreadPoolExecutor(max_workers=16) as executor:
        futures = [executor.submit(worker, exemplar) for exemplar in exemplars]
        for future in as_completed(futures):
            tasks = future.result()
            with lock:
                for task in tasks:
                    task["task_id"] = f"synthetic-b{batch_number:02d}-{len(generated) + 1:04d}"
                    generated.append(task)
                    stats["generated_tasks"] += 1
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    with output_path.open("a", encoding="utf-8") as handle:
                        handle.write(json.dumps(task, ensure_ascii=False) + "\n")
    return generated


def label_batch_tasks(tasks: list[dict[str, Any]], model_path: str, output_dir: Path, batch_number: int, task_labels: dict[str, list[int]], stats: dict[str, Any], lock: threading.Lock) -> None:
    """Sample and sandbox-label ten Qwen candidates for every generated task."""
    # Load the copied EvalPlus decoder once for the entire batch to maximize GPU throughput.
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "qwen_eval" / "eval_plus"))
    from model import make_model
    model = make_model(model_type="qwen2", model_size="chat", model_path=model_path, batch_size=10, temperature=0.2, dataset="mbpp")
    batch_dir = output_dir / f"batch-{batch_number:02d}"
    batch_dir.mkdir(parents=True, exist_ok=True)
    for task in tasks:
        # Use the same docstring-plus-assertion prompt shape as the official MBPP EvalPlus records.
        prompt = f'"""\n{task["task"]}\n{task["test_code"]}\n"""\n'
        completions = model.codegen(prompt, do_sample=True, num_samples=10)
        task_dir = batch_dir / str(task["task_id"])
        task_dir.mkdir(parents=True, exist_ok=True)
        setup = reference_setup(str(task["reference_code"]), str(task["function_name"]))
        labels: list[int] = []
        records: list[dict[str, Any]] = []
        for index, completion in enumerate(completions):
            # Extract the same fenced completion body used by the repository sandbox.
            try:
                code = extract_code(completion)
            except ValueError:
                code = completion.strip()
            (task_dir / f"{index}.py").write_text(code, encoding="utf-8")
            valid = validate_interface(code, str(task["test_code"]))
            result = execute_code(setup + "\n" + code, str(task["test_code"])) if valid else None
            label = int(result is not None and result.status == "passed")
            labels.append(label)
            records.append({"task_id": task["task_id"], "candidate_index": index, "code": code, "label": label, "status": result.status if result else "interface_error"})
        (task_dir / "labels.json").write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")
        with lock:
            task_labels[str(task["task_id"])] = labels
            stats["labeled_tasks"] += 1
            stats["candidates"] += len(labels)
            stats["positive_candidates"] += sum(labels)
        print(json.dumps({"batch": batch_number, "task_id": task["task_id"], "correct": sum(labels), "tasks_done": stats["labeled_tasks"], "pass_sweep": pass_sweep(task_labels)}, sort_keys=True), flush=True)
    # Release the decoder before the next batch so memory remains bounded.
    del model
    if hasattr(__import__("torch"), "cuda") and __import__("torch").cuda.is_available():
        __import__("torch").cuda.empty_cache()


def reporter(stop_event: threading.Event, task_labels: dict[str, list[int]], stats: dict[str, Any], lock: threading.Lock) -> None:
    """Print cumulative progress and Pass@K every five minutes."""
    # Emit a periodic status line even while GPT requests or GPU generation are busy.
    while not stop_event.wait(300):
        with lock:
            snapshot = dict(stats)
            sweep = format_sweep(task_labels)
        print(f"[5-minute update] generated_tasks={snapshot['generated_tasks']} labeled_tasks={snapshot['labeled_tasks']} candidates={snapshot['candidates']} rejected_gpt={snapshot['rejected']} cost_usd={snapshot['estimated_cost_usd']:.4f} {sweep}", flush=True)


def run(config: dict[str, Any]) -> None:
    """Run five sequential generate-label batches over the clean training exemplars."""
    # Load the API environment and fail before starting a partial experiment when credentials are absent.
    load_dotenv()
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is required.")
    from openai import OpenAI
    exemplars = load_exemplars(Path(config["exemplars"]))
    batch_count = int(config["batches"])
    batch_size = (len(exemplars) + batch_count - 1) // batch_count
    output_dir = Path(config["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)
    stats: dict[str, Any] = {"generated_tasks": 0, "labeled_tasks": 0, "candidates": 0, "positive_candidates": 0, "rejected": 0, "requests": 0, "input_tokens": 0, "output_tokens": 0, "estimated_cost_usd": 0.0}
    task_labels: dict[str, list[int]] = {}
    lock = threading.Lock()
    stop_event = threading.Event()
    monitor = threading.Thread(target=reporter, args=(stop_event, task_labels, stats, lock), daemon=True)
    monitor.start()
    client = OpenAI(timeout=60.0, max_retries=0)
    try:
        for batch_number in range(1, batch_count + 1):
            # Select a deterministic slice so an interrupted run can be audited batch by batch.
            start = (batch_number - 1) * batch_size
            batch_exemplars = exemplars[start:min(start + batch_size, len(exemplars))]
            tasks_path = output_dir / f"batch-{batch_number:02d}-tasks.jsonl"
            tasks = generate_batch_tasks(client, batch_exemplars, config["generator_model"], batch_number, tasks_path, stats, lock, float(config["max_cost_usd"]))
            label_batch_tasks(tasks, config["candidate_model"], output_dir, batch_number, task_labels, stats, lock)
            print(f"[batch {batch_number}/{batch_count} complete] exemplars={len(batch_exemplars)} generated_tasks={len(tasks)} labeled_tasks={stats['labeled_tasks']} cost_usd={stats['estimated_cost_usd']:.4f} {format_sweep(task_labels)}", flush=True)
    finally:
        stop_event.set()
        monitor.join(timeout=1)
    (output_dir / "summary.json").write_text(json.dumps({**stats, "pass_at_k": pass_sweep(task_labels)}, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({**stats, "pass_at_k": pass_sweep(task_labels)}, indent=2), flush=True)


def parse_args() -> dict[str, Any]:
    """Parse batch pipeline paths and model configuration."""
    # Keep all experiment parameters explicit so the long run is reproducible.
    parser = argparse.ArgumentParser(description="Generate and label synthetic tasks in streaming batches.")
    parser.add_argument("--exemplars", default="outputs/clean-verifier/train.jsonl")
    parser.add_argument("--output-dir", default="outputs/synthetic-clean-batched")
    parser.add_argument("--batches", type=int, default=5)
    parser.add_argument("--generator-model", default="gpt-5.4-mini")
    parser.add_argument("--candidate-model", default="Qwen/Qwen2.5-Coder-0.5B-Instruct")
    parser.add_argument("--max-cost-usd", type=float, default=25.0)
    return vars(parser.parse_args())


if __name__ == "__main__":
    # Start the complete five-batch pipeline from the command line.
    run(parse_args())
