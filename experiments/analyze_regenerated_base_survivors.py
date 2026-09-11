"""Analyze MBPP correctness retention after visible-assertion filtering.

The script evaluates every visible-assertion survivor in a subprocess with a
hard timeout, identifies tasks where filtering removed all correct candidates,
and measures incorrect first-survivor choices among tasks with multiple
survivors.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import copy
import json
import subprocess
import sys
from pathlib import Path

from mbpp_input_types import mbpp_deserialize_inputs
from llm_output_verifier import DATA


# Serialize values with stable type tags for exact MBPP comparison.
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


# Execute one candidate in a fresh subprocess with a hard wall-clock timeout.
def run_candidate(job: dict) -> dict:
    child = (
        "import contextlib, io, json, sys\n"
        "def encode(v):\n"
        "    if v is None or type(v) in (bool,int,str): return [type(v).__name__,v]\n"
        "    if type(v) is float: return ['float',v.hex()]\n"
        "    if type(v) in (list,tuple): return [type(v).__name__,[encode(x) for x in v]]\n"
        "    if type(v) in (set,frozenset): return [type(v).__name__,sorted([encode(x) for x in v],key=repr)]\n"
        "    if type(v) is dict: return ['dict',sorted([[encode(k),encode(x)] for k,x in v.items()],key=repr)]\n"
        "    return ['unsupported',type(v).__name__]\n"
        "j=json.loads(sys.stdin.read()); out=[]\n"
        "try:\n"
        "  with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):\n"
        "    scope={'__name__':'candidate'}; exec(j['code'],scope); f=scope[j['entry_point']]\n"
        "    for args in j['inputs']: out.append(encode(f(*args)))\n"
        "  print(json.dumps({'outputs':out}))\n"
        "except BaseException as e: print(json.dumps({'error':type(e).__name__}))\n"
    )
    try:
        completed = subprocess.run([sys.executable, "-I", "-c", child], input=json.dumps(job).encode(), stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=5)
        value = json.loads(completed.stdout.decode().splitlines()[-1]) if completed.stdout else {}
        outputs = value.get("outputs", [])
        return {"all_correct": outputs == job["expected"], "test_correct": sum(left == right for left, right in zip(outputs, job["expected"])), "test_total": len(job["expected"])}
    except BaseException:
        return {"all_correct": False, "test_correct": 0, "test_total": len(job["expected"])}


# Compute canonical MBPP outputs without using candidate correctness labels.
def canonical_outputs(task: dict) -> tuple[list, list]:
    scope = {"__name__": "canonical"}
    exec(task["canonical_solution"], scope)
    inputs = mbpp_deserialize_inputs(task["task_id"], task["base_input"])
    function = scope[task["entry_point"]]
    return inputs, [encode(function(*copy.deepcopy(args))) for args in inputs]


# Summarize filter false negatives and incorrect first-survivor choices.
def summarize(results: dict[str, dict], survivor_map: dict[str, list[int]]) -> dict:
    nonempty = [task_id for task_id, indices in survivor_map.items() if indices]
    multi = [task_id for task_id in nonempty if len(survivor_map[task_id]) > 1]
    false_negative = [task_id for task_id in nonempty if not any(results[task_id][str(index)]["all_correct"] for index in survivor_map[task_id])]
    tie_with_correct = [task_id for task_id in multi if any(results[task_id][str(index)]["all_correct"] for index in survivor_map[task_id])]
    incorrect_tie = [task_id for task_id in tie_with_correct if not results[task_id][str(survivor_map[task_id][0])]["all_correct"]]
    selected_correct = [task_id for task_id in nonempty if results[task_id][str(survivor_map[task_id][0])]["all_correct"]]
    return {
        "tasks_with_survivors": len(nonempty),
        "multi_survivor_tasks": len(multi),
        "filter_removed_all_correct_candidates": len(false_negative),
        "filter_false_negative_rate": len(false_negative) / len(nonempty) if nonempty else 0.0,
        "multi_survivor_tasks_with_correct_candidate": len(tie_with_correct),
        "incorrect_first_survivor_tie_breaks": len(incorrect_tie),
        "incorrect_tie_break_rate_among_multi_with_correct": len(incorrect_tie) / len(tie_with_correct) if tie_with_correct else 0.0,
        "incorrect_tie_break_rate_among_all_multi": len(incorrect_tie) / len(multi) if multi else 0.0,
        "first_survivor_correct": len(selected_correct),
        "first_survivor_accuracy_conditional": len(selected_correct) / len(nonempty) if nonempty else 0.0,
        "filter_false_negative_task_ids": false_negative,
        "incorrect_tie_break_task_ids": incorrect_tie,
    }


# Run bounded survivor evaluations in parallel and save the diagnostic report.
def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidates", type=Path, required=True)
    parser.add_argument("--filter-evaluation", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=32)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    tasks = {row["task_id"]: row for row in map(json.loads, DATA.open())}
    filtered = json.loads(args.filter_evaluation.read_text())
    survivor_map = {task_id: filtered["results"][task_id]["survivor_indices"] for task_id in filtered["tasks"]}
    pending = []
    results = {task_id: {} for task_id in survivor_map}
    for task_id, indices in survivor_map.items():
        inputs, expected = canonical_outputs(tasks[task_id])
        directory = args.candidates / "mbpp" / "qwen2_chat_temp_0.2" / task_id.replace("/", "_")
        for index in indices:
            pending.append((task_id, index, {"code": (directory / f"{index}.py").read_text(), "entry_point": tasks[task_id]["entry_point"], "inputs": inputs, "expected": expected}))
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(run_candidate, job): (task_id, index) for task_id, index, job in pending}
        for completed, future in enumerate(concurrent.futures.as_completed(futures), 1):
            task_id, index = futures[future]
            results[task_id][str(index)] = future.result()
            if completed % 100 == 0 or completed == len(pending):
                print(f"Evaluated {completed}/{len(pending)} survivors", flush=True)
    report = {
        "experiment": "regenerated-base-survivor-correctness-analysis",
        "candidate_artifact": str(args.candidates),
        "filter_evaluation_artifact": str(args.filter_evaluation),
        "selection_uses_correctness_labels": False,
        "survivor_count": len(pending),
        "metrics": summarize(results, survivor_map),
        "results": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report["metrics"], indent=2))


if __name__ == "__main__":
    main()
