"""Ask an LLM for standard-test answers across the full EvalPlus suite.

The script loads saved EvalPlus tasks and candidate observations, sends only
the task prompt and all stored base tests to GPT-5 mini, parses and caches the
predicted answers, executes the trusted canonical solution for ground truth,
and reports per-test and per-task prediction accuracy.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import math
import os
from pathlib import Path

from llm_output_verifier import DATA, EVAL, OBS
from mbpp_input_types import mbpp_deserialize_inputs


# Build the answer-prediction prompt from only the task and standard tests.
def build_prompt(task: dict) -> str:
    tests = [{"test_index": index, "inputs": inputs} for index, inputs in enumerate(task["base_input"])]
    return (
        "Solve the following Python programming task mentally. "
        "For each supplied standard test input, predict the exact returned value of the requested function. "
        "Do not write code and do not use any hidden tests. "
        "Return only JSON with a predictions array containing one object per test. "
        "Each object must have test_index and value.\n\n"
        f"TASK:\n{task['prompt']}\n\n"
        f"ENTRY POINT: {task['entry_point']}\n\n"
        f"STANDARD TESTS:\n{json.dumps(tests, ensure_ascii=False)}"
    )


# Parse the model response into one prediction object per standard test.
def parse_response(text: str, count: int) -> list[dict]:
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        value = json.loads(text[start:end + 1])
    predictions = value["predictions"]
    if len(predictions) != count:
        raise ValueError(f"Expected {count} predictions, received {len(predictions)}.")
    return predictions


# Query one task and preserve both the prompt and raw model response.
def predict(client: object, model: str, task_id: str, task: dict) -> dict:
    prompt = build_prompt(task)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "Predict the exact outputs for the supplied standard tests."},
            {"role": "user", "content": prompt},
        ],
    )
    raw = response.choices[0].message.content or ""
    return {"task_id": task_id, "prompt": prompt, "raw_response": raw, "predictions": parse_response(raw, len(task["base_input"]))}


# Encode native JSON values in the saved typed observation representation.
def encode(value: object) -> list:
    if value is None or type(value) in (bool, int, str):
        return [type(value).__name__, value]
    if type(value) is float:
        return ["float", value.hex()]
    if type(value) is list:
        return ["list", [encode(item) for item in value]]
    if type(value) is dict:
        return ["dict", [[encode(key), encode(item)] for key, item in sorted(value.items(), key=repr)]]
    if type(value) is tuple:
        return ["tuple", [encode(item) for item in value]]
    if type(value) in (set, frozenset):
        return [type(value).__name__, sorted([encode(item) for item in value], key=repr)]
    return ["unsupported", type(value).__name__]


# Execute the trusted canonical implementation on the three standard inputs.
def ground_truth(task_id: str, task: dict) -> list[object]:
    scope = {"__name__": "canonical"}
    exec(task["canonical_solution"], scope)
    function = scope[task["entry_point"]]
    inputs = mbpp_deserialize_inputs(task_id, task["base_input"])
    return [function(*arguments) for arguments in inputs]


# Compare a JSON prediction with a canonical value using the task tolerance.
def values_match(expected: object, predicted: object, atol: float) -> bool:
    if isinstance(expected, (int, float)) and not isinstance(expected, bool) and isinstance(predicted, (int, float)) and not isinstance(predicted, bool):
        return math.isclose(float(expected), float(predicted), abs_tol=atol, rel_tol=1e-6)
    if type(expected) is not type(predicted):
        if isinstance(expected, tuple) and isinstance(predicted, list):
            return all(values_match(left, right, atol) for left, right in zip(expected, predicted)) and len(expected) == len(predicted)
        return False
    if isinstance(expected, (list, tuple)):
        return len(expected) == len(predicted) and all(values_match(left, right, atol) for left, right in zip(expected, predicted))
    if isinstance(expected, (set, frozenset)):
        return expected == set(predicted)
    if isinstance(expected, dict):
        return expected.keys() == predicted.keys() and all(values_match(expected[key], predicted[key], atol) for key in expected)
    return expected == predicted


# Compare JSON predictions with the saved typed output representations.
def matching_candidates(task_id: str, predictions: list[dict], evaluations: dict) -> list[int]:
    expected = {item["test_index"]: json.dumps(encode(item["value"]), separators=(",", ":")) for item in predictions}
    matches = []
    for index in range(len(evaluations[task_id])):
        observation = json.loads((OBS / f"{task_id.replace('/', '_')}_{index}.json").read_text())
        candidate = {}
        for row in observation["tests"]:
            if row["suite"] == "base_input":
                candidate[row["index"]] = row.get("value")
        if all(candidate.get(index) == value for index, value in expected.items()):
            matches.append(index)
    return matches


# Compute prediction accuracy after joining canonical outputs and no selection labels.
def metrics(task_ids: list[str], rows: dict[str, dict], data: dict[str, dict]) -> dict:
    test_correct = 0
    test_total = 0
    task_correct = 0
    task_total = 0
    per_task = {}
    for task_id in task_ids:
        task = data[task_id]
        expected = ground_truth(task_id, task)
        predictions = {item["test_index"]: item["value"] for item in rows[task_id]["predictions"]}
        correctness = [values_match(value, predictions.get(index), task["atol"]) for index, value in enumerate(expected)]
        test_correct += sum(correctness)
        test_total += len(correctness)
        task_correct += all(correctness)
        task_total += 1
        per_task[task_id] = {
            "test_correct": sum(correctness),
            "test_total": len(correctness),
            "all_tests_correct": all(correctness),
            "ground_truth": [encode(value) for value in expected],
            "predictions": rows[task_id]["predictions"],
            "test_correctness": correctness,
        }
    return {
        "test_accuracy": test_correct / test_total if test_total else 0.0,
        "test_correct": test_correct,
        "test_total": test_total,
        "task_accuracy": task_correct / task_total if task_total else 0.0,
        "tasks_all_correct": task_correct,
        "tasks_total": task_total,
        "per_task": per_task,
    }


# Detect API rate limiting without treating ordinary task failures as capacity errors.
def is_rate_limit(error: BaseException) -> bool:
    return getattr(error, "status_code", None) == 429 or "rate limit" in str(error).lower()


# Run uncached requests with adaptive concurrency and persist each success immediately.
def run_requests(task_ids: list[str], data: dict[str, dict], evaluations: dict, client: object, model: str, output: Path, results: dict[str, dict], workers: int) -> None:
    while True:
        pending = [task_id for task_id in task_ids if task_id not in results]
        if not pending:
            return
        limited = False
        failures = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(predict, client, model, task_id, data[task_id]): task_id
                for task_id in pending
            }
            for future in concurrent.futures.as_completed(futures):
                task_id = futures[future]
                try:
                    results[task_id] = future.result()
                    output.write_text(json.dumps({"model": model, "results": results}, indent=2) + "\n")
                    print(f"Predicted {len(results)}/{len(task_ids)}: {task_id}", flush=True)
                except BaseException as error:
                    if is_rate_limit(error):
                        limited = True
                    else:
                        failures.append((task_id, repr(error)))
        if limited:
            workers = max(1, workers // 2)
            print(f"Rate limited. Retrying uncached tasks with {workers} workers.", flush=True)
            continue
        if failures:
            raise RuntimeError("Prediction failures: " + repr(failures))


# Run the full suite or a bounded preview and save predictions and ground truth.
def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tasks", type=int, default=399)
    parser.add_argument("--model", default="gpt-5-mini")
    parser.add_argument("--workers", type=int, default=32)
    parser.add_argument("--output", type=Path, default=Path("outputs/qwen-evalplus-full-10-temp02/llm-test-answer-predictions-399.json"))
    args = parser.parse_args()
    from openai import OpenAI

    data = {row["task_id"]: row for row in map(json.loads, DATA.open())}
    evaluations = json.loads(EVAL.read_text())["eval"]
    task_ids = list(evaluations)[:args.tasks]
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    cached = json.loads(args.output.read_text()) if args.output.exists() else {"results": {}}
    results = cached.get("results", {})
    run_requests(task_ids, data, evaluations, client, args.model, args.output, results, args.workers)
    for task_id in task_ids:
        results[task_id]["matching_candidate_indices"] = matching_candidates(task_id, results[task_id]["predictions"], evaluations)
    report = {
        "experiment": "llm-standard-test-answer-prediction-evalplus",
        "model": args.model,
        "tasks": task_ids,
        "prompt_condition": "Raw MBPP task prompt plus all stored standard base inputs.",
        "results": results,
        "metrics": metrics(task_ids, results, data),
    }
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: value for key, value in report["metrics"].items() if key != "per_task"}, indent=2))


if __name__ == "__main__":
    main()
