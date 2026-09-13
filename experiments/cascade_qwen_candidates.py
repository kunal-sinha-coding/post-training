"""Run a two model cascade and save paired MBPP candidates.

The script loads the 0.5B model, generates and verifies every task, saves each
result immediately, unloads the small model, routes only visible assertion
failures to the 3B model for one repair, and leaves artifacts for paired MBPP
and MBPP+ evaluation.
"""

from __future__ import annotations

import argparse
import gc
import json
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from adaptive_qwen_candidates import (
    build_generation_prompt,
    build_repair_prompt,
    check_assertion,
    clean_completion,
    generate_one,
)
from llm_output_verifier import DATA


# Load one causal model and tokenizer with the configured generation settings.
def load_model(model_name: str) -> tuple[object, object]:
    # Load the tokenizer and model once before processing the assigned stage.
    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=False)
    tokenizer.padding_side = "left"
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(model_name, torch_dtype=torch.bfloat16, device_map="auto", trust_remote_code=False)
    model.eval()
    return model, tokenizer


# Run one model completion and visible assertion for a task.
def run_candidate(model: object, tokenizer: object, task: dict, args: argparse.Namespace, prompt: str, model_name: str) -> dict:
    # Generate code, clean the response, and preserve the complete verifier record.
    assertion = next(line.strip() for line in task["prompt"].splitlines() if line.strip().startswith("assert "))
    raw = generate_one(model, tokenizer, prompt, args)
    code = clean_completion(raw)
    verdict = check_assertion(code, assertion)
    return {"model": model_name, "prompt": prompt, "raw_output": raw, "code": code, "verdict": verdict}


# Save one task artifact immediately after its current cascade stage.
def save_artifact(path: Path, task: dict, assertion: str, records: list[dict], route: str) -> None:
    # Preserve the initial and selected records with the routing decision.
    artifact = {
        "experiment": "qwen3b-simple-cascade",
        "model": "Qwen/Qwen2.5-Coder-3B-Instruct",
        "task_id": task["task_id"],
        "task_prompt": task["prompt"],
        "visible_assertion": assertion,
        "route": route,
        "budget": len(records),
        "records": [{"index": index, "mode": "generate" if index == 0 else "repair", **record} for index, record in enumerate(records)],
    }
    path.write_text(json.dumps(artifact, indent=2) + "\n")


# Release the current model before loading the larger cascade stage.
def unload_model(model: object, tokenizer: object) -> None:
    # Delete model references and release cached accelerator memory.
    del model, tokenizer
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


# Generate small model candidates, route failures, and save every task.
def main() -> None:
    # Parse model names, output locations, and generation configuration.
    parser = argparse.ArgumentParser()
    parser.add_argument("--small-model", default="Qwen/Qwen2.5-Coder-0.5B-Instruct")
    parser.add_argument("--large-model", default="Qwen/Qwen2.5-Coder-3B-Instruct")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--max-new-tokens", type=int, default=512)
    parser.add_argument("--max-prompt-tokens", type=int, default=2048)
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--top-p", type=float, default=0.95)
    args = parser.parse_args()
    tasks = list(map(json.loads, DATA.open()))
    args.output_dir.mkdir(parents=True, exist_ok=True)

    # Run the inexpensive initial generation across the entire task set.
    small_model, small_tokenizer = load_model(args.small_model)
    failures = []
    for completed, task in enumerate(tasks, 1):
        assertion = next(line.strip() for line in task["prompt"].splitlines() if line.strip().startswith("assert "))
        record = run_candidate(small_model, small_tokenizer, task, args, build_generation_prompt(task["prompt"]), args.small_model)
        target = args.output_dir / f"{task['task_id'].replace('/', '_')}.json"
        save_artifact(target, task, assertion, [record], "small" if record["verdict"]["passed"] else "large_pending")
        if not record["verdict"]["passed"]:
            failures.append((task, record))
        if completed % 25 == 0 or completed == len(tasks):
            print(f"Small model completed {completed}/{len(tasks)}; routed failures {len(failures)}", flush=True)
    unload_model(small_model, small_tokenizer)

    # Run one large model repair only for tasks that failed the visible assertion.
    large_model, large_tokenizer = load_model(args.large_model)
    for completed, (task, initial) in enumerate(failures, 1):
        error = initial["verdict"].get("error", "Assertion failed")
        retry_prompt = build_repair_prompt(task["prompt"], initial["code"], error)
        retry = run_candidate(large_model, large_tokenizer, task, args, retry_prompt, args.large_model)
        assertion = next(line.strip() for line in task["prompt"].splitlines() if line.strip().startswith("assert "))
        save_artifact(args.output_dir / f"{task['task_id'].replace('/', '_')}.json", task, assertion, [initial, retry], "large")
        if completed % 25 == 0 or completed == len(failures):
            print(f"Large model completed {completed}/{len(failures)} routed repairs", flush=True)
    unload_model(large_model, large_tokenizer)
    print(f"Cascade completed {len(tasks)} tasks with {len(failures)} routed to the large model", flush=True)


if __name__ == "__main__":
    main()
