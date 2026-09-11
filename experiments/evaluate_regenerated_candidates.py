"""Filter and evaluate a regenerated Qwen candidate pool.

The script executes each regenerated candidate on the prompt-visible assertion,
retains passing candidates in original order, evaluates the first survivor
against canonical MBPP and MBPP+ outputs, and saves every verdict and metric
without using benchmark labels during filtering or selection.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import contextlib
import copy
import hashlib
import io
import json
import signal
from pathlib import Path

from mbpp_input_types import mbpp_deserialize_inputs
from llm_output_verifier import DATA


# Serialize returned values with stable type tags for exact comparison.
def encode(value: object) -> object:
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


# Raise a bounded execution exception for a candidate that does not terminate.
def alarm_handler(signum: int, frame: object) -> None:
    raise TimeoutError("Candidate execution timed out.")


# Execute one candidate on the visible assertion and all hidden benchmark inputs.
def evaluate_candidate(job: dict) -> dict:
    signal.signal(signal.SIGALRM, alarm_handler)
    verdict = {"visible": "fail", "base": [], "plus": []}
    try:
        signal.setitimer(signal.ITIMER_REAL, 2.0)
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            scope = {"__name__": "candidate"}
            exec(job["code"], scope)
            exec(job["visible_assertion"], scope)
        verdict["visible"] = "pass"
    except BaseException as error:
        verdict["visible_error"] = type(error).__name__
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
    if verdict["visible"] != "pass":
        return verdict
    # Skip hidden-suite execution for candidates that are not selected.
    if job.get("visible_only", False):
        return verdict
    for suite in ("base", "plus"):
        for arguments, expected in zip(job[suite]["inputs"], job[suite]["expected"]):
            signal.setitimer(signal.ITIMER_REAL, 2.0)
            try:
                with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                    scope = {"__name__": "candidate"}
                    exec(job["code"], scope)
                    value = scope[job["entry_point"]](*copy.deepcopy(arguments))
                verdict[suite].append({"status": "pass" if encode(value) == expected else "fail", "value": encode(value)})
            except BaseException as error:
                verdict[suite].append({"status": "error", "error_type": type(error).__name__})
            finally:
                signal.setitimer(signal.ITIMER_REAL, 0)
    return verdict


# Compute canonical typed outputs for one task without joining candidate labels.
def canonical_outputs(task: dict, suite: str) -> list[object]:
    scope = {"__name__": "canonical"}
    exec(task["canonical_solution"], scope)
    arguments = mbpp_deserialize_inputs(task["task_id"], task[suite])
    function = scope[task["entry_point"]]
    return [encode(function(*copy.deepcopy(inputs))) for inputs in arguments]


# Evaluate all ten candidates for one task and preserve their source hashes.
def evaluate_task(job: dict) -> dict:
    verdicts = [evaluate_candidate({**job, "code": candidate, "visible_only": True}) for candidate in job["candidates"]]
    survivors = [index for index, verdict in enumerate(verdicts) if verdict["visible"] == "pass"]
    first = survivors[0] if survivors else None
    selected = evaluate_candidate({**job, "code": job["candidates"][first]}) if first is not None else None
    if first is not None:
        verdicts[first] = selected
    return {
        "task_id": job["task_id"],
        "candidate_code_sha256": [hashlib.sha256(candidate.encode()).hexdigest() for candidate in job["candidates"]],
        "verdicts": verdicts,
        "survivor_indices": survivors,
        "first_survivor": first,
        "selected_base_pass": bool(selected) and all(row["status"] == "pass" for row in selected["base"]),
        "selected_plus_pass": bool(selected) and all(row["status"] == "pass" for row in selected["plus"]),
    }


# Run the regenerated pool in parallel and save the complete selection artifact.
def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidates", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=32)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    tasks = {row["task_id"]: row for row in map(json.loads, DATA.open())}
    jobs = []
    task_ids = list(tasks)
    for task_id in task_ids:
        task = tasks[task_id]
        candidate_dir = args.candidates / "mbpp" / "qwen2_chat_temp_0.2" / task_id.replace("/", "_")
        candidates = [(candidate_dir / f"{index}.py").read_text() for index in range(10)]
        visible = next(line.strip() for line in task["prompt"].splitlines() if line.strip().startswith("assert "))
        jobs.append({
            "task_id": task_id,
            "entry_point": task["entry_point"],
            "visible_assertion": visible,
            "candidates": candidates,
            "base": {"inputs": mbpp_deserialize_inputs(task_id, task["base_input"]), "expected": canonical_outputs(task, "base_input")},
            "plus": {"inputs": mbpp_deserialize_inputs(task_id, task["plus_input"]), "expected": canonical_outputs(task, "plus_input")},
        })
    results = {}
    with concurrent.futures.ProcessPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(evaluate_task, job): job["task_id"] for job in jobs}
        for completed, future in enumerate(concurrent.futures.as_completed(futures), 1):
            task_id = futures[future]
            results[task_id] = future.result()
            if completed % 25 == 0 or completed == len(task_ids):
                print(f"Evaluated {completed}/{len(task_ids)} tasks", flush=True)
    selected = [results[task_id] for task_id in task_ids if results[task_id]["first_survivor"] is not None]
    artifact = {
        "experiment": "regenerated-candidate-visible-assertion-filter",
        "candidate_artifact": str(args.candidates),
        "selection": "First candidate passing the visible prompt assertion in original order.",
        "selection_uses_correctness_labels": False,
        "tasks": task_ids,
        "tasks_with_survivors": len(selected),
        "tasks_without_survivors": len(task_ids) - len(selected),
        "base_selected_correct": sum(row["selected_base_pass"] for row in results.values()),
        "plus_selected_correct": sum(row["selected_plus_pass"] for row in results.values()),
        "base_accuracy_full_suite": sum(row["selected_base_pass"] for row in results.values()) / len(task_ids),
        "plus_accuracy_full_suite": sum(row["selected_plus_pass"] for row in results.values()) / len(task_ids),
        "base_accuracy_conditional": sum(row["selected_base_pass"] for row in selected) / len(selected) if selected else 0.0,
        "plus_accuracy_conditional": sum(row["selected_plus_pass"] for row in selected) / len(selected) if selected else 0.0,
        "results": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, indent=2) + "\n")
    print(json.dumps({key: artifact[key] for key in ("tasks_with_survivors", "tasks_without_survivors", "base_accuracy_full_suite", "plus_accuracy_full_suite", "base_accuracy_conditional", "plus_accuracy_conditional")}, indent=2))


if __name__ == "__main__":
    main()
