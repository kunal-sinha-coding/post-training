# This script loads Qwen with LoRA, scores two fixed completions with fixed advantages, applies one controlled policy-gradient update, and reports whether the positive completion becomes more likely.

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import torch
import torch.nn.functional as functional
from transformers import AutoModelForCausalLM, AutoTokenizer

# Make shared repository modules importable when this file is launched directly.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from train import build_peft_config, seed_everything


def build_probe_inputs(tokenizer: object) -> tuple[str, list[str]]:
    """Build one fixed chat prompt and two fixed assistant completions."""
    # Use one simple coding task so the probe does not depend on sampling or sandbox execution.
    messages = [{"role": "user", "content": "Write a Python function named add(a, b) that returns the sum of a and b."}]
    prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    completions = [
        "```python\ndef add(a, b):\n    return a + b\n```",
        "```python\ndef add(a, b):\n    return a - b\n```",
    ]
    return prompt, completions


def sequence_logps(model: object, tokenizer: object, prompt: str, completions: list[str], device: torch.device) -> torch.Tensor:
    """Compute the mean teacher-forced completion log probability for each fixed sample."""
    # Tokenize each prompt and completion pair while preserving the exact prompt boundary.
    rows = []
    prompt_lengths = []
    for completion in completions:
        prompt_ids = tokenizer(prompt, add_special_tokens=False)["input_ids"]
        completion_ids = tokenizer(completion, add_special_tokens=False)["input_ids"]
        prompt_lengths.append(len(prompt_ids))
        rows.append(prompt_ids + completion_ids)
    width = max(len(row) for row in rows)
    input_ids = torch.full((len(rows), width), tokenizer.pad_token_id, dtype=torch.long, device=device)
    attention_mask = torch.zeros_like(input_ids)
    for row_index, row in enumerate(rows):
        input_ids[row_index, : len(row)] = torch.tensor(row, dtype=torch.long, device=device)
        attention_mask[row_index, : len(row)] = 1
    # Score only completion tokens so the shared prompt cannot dominate the comparison.
    outputs = model(input_ids=input_ids, attention_mask=attention_mask)
    log_probs = functional.log_softmax(outputs.logits[:, :-1].float(), dim=-1)
    target_ids = input_ids[:, 1:]
    token_log_probs = log_probs.gather(-1, target_ids.unsqueeze(-1)).squeeze(-1)
    completion_mask = torch.zeros_like(token_log_probs, dtype=torch.float32)
    for row_index, prompt_length in enumerate(prompt_lengths):
        completion_mask[row_index, prompt_length - 1 : len(rows[row_index]) - 1] = 1.0
    return (token_log_probs * completion_mask).sum(dim=1) / completion_mask.sum(dim=1)


def run_probe(args: argparse.Namespace) -> dict[str, object]:
    """Run repeated deterministic LoRA policy-gradient updates on one fixed rollout."""
    # Seed every relevant library and use evaluation mode so dropout cannot add noise.
    seed_everything(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    tokenizer = AutoTokenizer.from_pretrained(args.model, use_fast=True)
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(args.model, torch_dtype=torch.bfloat16 if device.type == "cuda" else torch.float32)
    model.to(device)
    model = model
    peft_config = build_peft_config({"lora_enabled": True, "lora_r": 16, "lora_alpha": 32, "lora_dropout": 0.0, "lora_target_modules": ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]})
    from peft import get_peft_model
    model = get_peft_model(model, peft_config)
    model.eval()
    prompt, completions = build_probe_inputs(tokenizer)
    advantages = torch.tensor([0.5, -0.5], dtype=torch.float32, device=device)
    # Reuse one fixed rollout and its advantages for every optimizer update.
    # Match the AdamW optimizer used by the live GRPO trainer while keeping the rollout frozen.
    optimizer = torch.optim.AdamW(
        [parameter for parameter in model.parameters() if parameter.requires_grad],
        lr=args.learning_rate,
        weight_decay=0.0,
    )
    initial_logps = sequence_logps(model, tokenizer, prompt, completions, device).detach()
    initial_loss = -(advantages * initial_logps).mean()
    history = []
    for update in range(args.iterations):
        # Measure the fixed-batch objective before this update.
        before_logps = sequence_logps(model, tokenizer, prompt, completions, device)
        before_loss = -(advantages * before_logps).mean()
        optimizer.zero_grad(set_to_none=True)
        before_loss.backward()
        gradient_norm = torch.nn.utils.clip_grad_norm_([parameter for parameter in model.parameters() if parameter.requires_grad], max_norm=float("inf"))
        optimizer.step()
        # Measure the same fixed sequences after this update.
        with torch.no_grad():
            after_logps = sequence_logps(model, tokenizer, prompt, completions, device)
            after_loss = -(advantages * after_logps).mean()
        history.append({
            "update": update + 1,
            "before_loss": float(before_loss.detach().cpu()),
            "after_loss": float(after_loss.cpu()),
            "loss_delta": float((after_loss - before_loss.detach()).cpu()),
            "logp_deltas": (after_logps - before_logps.detach()).cpu().tolist(),
            "gradient_norm": float(gradient_norm),
        })
        print(json.dumps(history[-1]), flush=True)
    after_logps = sequence_logps(model, tokenizer, prompt, completions, device).detach()
    after_loss = -(advantages * after_logps).mean()
    result = {
        "model": args.model,
        "seed": args.seed,
        "learning_rate": args.learning_rate,
        "iterations": args.iterations,
        "prompt": prompt,
        "completions": completions,
        "advantages": advantages.cpu().tolist(),
        "before_logps": initial_logps.cpu().tolist(),
        "history": history,
        "after_logps": after_logps.cpu().tolist(),
        "before_loss": float(initial_loss.cpu()),
        "after_loss": float(after_loss.cpu()),
        "gradient_norm": history[-1]["gradient_norm"],
        "positive_direction_passed": all(item["logp_deltas"][0] > 0 for item in history),
        "negative_direction_passed": all(item["logp_deltas"][1] < 0 for item in history),
    }
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2), flush=True)
    return result


def parse_args() -> argparse.Namespace:
    """Parse deterministic probe command-line options."""
    # Keep the probe reproducible while allowing a smaller learning rate for follow-up checks.
    parser = argparse.ArgumentParser(description="Run a deterministic two-completion GRPO direction probe.")
    parser.add_argument("--model", default="Qwen/Qwen2.5-Coder-3B-Instruct")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--learning-rate", type=float, default=1e-3)
    parser.add_argument("--iterations", type=int, default=20)
    parser.add_argument("--output", default="outputs/fixed-rollout-overfit/result.json")
    return parser.parse_args()


if __name__ == "__main__":
    run_probe(parse_args())
