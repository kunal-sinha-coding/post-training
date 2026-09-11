"""Generate one task's candidates with assertion-guided adaptive repairs.

The script loads Qwen2.5-Coder-3B-Instruct, generates one candidate at a time,
executes the task-visible assertion, repairs failures with the observed error,
stops at the first passing candidate, and saves the complete trace.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import signal
import subprocess
import sys
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from llm_output_verifier import DATA


# Build the original Qwen ChatML prompt for a fresh candidate.
def build_generation_prompt(task_prompt: str) -> str:
    fence = chr(96) * 3
    return ("<|im_start|>system\nYou are an intelligent programming assistant to produce Python algorithmic solutions<|im_end|>\n"
            "<|im_start|>user\nCan you complete the following Python function?\n"
            f"{fence}python\n{task_prompt}\n{fence}\n<|im_end|>\n<|im_start|>assistant\n{fence}python\n")


# Build a repair prompt that includes the failed candidate and assertion error.
def build_repair_prompt(task_prompt: str, code: str, error: str) -> str:
    fence = chr(96) * 3
    return ("<|im_start|>system\nYou are an intelligent programming assistant that repairs Python algorithmic solutions<|im_end|>\n"
            "<|im_start|>user\nRepair the following solution so it satisfies the task and its visible assertion. Return only Python code.\n"
            f"Task:\n{task_prompt}\n\nCurrent solution:\n{fence}python\n{code}\n{fence}\n\n"
            f"Visible assertion failure:\n{error}\n<|im_end|>\n<|im_start|>assistant\n{fence}python\n")


# Remove a leading or trailing Markdown fence from a model response.
def clean_completion(text: str) -> str:
    completion = text.split(chr(96) * 3, 1)[0]
    return completion.strip()


# Execute the candidate and visible assertion in an isolated process.
def check_assertion(code: str, assertion: str) -> dict:
    child = ("import contextlib,io,json,sys\n"
             "j=json.loads(sys.stdin.read())\n"
             "try:\n"
             "  with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):\n"
             "    scope={'__name__':'candidate'}\n"
             "    exec(j['code'],scope)\n"
             "    exec(j['assertion'],scope)\n"
             "  print(json.dumps({'passed':True}))\n"
             "except BaseException as e:\n"
             "  print(json.dumps({'passed':False,'error':type(e).__name__+': '+str(e)}))\n")
    try:
        result = subprocess.run([sys.executable, "-I", "-c", child], input=json.dumps({"code": code, "assertion": assertion}).encode(), stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=5)
        return json.loads(result.stdout.decode().splitlines()[-1]) if result.stdout else {"passed": False, "error": "No subprocess output"}
    except BaseException as error:
        return {"passed": False, "error": type(error).__name__ + ": " + str(error)}


# Generate one completion with the local Qwen model.
def generate_one(model: object, tokenizer: object, prompt: str, args: argparse.Namespace) -> str:
    encoded = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=args.max_prompt_tokens).to(model.device)
    with torch.inference_mode():
        output = model.generate(**encoded, do_sample=True, temperature=args.temperature, top_p=args.top_p, max_new_tokens=args.max_new_tokens, num_return_sequences=1, pad_token_id=tokenizer.pad_token_id)
    prompt_width = encoded["input_ids"].shape[1]
    return tokenizer.decode(output[0, prompt_width:], skip_special_tokens=True)


# Run the bounded repair loop for one task and return its complete trace.
def run_task(model: object, tokenizer: object, task: dict, args: argparse.Namespace) -> dict:
    assertion = next(line.strip() for line in task["prompt"].splitlines() if line.strip().startswith("assert "))
    records = []
    previous_code = ""
    previous_error = ""
    for index in range(10):
        prompt = build_generation_prompt(task["prompt"]) if not previous_code or not previous_error else build_repair_prompt(task["prompt"], previous_code, previous_error)
        raw = generate_one(model, tokenizer, prompt, args)
        code = clean_completion(raw)
        verdict = check_assertion(code, assertion)
        records.append({"index": index, "mode": "generate" if not previous_code or not previous_error else "repair", "prompt": prompt, "raw_output": raw, "code": code, "verdict": verdict})
        if verdict["passed"]:
            break
        previous_code = code
        previous_error = verdict.get("error", "Assertion failed")
    return {"experiment": "adaptive-assertion-guided-qwen3b", "model": args.model, "task_id": task["task_id"], "task_prompt": task["prompt"], "visible_assertion": assertion, "budget": 10, "stop_on_first_pass": True, "records": records}


# Load the model once and run either one task or every task with resumable saves.
def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--top-p", type=float, default=0.95)
    parser.add_argument("--max-new-tokens", type=int, default=512)
    parser.add_argument("--max-prompt-tokens", type=int, default=2048)
    parser.add_argument("--task-index", type=int, default=0)
    args = parser.parse_args()
    tasks = list(map(json.loads, DATA.open()))
    tokenizer = AutoTokenizer.from_pretrained(args.model, trust_remote_code=False)
    tokenizer.padding_side = "left"
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(args.model, torch_dtype=torch.bfloat16, device_map="auto", trust_remote_code=False)
    model.eval()
    if args.output_dir:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        for task in tasks:
            target = args.output_dir / f"{task['task_id'].replace('/', '_')}.json"
            if target.exists():
                print(f"Skipping saved {task['task_id']}", flush=True)
                continue
            artifact = run_task(model, tokenizer, task, args)
            target.write_text(json.dumps(artifact, indent=2) + "\n")
            passed = artifact["records"][-1]["verdict"]["passed"]
            print(f"Completed {task['task_id']}: {len(artifact['records'])} outputs, assertion {'passed' if passed else 'failed'}", flush=True)
        return
    if args.output is None:
        raise ValueError("Specify --output for one task or --output-dir for the full suite.")
    artifact = run_task(model, tokenizer, tasks[args.task_index], args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, indent=2) + "\n")
    print(f"Completed {artifact['task_id']}: {len(artifact['records'])} outputs, assertion {'passed' if artifact['records'][-1]['verdict']['passed'] else 'failed'}", flush=True)


if __name__ == "__main__":
    main()
