"""Run saved MBPP generations, persist runtime outcomes, and evaluate reranking curves.

The script loads the existing ten candidates and EvalPlus inputs, runs each candidate
once in a bounded subprocess, writes per-input runtime outcomes, and computes the
requested answer-independent ordering strategies using saved correctness only after
selection for post-selection metrics.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path


# Resolve one candidate directory and its stored EvalPlus input record.
def _run_candidate(job: tuple[str, str, dict, int, float]) -> dict:
    task_id, code, task, candidate_index, timeout = job
    cases = list(task["base_input"])
    plus_cases = list(task["plus_input"])
    payload = {"task_id": task_id, "candidate_index": candidate_index}
    harness = r'''
import contextlib
import io
import signal
import time

def _call(args, entry, timeout):
    # Bound each function call so one candidate cannot stall the full scan.
    def alarm(_signum, _frame):
        raise TimeoutError("call timeout")
    old = signal.signal(signal.SIGALRM, alarm)
    signal.setitimer(signal.ITIMER_REAL, timeout)
    output = io.StringIO()
    error = io.StringIO()
    started = time.monotonic()
    try:
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(error):
            result = entry(*args)
        return {"executed": True, "status": "returned", "elapsed_seconds": time.monotonic() - started,
                "stdout_length": len(output.getvalue()), "stderr_length": len(error.getvalue()),
                "output_type": type(result).__name__}
    except BaseException as exc:
        return {"executed": False, "status": type(exc).__name__, "elapsed_seconds": time.monotonic() - started,
                "stdout_length": len(output.getvalue()), "stderr_length": len(error.getvalue())}
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old)

def _main():
    # Execute all standard and extended inputs while ignoring returned values.
    cases = json.loads(INPUTS)
    entry = globals()[ENTRY]
    results = []
    for suite, inputs in (("base", cases["base"]), ("plus", cases["plus"])):
        for index, args in enumerate(inputs):
            results.append({"suite": suite, "input_index": index, **_call(args, entry, CALL_TIMEOUT)})
    print(json.dumps(results, separators=(",", ":")))

_main()
'''
    inputs = json.dumps({"base": cases, "plus": plus_cases}, separators=(",", ":"))
    entry = task["entry_point"]
    script = code + "\n" + "ENTRY = " + repr(entry) + "\n" + "INPUTS = " + repr(inputs) + "\nCALL_TIMEOUT = " + repr(timeout) + "\n" + harness
    started = time.monotonic()
    try:
        completed = subprocess.run(
            [sys.executable, "-I", "-c", script],
            capture_output=True,
            text=True,
            timeout=max(10.0, timeout * max(1, len(cases) + len(plus_cases)) + 2.0),
            env={"PATH": os.environ.get("PATH", ""), "PYTHONIOENCODING": "utf-8"},
        )
        lines = completed.stdout.strip().splitlines()
        details = json.loads(lines[-1]) if lines else []
        return {**payload, "process_status": "completed" if completed.returncode == 0 else "process_error",
                "returncode": completed.returncode, "elapsed_seconds": time.monotonic() - started,
                "tests": details, "stderr": completed.stderr[-2000:]}
    except subprocess.TimeoutExpired as exc:
        return {**payload, "process_status": "process_timeout", "returncode": None,
                "elapsed_seconds": time.monotonic() - started, "tests": [],
                "stderr": str(exc)[:2000]}


# Load tasks, candidates, and saved correctness labels in stable generation order.
def _load_jobs(root: Path, data_path: Path, eval_path: Path, timeout: float) -> tuple[list[dict], dict]:
    tasks = {row["task_id"]: row for row in map(json.loads, data_path.open())}
    evaluations = json.load(eval_path.open())["eval"]
    jobs = []
    for task_id in sorted(evaluations):
        task_dir = root / task_id.replace("/", "_")
        for candidate_index, row in enumerate(evaluations[task_id]):
            jobs.append((task_id, (task_dir / f"{candidate_index}.py").read_text(), tasks[task_id], candidate_index, timeout))
    return jobs, evaluations


# Convert runtime outcomes into candidate-level filter and coverage fields.
def _summarize(rows: list[dict], evaluations: dict) -> dict:
    by_task = {}
    for row in rows:
        tests = row["tests"]
        base = [x for x in tests if x["suite"] == "base"]
        plus = [x for x in tests if x["suite"] == "plus"]
        item = {"task_id": row["task_id"], "candidate_index": row["candidate_index"],
                "base_executed": sum(x["executed"] for x in base), "base_total": len(base),
                "plus_executed": sum(x["executed"] for x in plus), "plus_total": len(plus),
                "all_base_executed": bool(base) and all(x["executed"] for x in base),
                "all_plus_executed": bool(plus) and all(x["executed"] for x in plus),
                "execution_fraction": sum(x["executed"] for x in tests) / len(tests) if tests else 0.0,
                "correct": evaluations[row["task_id"]][row["candidate_index"]]["base_status"] == "pass",
                "plus_correct": evaluations[row["task_id"]][row["candidate_index"]]["plus_status"] == "pass"}
        by_task.setdefault(row["task_id"], []).append(item)
    return by_task


# Build each ordering with deterministic random tie breaks from a fixed seed.
def _order(task_rows: list[dict], strategy: str, seed: int) -> list[dict]:
    import random
    rng = random.Random(seed + hash(task_rows[0]["task_id"]) % 1000003)
    if strategy == "baseline":
        return sorted(task_rows, key=lambda x: x["candidate_index"])
    if strategy == "mbpp_filter":
        pool = [x for x in task_rows if x["all_base_executed"]] or task_rows
        return sorted(pool, key=lambda x: rng.random())
    if strategy == "mbpp_plus_filter":
        pool = [x for x in task_rows if x["all_plus_executed"]] or task_rows
        return sorted(pool, key=lambda x: rng.random())
    if strategy == "plus_then_mbpp":
        plus = [x for x in task_rows if x["all_plus_executed"]]
        pool = plus or [x for x in task_rows if x["all_base_executed"]] or task_rows
        return sorted(pool, key=lambda x: rng.random())
    if strategy == "plus_then_first":
        pool = [x for x in task_rows if x["all_plus_executed"]]
        return sorted(pool, key=lambda x: rng.random()) if pool else [min(task_rows, key=lambda x: x["candidate_index"])]
    if strategy == "mbpp_then_first":
        pool = [x for x in task_rows if x["all_base_executed"]]
        return sorted(pool, key=lambda x: rng.random()) if pool else [min(task_rows, key=lambda x: x["candidate_index"])]
    if strategy == "max_execution":
        maximum = max(x["execution_fraction"] for x in task_rows)
        pool = [x for x in task_rows if x["execution_fraction"] == maximum]
        return sorted(pool, key=lambda x: rng.random())
    raise ValueError(strategy)


# Calculate empirical post-selection Pass@K over the ordered candidate prefixes.
def _metrics(by_task: dict, seed: int) -> dict:
    strategies = ["baseline", "mbpp_filter", "mbpp_plus_filter", "plus_then_mbpp", "plus_then_first", "mbpp_then_first", "max_execution"]
    result = {}
    for strategy in strategies:
        curves = {}
        selected = {}
        for k in range(1, 11):
            hits = 0
            for task_id, rows in by_task.items():
                order = _order(rows, strategy, seed)
                selected[task_id] = order
                hits += any(x["correct"] for x in order[:k])
            curves[f"pass_at_{k}"] = hits / len(by_task)
        result[strategy] = curves
    return result


# Run the scan and write both detailed runtime records and reproducible metrics.
def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--eval", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=16)
    parser.add_argument("--timeout", type=float, default=3.0)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    jobs, evaluations = _load_jobs(args.root, args.data, args.eval, args.timeout)
    with concurrent.futures.ProcessPoolExecutor(max_workers=args.workers) as executor:
        rows = list(executor.map(_run_candidate, jobs, chunksize=1))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w") as handle:
        for row in rows:
            handle.write(json.dumps(row, separators=(",", ":")) + "\n")
    by_task = _summarize(rows, evaluations)
    metrics = _metrics(by_task, args.seed)
    artifact_hash = hashlib.sha256(args.output.read_bytes()).hexdigest()
    summary = {"tasks": len(by_task), "candidates": len(rows), "workers": args.workers,
               "per_call_timeout_seconds": args.timeout, "seed": args.seed,
               "runtime_artifact": str(args.output), "runtime_artifact_sha256": artifact_hash,
               "metrics": metrics, "candidate_summary": {task: rows for task, rows in by_task.items()}}
    args.summary.write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({"tasks": len(by_task), "candidates": len(rows), "runtime_artifact_sha256": artifact_hash, "metrics": metrics}, indent=2))


if __name__ == "__main__":
    main()
