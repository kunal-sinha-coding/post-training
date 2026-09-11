"""Regenerate and persist ten Qwen candidate programs for every MBPP task.

The script reproduces the EvalPlus Qwen ChatML prompt and sampling settings,
generates ten completions per task with a local Transformers checkpoint, saves
raw completions and cleaned Python programs immediately, and writes a manifest
containing model, sampling, prompt, and code hashes for future experiments.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from llm_output_verifier import DATA


# Build the original Qwen ChatML completion prompt for one MBPP task.
def build_prompt(task_prompt: str) -> str:
    fence = chr(96) * 3
    return (
        "<|im_start|>system\n"
        "You are an intelligent programming assistant to produce Python algorithmic solutions<|im_end|>\n"
        "<|im_start|>user\n"
        "Can you complete the following Python function?\n"
        f"{fence}python\n{task_prompt}\n{fence}\n"
        "<|im_end|>\n"
        "<|im_start|>assistant\n"
        f"{fence}python\n"
    )


# Remove generation fences while retaining the generated Python source.
def clean_completion(text: str) -> str:
    completion = text.split(chr(96) * 3, 1)[0]
    return completion.strip()


# Hash text bytes so each persisted candidate can be verified later.
def digest(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


# Generate and persist one batch of task completions without discarding raw text.
def generate_batch(model: object, tokenizer: object, tasks: list[dict], args: argparse.Namespace) -> None:
    prompts = [build_prompt(task["prompt"]) for task in tasks for _ in range(args.samples)]
    encoded = tokenizer(prompts, return_tensors="pt", padding=True, truncation=True, max_length=args.max_prompt_tokens).to(model.device)
    with torch.inference_mode():
        outputs = model.generate(
            **encoded,
            do_sample=True,
            temperature=args.temperature,
            top_p=args.top_p,
            max_new_tokens=args.max_new_tokens,
            num_return_sequences=1,
            pad_token_id=tokenizer.pad_token_id,
        )
    prompt_width = encoded["input_ids"].shape[1]
    decoded = tokenizer.batch_decode(outputs[:, prompt_width:], skip_special_tokens=True)
    cursor = 0
    for task in tasks:
        task_dir = args.output_dir / "mbpp" / "qwen2_chat_temp_0.2" / task["task_id"].replace("/", "_")
        task_dir.mkdir(parents=True, exist_ok=True)
        manifest_rows = []
        for candidate_index in range(args.samples):
            raw = decoded[cursor]
            cleaned = clean_completion(raw)
            source_path = task_dir / f"{candidate_index}.py"
            raw_path = task_dir / f"{candidate_index}.raw.txt"
            source_path.write_text(cleaned + "\n")
            raw_path.write_text(raw)
            manifest_rows.append({"candidate_index": candidate_index, "source": str(source_path), "raw": str(raw_path), "code_sha256": digest(cleaned), "prompt_sha256": digest(prompts[cursor])})
            cursor += 1
        (task_dir / "manifest.json").write_text(json.dumps({"task_id": task["task_id"], "candidates": manifest_rows}, indent=2) + "\n")


# Run resumable local generation and save the complete run manifest.
def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--batch-tasks", type=int, default=2)
    parser.add_argument("--samples", type=int, default=10)
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--top-p", type=float, default=0.95)
    parser.add_argument("--max-new-tokens", type=int, default=512)
    parser.add_argument("--max-prompt-tokens", type=int, default=1024)
    args = parser.parse_args()
    tasks = list(map(json.loads, DATA.open()))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = args.output_dir / "run_manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {
        "experiment": "regenerate-qwen-candidates-for-visible-filter",
        "model": args.model,
        "name": args.name,
        "temperature": args.temperature,
        "top_p": args.top_p,
        "samples": args.samples,
        "max_new_tokens": args.max_new_tokens,
        "max_prompt_tokens": args.max_prompt_tokens,
        "tasks": [task["task_id"] for task in tasks],
        "completed_tasks": [],
    }
    tokenizer = AutoTokenizer.from_pretrained(args.model, trust_remote_code=False)
    tokenizer.padding_side = "left"
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(args.model, torch_dtype=torch.bfloat16, device_map="auto", trust_remote_code=False)
    model.eval()
    for start in range(0, len(tasks), args.batch_tasks):
        batch = [task for task in tasks[start:start + args.batch_tasks] if task["task_id"] not in manifest["completed_tasks"]]
        if not batch:
            continue
        generate_batch(model, tokenizer, batch, args)
        manifest["completed_tasks"].extend(task["task_id"] for task in batch)
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
        print(f"Generated {len(manifest['completed_tasks'])}/{len(tasks)} tasks", flush=True)


if __name__ == "__main__":
    main()
