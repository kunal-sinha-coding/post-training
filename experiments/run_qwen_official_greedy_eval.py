"""Run the Qwen EvalPlus greedy protocol for MBPP and MBPP+.

The runner follows the published Qwen ChatML prompt, greedy decoding, 2,048-token budget, and stop sequences while using Transformers for local inference. It writes the same per-task Python files expected by EvalPlus so the official sanitizer and evaluator can score each model.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from datasets import load_dataset


# Build the published Qwen ChatML prompt after stripping task boundary whitespace.
def build_prompt(task_prompt: str) -> str:
    fence = chr(96) * 3
    return (
        "<|im_start|>system\n"
        "You are an intelligent programming assistant to produce Python algorithmic solutions<|im_end|>\n"
        "<|im_start|>user\n"
        "Can you complete the following Python function?\n"
        f"{fence}python\n{task_prompt.strip()}\n{fence}\n"
        "<|im_end|>\n"
        "<|im_start|>assistant\n"
        f"{fence}python\n"
    )


# Truncate a completion at the same stop strings configured by the Qwen wrapper.
def apply_stops(text: str) -> str:
    stops = ("<|endoftext|>", "<|endofmask|>", "</s>", "\nif __name__", "\nprint(", "\n#", "\n" + chr(96) * 3)
    positions = [text.find(stop) for stop in stops if text.find(stop) >= 0]
    return text[:min(positions)] if positions else text


# Load one model and tokenizer for the complete MBPP task set.
def load_model(model_name: str) -> tuple[object, object]:
    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=False)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(model_name, torch_dtype=torch.bfloat16, device_map="auto", trust_remote_code=False)
    model.eval()
    return model, tokenizer


def load_tasks() -> list[dict]:
    """Load the versioned EvalPlus MBPP task set used by the benchmark evaluator."""
    # Reconstruct the official visible MBPP prompt while retaining the exact EvalPlus task IDs.
    rows = load_dataset("evalplus/mbppplus", split="test")
    tasks = []
    for row in rows:
        visible_tests = "\n".join(row["test_list"])
        tasks.append({
            "task_id": f"Mbpp/{row['task_id']}",
            "prompt": f'"""\n{row["prompt"]}\n{visible_tests}\n"""\n',
        })
    return tasks


# Generate one greedy completion and remove the protocol stop suffix.
def generate_one(model: object, tokenizer: object, prompt: str) -> str:
    encoded = tokenizer(prompt, return_tensors="pt").to(model.device)
    with torch.inference_mode():
        output = model.generate(**encoded, do_sample=False, max_new_tokens=2048, pad_token_id=tokenizer.pad_token_id)
    completion = tokenizer.decode(output[0, encoded["input_ids"].shape[1]:], skip_special_tokens=False)
    return apply_stops(completion).split(chr(96) * 3, 1)[0].strip()


# Generate and persist the official one-sample-per-task EvalPlus layout.
def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    tasks = load_tasks()
    output = args.output_dir / "mbpp" / "qwen2_chat_temp_0.0"
    output.mkdir(parents=True, exist_ok=True)
    model, tokenizer = load_model(args.model)

    # Process tasks in official dataset order and save every completion immediately.
    for index, task in enumerate(tasks, 1):
        task_dir = output / task["task_id"].replace("/", "_")
        task_dir.mkdir(parents=True, exist_ok=True)
        code = generate_one(model, tokenizer, build_prompt(task["prompt"]))
        (task_dir / "0.py").write_text(code + "\n")
        print(f"Generated {index}/{len(tasks)} tasks", flush=True)


if __name__ == "__main__":
    main()
