"""Generate candidates lazily until the visible assertion passes.

The runner loads one configured Qwen model, uses the established EvalPlus ChatML prompt and sampling settings, generates one candidate per task, executes the visible assertion, and samples another candidate with the identical prompt only after failure. Every attempt is saved immediately, and the run stops at the first passing candidate or after ten attempts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from adaptive_qwen_candidates import generate_one
from filter_candidates_by_visible_assertion import evaluate_candidate, visible_assertion
from regenerate_qwen_candidates import build_prompt, clean_completion
from llm_output_verifier import DATA


# Save one completed task artifact for resumable progress.
def save_task(path: Path, artifact: dict) -> None:
    path.write_text(json.dumps(artifact, indent=2) + "\n")


# Load one causal model and tokenizer with the established generation settings.
def load_model(model_name: str) -> tuple[object, object]:
    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=False)
    tokenizer.padding_side = "left"
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(model_name, torch_dtype=torch.bfloat16, device_map="auto", trust_remote_code=False)
    model.eval()
    return model, tokenizer


# Generate one candidate with the exact prompt and sampling configuration.
def generate_candidate(model: object, tokenizer: object, prompt: str, args: argparse.Namespace) -> tuple[str, str]:
    raw = generate_one(model, tokenizer, prompt, args)
    return raw, clean_completion(raw)


# Run tasks sequentially and stop sampling after the first visible assertion pass.
def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--max-attempts", type=int, default=10)
    parser.add_argument("--max-new-tokens", type=int, default=512)
    parser.add_argument("--max-prompt-tokens", type=int, default=1024)
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--top-p", type=float, default=0.95)
    parser.add_argument("--timeout-seconds", type=float, default=2.0)
    args = parser.parse_args()
    tasks = list(map(json.loads, DATA.open()))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    model, tokenizer = load_model(args.model)

    # Process tasks in dataset order and preserve each completed attempt immediately.
    for completed, task in enumerate(tasks, 1):
        target = args.output_dir / f"{task['task_id'].replace('/', '_')}.json"
        if target.exists():
            continue
        prompt = build_prompt(task["prompt"])
        assertion = visible_assertion(task["prompt"])
        attempts = []

        # Repeat the identical prompt only when the preceding candidate fails.
        for index in range(args.max_attempts):
            raw, code = generate_candidate(model, tokenizer, prompt, args)
            verdict = evaluate_candidate(code, assertion, args.timeout_seconds)
            attempts.append({
                "candidate_index": index,
                "prompt": prompt,
                "raw_output": raw,
                "code": code,
                "code_sha256": hashlib.sha256(code.encode()).hexdigest(),
                "verdict": verdict,
            })
            artifact = {
                "experiment": "sequential-visible-assertion-sampling-evalplus-399",
                "model": args.model,
                "task_id": task["task_id"],
                "task_prompt": task["prompt"],
                "visible_assertion": assertion,
                "max_attempts": args.max_attempts,
                "sampling": {"temperature": args.temperature, "top_p": args.top_p, "max_new_tokens": args.max_new_tokens, "max_prompt_tokens": args.max_prompt_tokens},
                "attempts": attempts,
                "selected_attempt": index if verdict["status"] == "pass" else None,
                "stopped_on_visible_pass": verdict["status"] == "pass",
            }
            save_task(target, artifact)
            if verdict["status"] == "pass":
                break
        print(f"Completed {completed}/{len(tasks)} tasks; attempts={len(attempts)}; visible_pass={attempts[-1]['verdict']['status'] == 'pass'}", flush=True)


if __name__ == "__main__":
    main()
