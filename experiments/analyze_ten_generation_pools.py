"""Compare saved ten-generation Qwen pools with visible-assertion filtering.

The analysis loads the complete 0.5B evaluator labels and executes every saved 3B candidate against canonical MBPP and MBPP+ inputs. It then computes baseline Pass@K, the first visible-assertion survivor result, first-correct-generation distributions, and the number of generations consumed by the retry-until-visible-pass policy.
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
from llm_output_verifier import DATA, EVAL
from filter_candidates_by_visible_assertion import evaluate_candidate, visible_assertion


# Serialize values with type information so benchmark comparisons are exact.
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


# Compute canonical typed outputs for one task and suite.
def canonical_outputs(task: dict, suite: str) -> list[object] | None:
    signal.signal(signal.SIGALRM, alarm_handler)
    signal.setitimer(signal.ITIMER_REAL, 10.0)
    try:
        scope = {"__name__": "canonical"}
        exec(task["canonical_solution"], scope)
        arguments = mbpp_deserialize_inputs(task["task_id"], task[suite])
        return [encode(scope[task["entry_point"]](*copy.deepcopy(inputs))) for inputs in arguments]
    except BaseException:
        return None
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)


# Evaluate one candidate against the canonical MBPP and MBPP+ suites.
def evaluate_hidden(job: dict) -> dict:
    signal.signal(signal.SIGALRM, alarm_handler)
    result = {"base": [], "plus": []}
    for suite in ("base", "plus"):
        for arguments, expected in zip(job[suite]["inputs"], job[suite]["expected"]):
            signal.setitimer(signal.ITIMER_REAL, 2.0)
            try:
                with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                    scope = {"__name__": "candidate"}
                    exec(job["code"], scope)
                    value = scope[job["entry_point"]](*copy.deepcopy(arguments))
                result[suite].append("pass" if encode(value) == expected else "fail")
            except BaseException:
                result[suite].append("error")
            finally:
                signal.setitimer(signal.ITIMER_REAL, 0)
    result["base_pass"] = all(status == "pass" for status in result["base"])
    result["plus_pass"] = all(status == "pass" for status in result["plus"])
    return result


# Load ten saved programs for one model and build canonical evaluation jobs.
def load_jobs(model_dir: Path, tasks: dict[str, dict]) -> dict[str, list[dict]]:
    jobs = {}
    for task_id, task in tasks.items():
        candidate_dir = model_dir / "mbpp" / "qwen2_chat_temp_0.2" / task_id.replace("/", "_")
        codes = [(candidate_dir / f"{index}.py").read_text() for index in range(10)]
        base_inputs = mbpp_deserialize_inputs(task_id, task["base_input"])
        plus_inputs = mbpp_deserialize_inputs(task_id, task["plus_input"])
        base_expected = canonical_outputs(task, "base_input")
        plus_expected = canonical_outputs(task, "plus_input")
        if base_expected is None or plus_expected is None:
            continue
        jobs[task_id] = [
            {
                "task_id": task_id,
                "entry_point": task["entry_point"],
                "code": code,
                "visible_assertion": visible_assertion(task["prompt"]),
                "base": {"inputs": base_inputs, "expected": base_expected},
                "plus": {"inputs": plus_inputs, "expected": plus_expected},
            }
            for code in codes
        ]
    return jobs


# Compute all requested metrics from candidate labels and visible-filter outcomes.
def summarize(task_ids: list[str], labels: dict[str, list[dict]], visible: dict[str, list[bool]]) -> dict:
    metrics = {}
    for suite, field in (("mbpp", "base_pass"), ("mbpp_plus", "plus_pass")):
        curves = {}
        first_correct = {str(index): 0 for index in range(1, 11)}
        first_correct["never"] = 0
        for k in range(1, 11):
            curves[f"pass_at_{k}"] = sum(any(row[field] for row in labels[task_id][:k]) for task_id in task_ids) / len(task_ids)
        filtered_hits = 0
        for task_id in task_ids:
            correct_index = next((index + 1 for index, row in enumerate(labels[task_id]) if row[field]), None)
            first_correct[str(correct_index) if correct_index is not None else "never"] += 1
            survivor = next((index for index, passed in enumerate(visible[task_id]) if passed), None)
            if survivor is not None and labels[task_id][survivor][field]:
                filtered_hits += 1
        metrics[suite] = {
            "baseline_pass_at_k": curves,
            "filtered_first_visible_pass_at_1": filtered_hits / len(task_ids),
            "first_correct_generation_distribution": first_correct,
        }
    attempts = {task_id: next((index + 1 for index, passed in enumerate(visible[task_id]) if passed), 10) for task_id in task_ids}
    metrics["generation_budget"] = {
        "total_generations": sum(attempts.values()),
        "average_generations_per_task": sum(attempts.values()) / len(task_ids),
        "attempt_count_distribution": {str(index): sum(value == index for value in attempts.values()) for index in range(1, 11)},
    }
    return metrics


# Analyze both saved model pools and persist the complete comparison artifact.
def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--three-b-model-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=32)
    args = parser.parse_args()
    tasks = {row["task_id"]: row for row in map(json.loads, DATA.open())}
    task_ids = list(tasks)
    old_eval = json.loads(EVAL.read_text())["eval"]
    old_visible = json.loads(Path("outputs/qwen-evalplus-full-10-temp02/visible-assertion-filter-399.json").read_text())["results"]
    labels_by_model = {
        "0.5B": {
            task_id: [
                {"base_pass": row["base_status"] == "pass", "plus_pass": row["plus_status"] == "pass"}
                for row in old_eval[task_id]
            ]
            for task_id in task_ids
        }
    }
    visible_by_model = {}
    for model_name, model_dir in [("0.5B", Path("outputs/qwen-evalplus-full-10-temp02/mbpp/qwen2_chat_temp_0.2")), ("3B", args.three_b_model_dir)]:
        if model_name == "0.5B":
            visible_by_model[model_name] = {task_id: [index in old_visible[task_id]["survivor_indices"] for index in range(10)] for task_id in task_ids}
            continue
        jobs_by_task = load_jobs(model_dir, tasks)
        task_ids = [task_id for task_id in task_ids if task_id in jobs_by_task]
        labels_by_model[model_name] = {task_id: [None] * 10 for task_id in task_ids}
        visible_by_model[model_name] = {task_id: [False] * 10 for task_id in task_ids}
        jobs = [(task_id, index, job) for task_id in task_ids for index, job in enumerate(jobs_by_task[task_id])]
        with concurrent.futures.ProcessPoolExecutor(max_workers=args.workers) as executor:
            futures = {executor.submit(evaluate_hidden, job): (task_id, index) for task_id, index, job in jobs}
            for completed, future in enumerate(concurrent.futures.as_completed(futures), 1):
                task_id, index = futures[future]
                labels_by_model[model_name][task_id][index] = future.result()
                if completed % 100 == 0 or completed == len(jobs):
                    print(f"3B evaluated {completed}/{len(jobs)} candidates", flush=True)
        filter_artifact = json.loads((model_dir / "visible-assertion-filter-evaluation.json").read_text())
        for task_id in task_ids:
            survivor_indices = set(filter_artifact["results"][task_id]["survivor_indices"])
            visible_by_model[model_name][task_id] = [index in survivor_indices for index in range(10)]
    report = {
        "experiment": "ten-generation-baseline-versus-visible-assertion-filter",
        "tasks": len(task_ids),
        "models": {model: summarize(task_ids, labels_by_model[model], visible_by_model[model]) for model in labels_by_model},
        "selection_uses_correctness_labels": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
