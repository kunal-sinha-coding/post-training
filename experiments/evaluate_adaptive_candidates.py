"""Evaluate initial and final adaptive candidates on MBPP and MBPP+ tests.

The script loads every saved adaptive task artifact, removes the visible assertion
from each candidate, executes the initial and final candidates on canonical MBPP
base and MBPP+ inputs, and writes paired task-level pass rates for comparison.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import signal
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from llm_output_verifier import DATA
from mbpp_input_types import mbpp_deserialize_inputs


# Encode outputs with exact type information for benchmark comparisons.
def encode(value: object) -> object:
    # Preserve primitive, container, and unsupported output types distinctly.
    if value is None or type(value) in (bool, int, str):
        return [type(value).__name__, value]
    if type(value) is float:
        return ["float", value.hex()]
    if type(value) in (list, tuple):
        return [type(value).__name__, [encode(item) for item in value]]
    if type(value) in (set, frozenset):
        return [type(value).__name__, sorted([encode(item) for item in value], key=repr)]
    if type(value) is dict:
        return ["dict", sorted([[encode(key), encode(item)] for key, item in value.items()], key=repr)]
    return ["unsupported", type(value).__name__]


# Remove the visible assertion that generated candidates often include.
def remove_visible_assertion(code: str, assertion: str) -> str:
    # Keep the implementation while avoiding a duplicate visible test execution.
    return "\n".join(line for line in code.splitlines() if line.strip() != assertion.strip())


# Execute one candidate against every input in one benchmark suite.
def run_suite(code: str, entry_point: str, inputs: list[list[object]], expected: list[object]) -> bool:
    # Run the candidate in a fresh namespace and enforce a bounded process alarm.
    signal.setitimer(signal.ITIMER_REAL, 5.0)
    try:
        scope = {"__name__": "candidate"}
        exec(code, scope)
        function = scope[entry_point]
        for arguments, target in zip(inputs, expected):
            value = function(*copy.deepcopy(arguments))
            if encode(value) != target:
                return False
        return True
    except BaseException:
        return False
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)


# Evaluate both paired candidates for one task.
def evaluate_task(job: dict) -> dict:
    # Run initial and final candidates independently on MBPP and MBPP+ suites.
    results = {}
    for variant, candidate in (("initial", job["initial"]), ("final", job["final"])):
        code = remove_visible_assertion(candidate, job["assertion"])
        results[variant] = {
            "base_pass": run_suite(code, job["entry_point"], job["base_inputs"], job["base_expected"]),
            "plus_pass": run_suite(code, job["entry_point"], job["plus_inputs"], job["plus_expected"]),
            "code_sha256": hashlib.sha256(candidate.encode()).hexdigest(),
        }
    return {"task_id": job["task_id"], "results": results}


# Compute canonical outputs for a task without using them during candidate selection.
def canonical_outputs(task: dict, task_id: str, suite: str) -> list[object]:
    # Execute the trusted canonical solution only for the separate benchmark stage.
    scope = {"__name__": "canonical"}
    exec(task["canonical_solution"], scope)
    function = scope[task["entry_point"]]
    inputs = mbpp_deserialize_inputs(task_id, task[suite])
    return [encode(function(*copy.deepcopy(arguments))) for arguments in inputs]


# Aggregate paired task results into MBPP and MBPP+ pass rates.
def aggregate(results: dict[str, dict], task_ids: list[str]) -> dict:
    # Count complete task passes with a fixed denominator across both variants.
    metrics = {}
    for variant in ("initial", "final"):
        metrics[variant] = {}
        for suite in ("base", "plus"):
            field = f"{suite}_pass"
            count = sum(bool(results[task_id]["results"][variant][field]) for task_id in task_ids)
            metrics[variant][f"{suite}_correct"] = count
            metrics[variant][f"{suite}_tasks"] = len(task_ids)
            metrics[variant][f"{suite}_pass_rate"] = count / len(task_ids) if task_ids else 0.0
    metrics["paired_changes"] = {
        suite: sum(
            results[task_id]["results"]["final"][f"{suite}_pass"]
            and not results[task_id]["results"]["initial"][f"{suite}_pass"]
            for task_id in task_ids
        )
        - sum(
            results[task_id]["results"]["initial"][f"{suite}_pass"]
            and not results[task_id]["results"]["final"][f"{suite}_pass"]
            for task_id in task_ids
        )
        for suite in ("base", "plus")
    }
    return metrics


# Load artifacts, run the paired benchmark, and save all task outcomes.
def main() -> None:
    # Parse the adaptive artifact directory and output location.
    parser = argparse.ArgumentParser()
    parser.add_argument("--adaptive-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=32)
    args = parser.parse_args()

    # Build benchmark jobs from the complete EvalPlus MBPP task data.
    tasks = {row["task_id"]: row for row in map(json.loads, DATA.open())}
    jobs = []
    for task_id, task in tasks.items():
        artifact = json.loads((args.adaptive_dir / f"{task_id.replace('/', '_')}.json").read_text())
        records = artifact["records"]
        jobs.append({
            "task_id": task_id,
            "entry_point": task["entry_point"],
            "assertion": artifact["visible_assertion"],
            "initial": records[0]["code"],
            "final": records[-1]["code"],
            "base_inputs": mbpp_deserialize_inputs(task_id, task["base_input"]),
            "base_expected": canonical_outputs(task, task_id, "base_input"),
            "plus_inputs": mbpp_deserialize_inputs(task_id, task["plus_input"]),
            "plus_expected": canonical_outputs(task, task_id, "plus_input"),
        })

    # Evaluate tasks concurrently and preserve every result as it completes.
    results = {}
    with ProcessPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(evaluate_task, job): job["task_id"] for job in jobs}
        for completed, future in enumerate(as_completed(futures), 1):
            task_id = futures[future]
            results[task_id] = future.result()
            if completed % 25 == 0 or completed == len(jobs):
                print(f"Evaluated {completed}/{len(jobs)} tasks", flush=True)

    # Save benchmark results only after candidate generation and selection are complete.
    task_ids = list(tasks)
    artifact = {
        "experiment": "adaptive-qwen3b-mbpp-plus-paired-evaluation",
        "adaptive_artifact": str(args.adaptive_dir),
        "selection_uses_correctness_labels": False,
        "tasks": task_ids,
        "metrics": aggregate(results, task_ids),
        "results": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, indent=2) + "\n")
    print(json.dumps(artifact["metrics"], indent=2), flush=True)


if __name__ == "__main__":
    main()
