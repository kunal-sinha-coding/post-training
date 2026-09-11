"""Ask an LLM for standard-test answers and compare them with saved candidates.

The script loads saved EvalPlus tasks and candidate observations, sends only
the task prompt and three base tests to GPT-5 mini, parses the predicted
answers, and reports which saved candidates exactly match those predictions.
It is intended for a small preview before a larger answer-matching experiment.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
from pathlib import Path

from llm_output_verifier import DATA, EVAL, OBS


# Build the answer-prediction prompt from only the task and standard tests.
def build_prompt(task: dict) -> str:
    tests = [{"test_index": index, "inputs": inputs} for index, inputs in enumerate(task["base_input"])]
    return (
        "Solve the following Python programming task mentally. "
        "For each supplied test input, predict the exact returned value of the requested function. "
        "Do not write code and do not use any hidden tests. "
        "Return only JSON with a predictions array containing one object per test. "
        "Each object must have test_index and value.\n\n"
        f"TASK:\n{task['prompt']}\n\n"
        f"ENTRY POINT: {task['entry_point']}\n\n"
        f"STANDARD TESTS:\n{json.dumps(tests, ensure_ascii=False)}"
    )


# Parse the model response into one prediction object per standard test.
def parse_response(text: str, count: int) -> list[dict]:
    value = json.loads(text)
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
    raise TypeError(f"Unsupported predicted value type: {type(value).__name__}")


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


# Run the bounded preview in parallel and save the raw prompts and responses.
def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tasks", type=int, default=2)
    parser.add_argument("--model", default="gpt-5-mini")
    parser.add_argument("--output", type=Path, default=Path("outputs/qwen-evalplus-full-10-temp02/llm-test-answer-preview.json"))
    args = parser.parse_args()
    from openai import OpenAI

    data = {row["task_id"]: row for row in map(json.loads, DATA.open())}
    evaluations = json.loads(EVAL.read_text())["eval"]
    task_ids = list(evaluations)[:args.tasks]
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(task_ids)) as executor:
        futures = [executor.submit(predict, client, args.model, task_id, data[task_id]) for task_id in task_ids]
        rows = [future.result() for future in futures]
    for row in rows:
        row["matching_candidate_indices"] = matching_candidates(row["task_id"], row["predictions"], evaluations)
    artifact = {"model": args.model, "tasks": task_ids, "results": rows}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, indent=2) + "\n")
    print(json.dumps({"tasks": task_ids, "matching_candidate_indices": {row["task_id"]: row["matching_candidate_indices"] for row in rows}}, indent=2))


if __name__ == "__main__":
    main()
