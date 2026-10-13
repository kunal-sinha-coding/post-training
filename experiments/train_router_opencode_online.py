# This script streams OpenCodeInstruct, caches one Qwen 0.5B label per task, and trains MiniLM.
# It validates each source test suite against its supplied answer before it scores the Qwen completion.
# It logs task collection, cache use, training loss, and router retrieval metrics to W&B.
# It saves task labels, evaluation history, predictions, a step-100 checkpoint, and the final model.

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import gc
import os
import random
import sqlite3
import subprocess
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path
from typing import Any

import torch
from datasets import load_dataset
from huggingface_hub import HfApi
from transformers import AutoModel, AutoTokenizer

from experiments.run_qwen_official_greedy_eval import QWEN_EVALPLUS_STOP_STRINGS, apply_stops, normalize_tokenizer_metadata
from experiments.train_router_full import binary_metrics, encode_rows, predict_rows
from sandbox import extract_code


SAFE_IMPORTS = {
    "bisect", "collections", "copy", "datetime", "decimal", "fractions", "functools", "heapq",
    "itertools", "json", "math", "operator", "random", "re", "statistics", "string", "typing",
}
BLOCKED_NAMES = {
    "__builtins__", "__import__", "compile", "eval", "exec", "getattr", "globals", "input",
    "locals", "open", "setattr", "delattr", "vars",
}


# Normalize whitespace for benchmark overlap checks and exact duplicate removal.
def normalized_text(text: str) -> str:
    # Collapse all whitespace and lowercase task descriptions into a stable comparison key.
    return " ".join(text.split()).lower()


# Parse the serialized OpenCodeInstruct test list without evaluating source text.
def parse_test_list(value: str) -> list[str]:
    # Require a nonempty JSON array of strings so malformed rows cannot enter the label set.
    parsed = json.loads(value)
    if not isinstance(parsed, list) or not parsed or any(not isinstance(item, str) for item in parsed):
        raise ValueError("unit_tests must be a nonempty JSON array of strings")
    return parsed


# Reject Python snippets that try to import unsafe modules or access unsafe builtins.
def validate_safe_python(source: str) -> None:
    # Parse each candidate and test suite, then allow only common algorithmic standard-library code.
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots = [alias.name.split(".", 1)[0] for alias in node.names]
            if any(root not in SAFE_IMPORTS for root in roots):
                raise ValueError("unsafe_import")
        if isinstance(node, ast.ImportFrom) and node.module:
            if node.module.split(".", 1)[0] not in SAFE_IMPORTS:
                raise ValueError("unsafe_import")
        if isinstance(node, ast.Name) and node.id in BLOCKED_NAMES:
            raise ValueError("unsafe_builtin")
        if isinstance(node, ast.Attribute) and node.attr.startswith("__"):
            raise ValueError("dunder_attribute")


# Run trusted-looking task code with strict process limits and blocked filesystem and network events.
def run_restricted_tests(code: str, tests: str, timeout_seconds: float) -> dict[str, Any]:
    # Validate source before creating an isolated temporary script and bounded child process.
    validate_safe_python(code)
    validate_safe_python(tests)
    guard = """
import sys
allowed = "bisect collections copy datetime decimal fractions functools heapq itertools json math operator random re statistics string typing".split()
for module_name in allowed:
    __import__(module_name)
def deny(event, args):
    if event in {"open", "socket.__new__", "socket.connect", "socket.bind", "subprocess.Popen", "os.system", "os.exec", "os.fork", "ctypes.dlopen"}:
        raise PermissionError("operation blocked by router test runner")
sys.addaudithook(deny)
"""
    with tempfile.TemporaryDirectory(prefix="router-tests-") as directory:
        script = Path(directory) / "candidate.py"
        script.write_text(guard + "\n" + code + "\n" + tests + "\n", encoding="utf-8")
        command = [
            "prlimit", "--cpu=5", "--as=1073741824", "--fsize=1048576", "--nproc=1", "--nofile=64",
            sys.executable, "-I", str(script),
        ]
        stdout_path = Path(directory) / "stdout.txt"
        stderr_path = Path(directory) / "stderr.txt"
        try:
            with stdout_path.open("w", encoding="utf-8") as stdout_file, stderr_path.open("w", encoding="utf-8") as stderr_file:
                result = subprocess.run(command, stdout=stdout_file, stderr=stderr_file, text=True, timeout=timeout_seconds, cwd=directory, env={"PATH": os.environ.get("PATH", ""), "PYTHONIOENCODING": "utf-8"}, check=False)
        except subprocess.TimeoutExpired as error:
            return {"passed": False, "status": "timeout", "stderr": str(error)[:1000]}
        return {"passed": result.returncode == 0, "status": "passed" if result.returncode == 0 else "failed", "stderr": stderr_path.read_text(encoding="utf-8", errors="replace")[-2000:]}


# Build a stable label-cache key from the pinned row, checkpoint, prompt policy, and decode settings.
def make_cache_key(row: dict[str, Any], revision: str, model_fingerprint: str, prompt_version: str) -> tuple[str, str]:
    # Hash the task input and tests separately so any dataset or label-policy change invalidates reuse.
    test_text = json.dumps(parse_test_list(row["unit_tests"]), ensure_ascii=False)
    fingerprint = hashlib.sha256((row["input"] + "\n" + test_text).encode("utf-8")).hexdigest()
    key_payload = f"{revision}:{row['id']}:{fingerprint}:{model_fingerprint}:{prompt_version}:greedy-2048"
    return hashlib.sha256(key_payload.encode("utf-8")).hexdigest(), fingerprint


# Open a durable SQLite cache and create the single-completion label table if needed.
def checkpoint_fingerprint(path: Path) -> str:
    # Hash model configuration and checkpoint tensors so a changed Qwen model never reuses stale labels.
    digest = hashlib.sha256()
    model_files = [path / "config.json", *sorted(path.glob("*.safetensors"))]
    for model_file in model_files:
        digest.update(model_file.name.encode("utf-8"))
        with model_file.open("rb") as handle:
            for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
                digest.update(block)
    return digest.hexdigest()


def open_label_cache(path: Path) -> sqlite3.Connection:
    # Enable write-ahead logging so a process interruption preserves every committed batch.
    connection = sqlite3.connect(path)
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("CREATE TABLE IF NOT EXISTS labels (cache_key TEXT PRIMARY KEY, task_id TEXT, fingerprint TEXT, completion TEXT, label INTEGER, status TEXT, passed_tests INTEGER, total_tests INTEGER, created_at TEXT DEFAULT CURRENT_TIMESTAMP)")
    connection.commit()
    return connection


# Create one Qwen vLLM engine that remains loaded for all eight-task label batches.
def load_qwen_generator(model_path: Path, gpu_memory_utilization: float) -> tuple[Any, Any]:
    # Use the same bfloat16 greedy decoding settings as the existing EvalPlus generation flow.
    normalize_tokenizer_metadata(model_path)
    from vllm import LLM, SamplingParams

    engine = LLM(model=str(model_path), dtype="bfloat16", tensor_parallel_size=1, gpu_memory_utilization=gpu_memory_utilization, max_model_len=8192, enforce_eager=True)
    sampler = SamplingParams(temperature=0.0, top_p=1.0, max_tokens=2048, stop=list(QWEN_EVALPLUS_STOP_STRINGS))
    return engine, sampler


# Format one OpenCodeInstruct problem as a Python coding task without exposing its answer or tests.
def build_coding_prompt(task_text: str) -> str:
    # Ask for a complete implementation while preserving the required interface from the problem.
    fence = chr(96) * 3
    return (
        "<|im_start|>system\nYou are a precise Python coding assistant. Solve the task. Return only complete Python code. "
        "Implement the requested functions or classes with the exact interface. Do not include explanations or tests.<|im_end|>\n"
        "<|im_start|>user\n" + task_text.strip() + "\n<|im_end|>\n<|im_start|>assistant\n" + fence + "python\n"
    )


# Generate one greedy completion for the cache-missing tasks in one input batch.
def generate_batch(engine: Any, sampler: Any, prompts: list[str]) -> list[str]:
    # Preserve task order and strip only the official stop strings from each single output.
    outputs = engine.generate(prompts, sampler, use_tqdm=False)
    return [apply_stops(output.outputs[0].text).strip() for output in outputs]


# Validate the supplied answer against every source test before using that suite as a label oracle.
def validate_reference(row: dict[str, Any], tests: list[str], timeout_seconds: float) -> dict[str, Any]:
    # Mark unsupported source code or any failing test suite as invalid rather than labeling it as Qwen failure.
    try:
        reference = extract_code(str(row["output"]))
        result = run_restricted_tests(reference, "\n".join(tests), timeout_seconds)
        return {"valid": result["passed"], "status": result["status"], "stderr": result["stderr"]}
    except Exception as error:
        return {"valid": False, "status": str(error)[:100], "stderr": ""}


# Score one Qwen completion with the same complete task test suite after the reference validation.
def label_completion(completion: str, tests: list[str], timeout_seconds: float) -> dict[str, Any]:
    # Extract the generated Python code and treat only a complete successful test run as label one.
    try:
        candidate = extract_code(completion if "```" in completion else f"```python\n{completion}")
        result = run_restricted_tests(candidate, "\n".join(tests), timeout_seconds)
        return {"label": int(result["passed"]), "status": result["status"], "passed_tests": len(tests) if result["passed"] else 0, "total_tests": len(tests), "stderr": result["stderr"]}
    except Exception as error:
        return {"label": 0, "status": str(error)[:100], "passed_tests": 0, "total_tests": len(tests), "stderr": ""}


# Load the held-out EvalPlus dual-label rows and encode the same task prompts used by the earlier router.
def load_eval_rows(path: Path) -> tuple[list[dict[str, Any]], list[int], list[int]]:
    # Preserve separate MBPP and MBPP+ labels for each canonical task.
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return rows, [int(row["label_mbpp"]) for row in rows], [int(row["label_mbpp_plus"]) for row in rows]


# Train MiniLM from the completed streaming label file and evaluate the established retrieval metrics.
def train_router(args: argparse.Namespace, output_dir: Path, run: Any, eval_rows: list[dict[str, Any]], eval_mbpp_labels: list[int], eval_plus_labels: list[int]) -> dict[str, Any]:
    # Load the generated training labels after streaming has finished so vLLM can release its GPU memory.
    train_rows = [json.loads(line) for line in (output_dir / "router_dataset.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    if len({row["label"] for row in train_rows}) < 2:
        raise RuntimeError("OpenCodeInstruct label pass did not produce both classes.")
    random.seed(args.seed)
    torch.manual_seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)
    tokenizer = AutoTokenizer.from_pretrained(args.encoder)
    encoder = AutoModel.from_pretrained(args.encoder)
    train_encoded, train_labels = encode_rows(tokenizer, train_rows, args.max_length, "label")
    eval_encoded, _ = encode_rows(tokenizer, eval_rows, args.max_length, "label_mbpp")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    encoder.to(device)
    dropout = torch.nn.Dropout(0.1).to(device)
    head = torch.nn.Linear(int(encoder.config.hidden_size), 2).to(device)
    optimizer = torch.optim.AdamW(list(encoder.parameters()) + list(head.parameters()), lr=args.learning_rate)
    loss_function = torch.nn.CrossEntropyLoss()
    labels_tensor = torch.tensor(train_labels, dtype=torch.long)
    metrics_path = output_dir / "evaluation_history.jsonl"
    losses_path = output_dir / "training_loss.jsonl"
    predictions_path = output_dir / "predictions.jsonl"
    metrics_path.unlink(missing_ok=True)
    losses_path.unlink(missing_ok=True)
    predictions_path.unlink(missing_ok=True)
    metrics_log: list[dict[str, Any]] = []

    # Evaluate the current model on all observed labels and both held-out EvalPlus targets.
    def evaluate_and_log(step: int) -> dict[str, Any]:
        train_metrics, train_predictions, train_probabilities = predict_rows(encoder, head, dropout, train_encoded, train_labels, device, args.eval_batch_size)
        mbpp_metrics, eval_predictions, eval_probabilities = predict_rows(encoder, head, dropout, eval_encoded, eval_mbpp_labels, device, args.eval_batch_size)
        plus_metrics = binary_metrics(eval_plus_labels, eval_predictions)
        record = {"optimizer_step": step, "training": train_metrics, "evalplus_mbpp": mbpp_metrics, "evalplus_mbpp_plus": plus_metrics}
        metrics_log.append(record)
        with metrics_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record) + "\n")
        with predictions_path.open("w", encoding="utf-8") as handle:
            for split, rows, labels, predictions, probabilities in (
                ("training", train_rows, train_labels, train_predictions, train_probabilities),
                ("evalplus", eval_rows, eval_mbpp_labels, eval_predictions, eval_probabilities),
            ):
                for row, label, prediction, probability in zip(rows, labels, predictions, probabilities, strict=True):
                    handle.write(json.dumps({"optimizer_step": step, "split": split, "task_id": str(row["task_id"]), "label_mbpp": label, "label_mbpp_plus": row.get("label_mbpp_plus"), "prediction": prediction, "positive_probability": probability}) + "\n")
        payload = {"optimizer_step": step}
        payload.update({f"train/{key}": value for key, value in train_metrics.items()})
        payload.update({f"evalplus_mbpp/{key}": value for key, value in mbpp_metrics.items()})
        payload.update({f"evalplus_mbpp_plus/{key}": value for key, value in plus_metrics.items()})
        run.log(payload)
        print(json.dumps(record), flush=True)
        return record

    # Log the untrained baseline before the first classifier update.
    evaluate_and_log(0)
    order = torch.randperm(len(train_rows))
    updates = 0
    training_start = time.time()

    # Shuffle and train for the requested number of epochs with bounded classifier batches.
    for epoch in range(args.epochs):
        if epoch:
            order = torch.randperm(len(train_rows))
        for start in range(0, len(train_rows), args.train_batch_size):
            indexes = order[start:start + args.train_batch_size]
            batch = {key: value[indexes].to(device) for key, value in train_encoded.items()}
            batch_labels = labels_tensor[indexes].to(device)
            encoder.train()
            head.train()
            dropout.train()
            optimizer.zero_grad(set_to_none=True)
            logits = head(dropout(encoder(**batch).last_hidden_state[:, 0]))
            loss = loss_function(logits, batch_labels)
            loss.backward()
            optimizer.step()
            updates += 1
            loss_value = float(loss.detach().cpu())
            with losses_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps({"optimizer_step": updates, "epoch": epoch + 1, "loss": loss_value}) + "\n")
            run.log({"optimizer_step": updates, "train/loss": loss_value, "train/epoch": epoch + 1})
            if updates % args.eval_every_steps == 0:
                record = evaluate_and_log(updates)
                if updates == 100:
                    save_model(output_dir / "checkpoint-100", encoder, tokenizer, head, record)
    if updates % args.eval_every_steps:
        evaluate_and_log(updates)
    save_model(output_dir / "final", encoder, tokenizer, head, metrics_log[-1])
    return {"optimizer_steps": updates, "training_seconds": time.time() - training_start, "final_metrics": metrics_log[-1]}


# Save encoder, tokenizer, classification head, and the matching evaluation record.
def save_model(path: Path, encoder: Any, tokenizer: Any, head: Any, metrics: dict[str, Any]) -> None:
    # Store the same CLS linear-head architecture used by the existing MiniLM router experiments.
    path.mkdir(parents=True, exist_ok=True)
    encoder.save_pretrained(path / "encoder")
    tokenizer.save_pretrained(path / "encoder")
    torch.save(head.state_dict(), path / "classification_head.pt")
    (path / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")


# Stream source tasks in shuffled batches, score one completion per valid task, and save every batch.
def collect_labels(args: argparse.Namespace, output_dir: Path, run: Any, revision: str, cache: sqlite3.Connection, model_fingerprint: str, eval_rows: list[dict[str, Any]]) -> dict[str, Any]:
    # Initialize fresh run artifacts while preserving the cross-run SQLite label cache.
    dataset_path = output_dir / "router_dataset.jsonl"
    excluded_path = output_dir / "excluded_test_suites.jsonl"
    dataset_path.unlink(missing_ok=True)
    excluded_path.unlink(missing_ok=True)
    eval_texts = {normalized_text(row["prompt"]) for row in eval_rows}
    prompt_version = "opencode-coding-assistant-v1"
    stream = load_dataset("nvidia/OpenCodeInstruct", split="train", streaming=True, revision=revision).shuffle(seed=args.seed, buffer_size=args.shuffle_buffer)
    engine, sampler = load_qwen_generator(args.qwen_model, args.gpu_memory_utilization)
    cache_hits = 0
    cache_misses = 0
    valid_tasks = 0
    excluded = 0
    batch_rows: list[dict[str, Any]] = []
    domain_counts: Counter[str] = Counter()
    algorithm_counts: Counter[str] = Counter()
    positive_count = 0
    generation_seconds_total = 0.0
    status_counts: Counter[str] = Counter()
    seen_task_ids: set[str] = set()
    seen_prompt_hashes: set[str] = set()
    run.log({"labeling/stream_started": 1})
    started = time.time()

    # Process each deterministic eight-row source batch before fetching the next batch.
    iterator = iter(stream)
    while valid_tasks + excluded < args.max_source_rows:
        batch_started = time.time()
        generation_seconds = 0.0
        source_batch = []
        for _ in range(min(args.label_batch_size, args.max_source_rows - valid_tasks - excluded)):
            try:
                source_batch.append(next(iterator))
            except StopIteration:
                break
        if not source_batch:
            break
        prepared = []
        for row in source_batch:
            prompt_hash = hashlib.sha256(normalized_text(str(row["input"])).encode("utf-8")).hexdigest()
            task_id = str(row["id"])
            if task_id in seen_task_ids or prompt_hash in seen_prompt_hashes:
                excluded += 1
                with excluded_path.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps({"task_id": task_id, "reason": "duplicate_task_or_prompt"}) + "\n")
                continue
            seen_task_ids.add(task_id)
            seen_prompt_hashes.add(prompt_hash)
            if normalized_text(str(row["input"])) in eval_texts:
                excluded += 1
                with excluded_path.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps({"task_id": row.get("id"), "reason": "held_out_evalplus_prompt_overlap"}) + "\n")
                continue
            try:
                tests = parse_test_list(row["unit_tests"])
                cache_key, fingerprint = make_cache_key(row, revision, model_fingerprint, prompt_version)
            except Exception as error:
                excluded += 1
                with excluded_path.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps({"task_id": row.get("id"), "reason": str(error)[:160]}) + "\n")
                continue
            cached = cache.execute("SELECT completion, label, status, passed_tests, total_tests FROM labels WHERE cache_key=?", (cache_key,)).fetchone()
            if cached:
                completion, label, status, passed_tests, total_tests = cached
                result = {"label": int(label), "status": status, "passed_tests": passed_tests, "total_tests": total_tests}
                cache_hits += 1
            else:
                validation = validate_reference(row, tests, args.test_timeout)
                if not validation["valid"]:
                    excluded += 1
                    with excluded_path.open("a", encoding="utf-8") as handle:
                        handle.write(json.dumps({"task_id": row["id"], "reason": "reference_test_validation", "status": validation["status"], "stderr": validation["stderr"][:600]}) + "\n")
                    continue
                completion = None
                result = None
                cache_misses += 1
            prepared.append({"source": row, "tests": tests, "cache_key": cache_key, "fingerprint": fingerprint, "completion": completion, "result": result})
        misses = [item for item in prepared if item["completion"] is None]
        if misses:
            prompts = [build_coding_prompt(item["source"]["input"]) for item in misses]
            generation_started = time.time()
            completions = generate_batch(engine, sampler, prompts)
            generation_seconds = time.time() - generation_started
            generation_seconds_total += generation_seconds
            for item, completion in zip(misses, completions, strict=True):
                item["completion"] = completion
                item["result"] = label_completion(completion, item["tests"], args.test_timeout)
                cache.execute("INSERT OR REPLACE INTO labels(cache_key, task_id, fingerprint, completion, label, status, passed_tests, total_tests) VALUES(?,?,?,?,?,?,?,?)", (item["cache_key"], str(item["source"]["id"]), item["fingerprint"], completion, item["result"]["label"], item["result"]["status"], item["result"]["passed_tests"], item["result"]["total_tests"]))
        cache.commit()
        with dataset_path.open("a", encoding="utf-8") as handle:
            for item in prepared:
                row = item["source"]
                record = {"task_id": str(row["id"]), "prompt": str(row["input"]), "completion": item["completion"], "label": int(item["result"]["label"]), "label_mbpp": int(item["result"]["label"]), "label_mbpp_plus": None, "status": item["result"]["status"], "passed_tests": item["result"]["passed_tests"], "total_tests": item["result"]["total_tests"], "domain": row.get("domain"), "generation_algorithm": row.get("generation_algorithm"), "source_revision": revision, "cache_key": item["cache_key"]}
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
                valid_tasks += 1
                positive_count += int(item["result"]["label"])
                status_counts[str(item["result"]["status"])] += 1
                domain_counts[str(row.get("domain", "unknown"))] += 1
                algorithm_counts[str(row.get("generation_algorithm", "unknown"))] += 1
        batch_rows.append({"source_rows": len(source_batch), "valid_tasks": len(prepared), "cache_hits": cache_hits, "cache_misses": cache_misses, "positive_labels": sum(item["result"]["label"] for item in prepared), "batch_seconds": time.time() - batch_started, "generation_seconds": generation_seconds})
        run.log({"labeling/source_rows_seen": valid_tasks + excluded, "labeling/valid_tasks": valid_tasks, "labeling/excluded_tasks": excluded, "labeling/cache_hits": cache_hits, "labeling/cache_misses": cache_misses, "labeling/batch_size": len(source_batch), "labeling/batch_index": len(batch_rows), "labeling/positive_total": positive_count, "labeling/generation_seconds": generation_seconds, "labeling/completions_generated": len(misses)})
        print(json.dumps(batch_rows[-1]), flush=True)
        if len(source_batch) < args.label_batch_size:
            break
    del engine
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    summary = {"source_dataset": "nvidia/OpenCodeInstruct", "source_revision": revision, "source_rows_seen": valid_tasks + excluded, "valid_labeled_tasks": valid_tasks, "excluded_tasks": excluded, "cache_hits": cache_hits, "cache_misses": cache_misses, "domain_counts": dict(domain_counts), "generation_algorithm_counts": dict(algorithm_counts), "status_counts": dict(status_counts), "positive_count": positive_count, "generation_seconds": generation_seconds_total, "negative_count": valid_tasks - positive_count, "elapsed_seconds": time.time() - started, "labels_path": str(dataset_path), "cache_path": str(args.cache_path)}
    (output_dir / "label_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


# Run the streamed labeling stage and then train and evaluate MiniLM in one W&B experiment.
def main() -> None:
    # Parse dataset, model, output, training, and evaluation settings for the end-to-end experiment.
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/router-opencode-online-20261013"))
    parser.add_argument("--cache-path", type=Path, default=Path("outputs/router-opencode-online-20261013/opencode_label_cache.sqlite"))
    parser.add_argument("--eval-data", type=Path, default=Path("outputs/router-evalplus-greedy-dual-label-20261013/router_evalplus_labels.jsonl"))
    parser.add_argument("--qwen-model", type=Path, default=Path("outputs/evalplus-pass16-mbpphard10x1009-seed42-20261011/base-model"))
    parser.add_argument("--encoder", default="microsoft/MiniLM-L12-H384-uncased")
    parser.add_argument("--revision", default="")
    parser.add_argument("--max-source-rows", type=int, default=20000)
    parser.add_argument("--shuffle-buffer", type=int, default=10000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--label-batch-size", type=int, default=8)
    parser.add_argument("--train-batch-size", type=int, default=16)
    parser.add_argument("--eval-batch-size", type=int, default=32)
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--eval-every-steps", type=int, default=100)
    parser.add_argument("--max-length", type=int, default=512)
    parser.add_argument("--learning-rate", type=float, default=5e-5)
    parser.add_argument("--test-timeout", type=float, default=5.0)
    parser.add_argument("--gpu-memory-utilization", type=float, default=0.35)
    parser.add_argument("--wandb-project", default="grpo-mbpp")
    parser.add_argument("--wandb-entity", default="kunal-personal")
    parser.add_argument("--run-name", default="router-opencode-online-minilm-20261013")
    args = parser.parse_args()

    # Resolve repository-relative paths and load credentials without exposing secret values.
    root = Path(__file__).resolve().parents[1]
    for name in ("output_dir", "cache_path", "eval_data", "qwen_model"):
        value = getattr(args, name)
        setattr(args, name, value if value.is_absolute() else root / value)
    from dotenv import load_dotenv
    import wandb

    load_dotenv(root / ".env")
    if not os.getenv("WANDB_API_KEY"):
        raise RuntimeError("WANDB_API_KEY is required for online router labeling and training.")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.cache_path.parent.mkdir(parents=True, exist_ok=True)
    eval_rows, eval_mbpp_labels, eval_plus_labels = load_eval_rows(args.eval_data)
    revision = args.revision or HfApi().dataset_info("nvidia/OpenCodeInstruct").sha
    normalize_tokenizer_metadata(args.qwen_model)
    model_fingerprint = checkpoint_fingerprint(args.qwen_model)
    run = wandb.init(entity=args.wandb_entity, project=args.wandb_project, name=args.run_name, job_type="router-opencode-online-training", config={"source_dataset": "nvidia/OpenCodeInstruct", "source_revision": revision, "source_license": "CC-BY-4.0", "max_source_rows": args.max_source_rows, "streaming": True, "selection": "seeded Hugging Face streaming shuffle, selected before Qwen labels, exact task text overlaps with held-out EvalPlus removed", "label_batch_size": args.label_batch_size, "label_rule": "one greedy Qwen completion passes every task test after test-suite validity is checked against the supplied reference answer", "source_status_fields_used_as_labels": False, "qwen_model": str(args.qwen_model), "qwen_config_sha256": model_fingerprint, "decode": {"temperature": 0.0, "top_p": 1.0, "max_tokens": 2048}, "label_cache": str(args.cache_path), "encoder": args.encoder, "epochs": args.epochs, "train_batch_size": args.train_batch_size, "learning_rate": args.learning_rate, "eval_every_steps": args.eval_every_steps, "eval_dataset": str(args.eval_data), "eval_task_count": len(eval_rows), "eval_targets": ["MBPP base pass", "MBPP+ full pass"]})
    run.define_metric("optimizer_step")
    run.define_metric("train/*", step_metric="optimizer_step")
    run.define_metric("evalplus_mbpp/*", step_metric="optimizer_step")
    run.define_metric("evalplus_mbpp_plus/*", step_metric="optimizer_step")
    run.log({"labeling/started": 1})
    cache = open_label_cache(args.cache_path)
    label_summary = collect_labels(args, args.output_dir, run, revision, cache, model_fingerprint, eval_rows)
    cache.close()
    (args.output_dir / "label_summary.json").write_text(json.dumps(label_summary, indent=2) + "\n", encoding="utf-8")
    run.log({"labeling/completed": 1, "labeling/valid_tasks": label_summary["valid_labeled_tasks"], "labeling/excluded_tasks": label_summary["excluded_tasks"], "labeling/cache_hits_total": label_summary["cache_hits"], "labeling/cache_misses_total": label_summary["cache_misses"], "labeling/positive_count": label_summary["positive_count"], "labeling/negative_count": label_summary["negative_count"], "labeling/elapsed_seconds": label_summary["elapsed_seconds"]})
    label_artifact = wandb.Artifact("router-opencodeinstruct-online-labels-20261013", type="dataset")
    for path in (args.output_dir / "router_dataset.jsonl", args.output_dir / "excluded_test_suites.jsonl", args.output_dir / "label_summary.json", args.eval_data):
        if path.exists():
            label_artifact.add_file(str(path))
    run.log_artifact(label_artifact)
    training_summary = train_router(args, args.output_dir, run, eval_rows, eval_mbpp_labels, eval_plus_labels)
    summary = {**label_summary, **training_summary, "experiment": "opencodeinstruct-online-minilm-router", "wandb_run_id": run.id, "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()}
    (args.output_dir / "experiment.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    cache_artifact = wandb.Artifact("router-opencodeinstruct-label-cache-20261013", type="dataset")
    cache_artifact.add_file(str(args.cache_path))
    run.log_artifact(cache_artifact)
    model_artifact = wandb.Artifact("router-opencodeinstruct-minilm-20261013", type="model")
    model_artifact.add_dir(str(args.output_dir / "final"))
    run.log_artifact(model_artifact)
    run.finish()
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == "__main__":
    # Start streamed OpenCodeInstruct labeling and continue automatically into router training.
    main()
