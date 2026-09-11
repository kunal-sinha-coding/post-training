"""Evaluate local Qwen models on the same standard-answer prediction task.

The script loads one local Qwen2.5-Coder-Instruct checkpoint at a time, sends
the exact answer-prediction messages used for the GPT-5 mini experiment,
parses and caches one response per EvalPlus task, and measures predictions
against the trusted canonical outputs.
"""

from __future__ import annotations

import argparse
import gc
import json
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from llm_output_verifier import DATA, EVAL
from llm_test_answer_predictor import build_prompt, ground_truth, parse_response, values_match


# Generate a local model response for one batch of answer-prediction prompts.
def generate_batch(model: object, tokenizer: object, prompts: list[str], max_new_tokens: int) -> list[str]:
    messages = [
        [
            {"role": "system", "content": "Predict the exact outputs for the supplied standard tests."},
            {"role": "user", "content": prompt},
        ]
        for prompt in prompts
    ]
    rendered = [tokenizer.apply_chat_template(item, tokenize=False, add_generation_prompt=True) for item in messages]
    batch = tokenizer(rendered, return_tensors="pt", padding=True, truncation=True).to(model.device)
    with torch.inference_mode():
        output = model.generate(**batch, do_sample=False, max_new_tokens=max_new_tokens)
    prompt_length = batch["input_ids"].shape[1]
    return tokenizer.batch_decode(output[:, prompt_length:], skip_special_tokens=True)


# Compute test and task accuracy from parsed model predictions and canonical outputs.
def measure(task_ids: list[str], rows: dict[str, dict], data: dict[str, dict]) -> dict:
    test_correct = 0
    test_total = 0
    task_correct = 0
    per_task = {}
    for task_id in task_ids:
        expected = ground_truth(task_id, data[task_id])
        predicted = {item["test_index"]: item["value"] for item in rows[task_id].get("predictions", [])}
        correctness = [values_match(value, predicted.get(index), data[task_id]["atol"]) for index, value in enumerate(expected)]
        test_correct += sum(correctness)
        test_total += len(correctness)
        task_correct += all(correctness)
        per_task[task_id] = {"test_correct": sum(correctness), "test_total": len(correctness), "all_tests_correct": all(correctness)}
    return {
        "test_accuracy": test_correct / test_total if test_total else 0.0,
        "test_correct": test_correct,
        "test_total": test_total,
        "task_accuracy": task_correct / len(task_ids) if task_ids else 0.0,
        "tasks_all_correct": task_correct,
        "tasks_total": len(task_ids),
        "per_task": per_task,
    }


# Evaluate one checkpoint and incrementally save every decoded response.
def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--tasks", type=int, default=399)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--max-new-tokens", type=int, default=256)
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/qwen-answer-predictions"))
    args = parser.parse_args()

    data = {row["task_id"]: row for row in map(json.loads, DATA.open())}
    evaluations = json.loads(EVAL.read_text())["eval"]
    task_ids = list(evaluations)[:args.tasks]
    output = args.output_dir / f"{args.name}.json"
    cached = json.loads(output.read_text()) if output.exists() else {"results": {}}
    rows = cached.get("results", {})
    tokenizer = AutoTokenizer.from_pretrained(args.model, trust_remote_code=False)
    tokenizer.padding_side = "left"
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(args.model, torch_dtype=torch.bfloat16, device_map="auto", trust_remote_code=False)
    model.eval()
    output.parent.mkdir(parents=True, exist_ok=True)
    for start in range(0, len(task_ids), args.batch_size):
        batch_ids = [task_id for task_id in task_ids[start:start + args.batch_size] if task_id not in rows]
        if not batch_ids:
            continue
        prompts = [build_prompt(data[task_id]) for task_id in batch_ids]
        raw_responses = generate_batch(model, tokenizer, prompts, args.max_new_tokens)
        for task_id, prompt, raw in zip(batch_ids, prompts, raw_responses):
            row = {"task_id": task_id, "prompt": prompt, "raw_response": raw}
            try:
                row["predictions"] = parse_response(raw, len(data[task_id]["base_input"]))
            except Exception as error:
                row["predictions"] = []
                row["parse_error"] = repr(error)
            rows[task_id] = row
        output.write_text(json.dumps({"model": args.model, "name": args.name, "results": rows}, indent=2) + "\n")
        print(f"{args.name}: predicted {len(rows)}/{len(task_ids)}", flush=True)
    report = {
        "experiment": "local-standard-test-answer-prediction-evalplus",
        "model": args.model,
        "name": args.name,
        "tasks": task_ids,
        "results": rows,
        "metrics": measure(task_ids, rows, data),
    }
    output.write_text(json.dumps(report, indent=2) + "\n")
    del model
    gc.collect()
    torch.cuda.empty_cache()
    print(json.dumps({key: value for key, value in report["metrics"].items() if key != "per_task"}, indent=2))


if __name__ == "__main__":
    main()
