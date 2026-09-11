"""Use one LLM call per task to select among saved EvalPlus candidates.

The script loads the official EvalPlus task prompt, visible and extended test
inputs, and saved candidate outputs, asks an external LLM to choose one
candidate without exposing correctness labels, caches every request and
response, and computes selected-candidate accuracy only after selection.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path


# Keep all source and cached artifact locations explicit for reproducibility.
ROOT = Path("outputs/qwen-evalplus-full-10-temp02")
DATA = Path("qwen_eval/eval_plus/MbppPlus-v0.1.0.jsonl")
EVAL = ROOT / "mbpp/qwen2_chat_temp_0.2/eval_results.json"
OBS = ROOT / "output-clusters-v3/observations"


# Build a compact JSON-safe description of one saved test observation.
def observation_view(row: dict) -> dict:
    if row["status"] != "returned":
        return {"status": row["status"]}
    return {"status": "returned", "value": row.get("value", "unserializable")}


# Load the exact candidate code and output observations in generation order.
def load_task(task_id: str, task: dict, evaluations: dict) -> list[dict]:
    candidates = []
    for index, evaluation in enumerate(evaluations[task_id]):
        observation_path = OBS / f"{task_id.replace('/', '_')}_{index}.json"
        observation = json.loads(observation_path.read_text())
        candidates.append({
            "candidate_index": index,
            "code": evaluation["solution"],
            "outputs": [observation_view(row) for row in observation["tests"]],
        })
    return candidates


# Construct the verifier prompt while excluding benchmark correctness labels.
def build_prompt(task: dict, candidates: list[dict]) -> str:
    cases = [{"suite": "base", "inputs": task["base_input"]}, {"suite": "plus", "inputs": task["plus_input"]}]
    candidate_text = []
    for candidate in candidates:
        candidate_text.append(json.dumps({
            "candidate_index": candidate["candidate_index"],
            "program": candidate["code"],
            "observed_outputs_in_test_order": candidate["outputs"],
        }, ensure_ascii=False))
    return (
        "You are selecting the most likely correct Python program for a coding task. "
        "Reason about the task and compare every candidate against all supplied tests and outputs. "
        "The test outputs are observations from running each program and may contain errors. "
        "Choose exactly one candidate index. Do not write a replacement program. "
        "Return only JSON with keys selected_candidate_index and rationale.\n\n"
        f"TASK PROMPT:\n{task['prompt']}\n\n"
        f"ENTRY POINT: {task['entry_point']}\n\n"
        f"TEST INPUTS:\n{json.dumps(cases, ensure_ascii=False)}\n\n"
        "CANDIDATES:\n" + "\n".join(candidate_text)
    )


# Parse a model response into a valid candidate index or fail loudly for review.
def parse_selection(text: str, count: int) -> tuple[int, str]:
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        value = json.loads(text[start:end + 1]) if start >= 0 and end > start else {}
    index = int(value["selected_candidate_index"])
    if index < 0 or index >= count:
        raise ValueError(f"Selected candidate index {index} is outside 0..{count - 1}.")
    return index, str(value.get("rationale", ""))


# Ask the configured LLM once and preserve the exact request and response for reuse.
def call_verifier(client: object, model: str, prompt: str, count: int) -> dict:
    response = client.chat.completions.create(
        model=model,
        temperature=0,
        messages=[
            {"role": "system", "content": "Select among candidate programs using the task and observed tests."},
            {"role": "user", "content": prompt},
        ],
    )
    text = response.choices[0].message.content or ""
    index, rationale = parse_selection(text, count)
    return {"raw_response": text, "selected_candidate_index": index, "rationale": rationale}


# Measure selected candidates against saved base and EvalPlus correctness labels after selection.
def measure(rows: list[dict], evaluations: dict) -> dict:
    metrics = {}
    for suite in ("base", "plus", "combined"):
        hits = []
        for row in rows:
            evaluation = evaluations[row["task_id"]][row["selected_candidate_index"]]
            hits.append((evaluation["base_status"] == "pass") if suite == "base" else (evaluation["plus_status"] == "pass") if suite == "plus" else evaluation["base_status"] == evaluation["plus_status"] == "pass")
        metrics[suite] = {"correct": sum(hits), "tasks": len(hits), "accuracy": sum(hits) / len(hits) if hits else 0.0}
    return metrics


# Run cached verification calls and write a complete reusable experiment artifact.
def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tasks", type=int, default=20)
    parser.add_argument("--model", default="gpt-5-mini")
    parser.add_argument("--output", type=Path, default=ROOT / "llm-output-verifier-20.json")
    args = parser.parse_args()

    from openai import OpenAI

    data = {row["task_id"]: row for row in map(json.loads, DATA.open())}
    evaluations = json.loads(EVAL.read_text())["eval"]
    task_ids = list(evaluations)[:args.tasks]
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    cached = json.loads(args.output.read_text()) if args.output.exists() else {"results": {}}
    results = cached.get("results", {})
    for task_id in task_ids:
        task = data[task_id]
        candidates = load_task(task_id, task, evaluations)
        prompt = build_prompt(task, candidates)
        prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()
        existing = results.get(task_id)
        if existing and existing.get("prompt_sha256") == prompt_hash and existing.get("model") == args.model:
            continue
        decision = call_verifier(client, args.model, prompt, len(candidates))
        results[task_id] = {
            "task_id": task_id,
            "model": args.model,
            "prompt_sha256": prompt_hash,
            "candidate_count": len(candidates),
            **decision,
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps({"results": results}, indent=2) + "\n")
        print(f"Verified {len(results)}/{len(task_ids)}: {task_id}", flush=True)
    selected_rows = [results[task_id] for task_id in task_ids]
    artifact = {
        "experiment": "llm-output-verifier-evalplus-20",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tasks": task_ids,
        "model": args.model,
        "candidate_artifact": str(EVAL),
        "observation_artifact": str(OBS),
        "selection_uses_correctness_labels": False,
        "results": {row["task_id"]: row for row in selected_rows},
        "metrics": measure(selected_rows, evaluations),
        "baseline_pass_at_k": json.loads((ROOT / "pass_at_k.json").read_text())["base"],
    }
    args.output.write_text(json.dumps(artifact, indent=2) + "\n")
    print(json.dumps(artifact["metrics"], indent=2))


if __name__ == "__main__":
    main()
