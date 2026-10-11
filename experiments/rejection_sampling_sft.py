# This experiment loads one MBPP task and a model, samples completions, keeps only fully passing solutions, and fine tunes with masked cross entropy.
# It repeats sampling and one supervised epoch until greedy evaluation passes the task or the configured cycle limit is reached.

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from pathlib import Path
from typing import Any

# Add the repository root so direct script execution can import shared training helpers.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def load_task(task_id: str) -> dict[str, Any]:
    """Load and normalize one original MBPP task by its numeric identifier."""
    # Search cached Arrow splits first to avoid downloading data during this small experiment.
    from datasets import Dataset
    from datasets.config import HF_DATASETS_CACHE
    from data import normalize_record

    cache_root = Path(HF_DATASETS_CACHE)
    arrow_files = list(cache_root.glob("google-research-datasets___mbpp/full/0.0.0/*/mbpp-*.arrow"))
    for arrow_path in arrow_files:
        # Return the requested task in the same prompt and test format used by GRPO.
        for row in Dataset.from_file(str(arrow_path)):
            if str(row.get("task_id")) == str(task_id):
                return normalize_record(row, visible_test_count=1)
    # Report a clear error when the task is missing from all local MBPP splits.
    raise ValueError(f"MBPP task {task_id} was not found in cached Arrow splits under {cache_root}.")


def clean_completion(completion: str) -> str:
    """Remove generated Markdown code-fence markers from the assistant response."""
    # Strip a generated opening fence before removing any closing fence.
    text = completion.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else ""
    # Keep the code body when generation includes the prompt's closing fence.
    return text.split("```", 1)[0].strip()


def load_model(model_path: str, use_bf16: bool, device: str) -> tuple[Any, Any]:
    """Load a PEFT checkpoint or create a LoRA model from a base model."""
    # Load the tokenizer for the selected checkpoint or base model.
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=False)
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    dtype = torch.bfloat16 if use_bf16 else torch.float16
    if (Path(model_path) / "adapter_config.json").is_file():
        # Load the saved adapter without changing the source checkpoint.
        from peft import AutoPeftModelForCausalLM

        model = AutoPeftModelForCausalLM.from_pretrained(model_path, torch_dtype=dtype, device_map=device, is_trainable=True)
    else:
        # Attach a small LoRA adapter when the source is a base causal model.
        from peft import LoraConfig, get_peft_model

        model = AutoModelForCausalLM.from_pretrained(model_path, torch_dtype=dtype, device_map=device)
        model = get_peft_model(model, LoraConfig(task_type="CAUSAL_LM", r=8, lora_alpha=16, lora_dropout=0.0, target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]))
    # Use evaluation mode before sampling from the policy.
    model.eval()
    return model, tokenizer


def generate(model: Any, tokenizer: Any, prompt: str, count: int, batch_size: int, max_new_tokens: int, temperature: float, greedy: bool = False) -> list[dict[str, Any]]:
    """Generate candidate completions in small batches to limit temporary GPU use."""
    import torch

    outputs = []
    # Generate only the remaining candidates in each bounded batch.
    for start in range(0, count, batch_size):
        current_batch = min(batch_size, count - start)
        encoded = tokenizer([prompt] * current_batch, return_tensors="pt", padding=True, truncation=True, max_length=1024).to(model.device)
        input_length = encoded["input_ids"].shape[1]
        with torch.inference_mode():
            # Sample diverse candidates or use one deterministic greedy completion.
            sampling = {"do_sample": False} if greedy else {"do_sample": True, "temperature": temperature, "top_p": 0.95}
            generated = model.generate(**encoded, **sampling, max_new_tokens=max_new_tokens, pad_token_id=tokenizer.pad_token_id, eos_token_id=tokenizer.eos_token_id)
        # Keep only tokens emitted after the prompt and decode each response.
        for sequence in generated:
            outputs.append({"completion": clean_completion(tokenizer.decode(sequence[input_length:], skip_special_tokens=True)), "prompt_tokens": input_length})
        del encoded, generated
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    return outputs


def score_candidates(candidates: list[dict[str, Any]], task: dict[str, Any], timeout: float) -> list[dict[str, Any]]:
    """Score every sampled completion against all task assertions in the sandbox."""
    from sandbox import score_completion, wrap_qwen_continuation

    scored = []
    # Preserve each generation and its detailed assertion outcomes for later review.
    for index, candidate in enumerate(candidates):
        completion = clean_completion(candidate["completion"])
        wrapped = f"Code:\n```python\n{completion}\n```"
        _, details = score_completion(wrapped, task["test_code"], timeout_seconds=timeout, reward_function="test_pass", visible_test_count=1)
        scored.append({"sample_index": index, **candidate, "completion": completion, **details, "passed_all": bool(details.get("passed_tests") == details.get("total_tests"))})
    return scored


def evaluate_greedy(model: Any, tokenizer: Any, task: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    """Generate and score one greedy completion for the selected task."""
    # Reuse the same sandbox path used to filter sampled candidates.
    candidate = generate(model, tokenizer, task["prompt"], 1, 1, args.max_new_tokens, args.temperature, greedy=True)[0]
    return score_candidates([candidate], task, args.timeout)[0]


def fine_tune_one_epoch(model: Any, tokenizer: Any, task: dict[str, Any], accepted: list[dict[str, Any]], args: argparse.Namespace) -> float:
    """Run one shuffled epoch of response-only cross-entropy updates on accepted samples."""
    import torch

    trainable = [parameter for parameter in model.parameters() if parameter.requires_grad]
    optimizer = torch.optim.AdamW(trainable, lr=args.learning_rate)
    indices = list(range(len(accepted)))
    random.Random(args.seed + len(accepted)).shuffle(indices)
    total_loss = 0.0
    model.train()
    # Update once per accepted response so each small batch makes one optimizer step.
    for index in indices:
        prompt_ids = tokenizer(task["prompt"], add_special_tokens=True, truncation=True, max_length=args.max_prompt_tokens, return_tensors="pt")["input_ids"].to(model.device)
        response_ids = tokenizer(clean_completion(accepted[index]["completion"]), add_special_tokens=False, truncation=True, max_length=args.max_response_tokens, return_tensors="pt")["input_ids"].to(model.device)
        eos = torch.tensor([[tokenizer.eos_token_id]], device=model.device) if tokenizer.eos_token_id is not None else response_ids[:, :0]
        input_ids = torch.cat([prompt_ids, response_ids, eos], dim=1)
        labels = input_ids.clone()
        labels[:, :prompt_ids.shape[1]] = -100
        optimizer.zero_grad(set_to_none=True)
        # Compute standard causal language-model cross entropy on response tokens only.
        loss = model(input_ids=input_ids, labels=labels).loss
        loss.backward()
        torch.nn.utils.clip_grad_norm_(trainable, 1.0)
        optimizer.step()
        total_loss += float(loss.detach().cpu())
        del input_ids, labels, loss, prompt_ids, response_ids
    # Return the mean batch loss and release optimizer state before generation resumes.
    model.eval()
    del optimizer
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    return total_loss / max(1, len(indices))


def run(args: argparse.Namespace) -> int:
    """Run the one-task rejection sampling and SFT pilot with separate W&B tracking."""
    import torch
    import wandb
    from dotenv import load_dotenv

    # Load local credentials, task data, and a deterministic random seed.
    load_dotenv()
    os.environ.pop("WANDB_RUN_ID", None)
    os.environ.pop("WANDB_RESUME", None)
    random.seed(args.seed)
    torch.manual_seed(args.seed)
    # Keep CPU pilot work to one thread when the live trainer owns the GPU.
    if args.device == "cpu":
        torch.set_num_threads(args.cpu_threads)
    task = load_task(args.task_id)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    # Start a new isolated W&B run so metrics do not enter the active GRPO run.
    run = wandb.init(project=args.wandb_project, name=args.wandb_run_name, config={**vars(args), "task_text": task["task_text"], "task_tests": task["test_code"]}, job_type="rejection-sampling-sft-pilot", reinit=True)
    model, tokenizer = load_model(args.model, args.bf16, args.device)
    accepted: list[dict[str, Any]] = []
    trace_path = output_dir / "candidates.jsonl"
    # Measure initial greedy accuracy before any pilot updates.
    if args.resume_greedy:
        # Re-score a saved greedy completion without another model generation.
        saved_greedy = json.loads(Path(args.resume_greedy).read_text(encoding="utf-8"))
        greedy = score_candidates([{"completion": saved_greedy["completion"]}], task, args.timeout)[0]
    else:
        # Measure the policy's current greedy accuracy before any pilot updates.
        greedy = evaluate_greedy(model, tokenizer, task, args)
    wandb.log({"rs/greedy_pass": int(greedy["passed_all"]), "rs/cycle": 0})
    (output_dir / "initial_greedy.json").write_text(json.dumps(greedy, indent=2), encoding="utf-8")
    # Repeat complete-task filtering followed by one epoch over all retained solutions.
    for cycle in range(1, args.max_cycles + 1):
        cycle_started = time.perf_counter()
        generation_started = time.perf_counter()
        if cycle == 1 and args.resume_candidates:
            # Reuse an already sampled batch when correcting scoring or resuming a tiny pilot.
            with Path(args.resume_candidates).open(encoding="utf-8") as handle:
                generated = [{"completion": json.loads(line)["completion"]} for line in handle if line.strip()]
            if len(generated) != args.samples:
                raise ValueError(f"Expected {args.samples} saved candidates, found {len(generated)}.")
        else:
            # Sample a fresh batch from the policy at the start of each cycle.
            generated = generate(model, tokenizer, task["prompt"], args.samples, args.generation_batch_size, args.max_new_tokens, args.temperature)
        generation_seconds = time.perf_counter() - generation_started
        scoring_started = time.perf_counter()
        scored = score_candidates(generated, task, args.timeout)
        scoring_seconds = time.perf_counter() - scoring_started
        accepted.extend(item for item in scored if item["passed_all"])
        # Append every sample and exact test result so the pilot can be audited without reruns.
        with trace_path.open("a", encoding="utf-8") as handle:
            for item in scored:
                handle.write(json.dumps({"cycle": cycle, "task_id": task["task_id"], **item}, ensure_ascii=False) + "\n")
        sample_pass_rate = sum(item["passed_all"] for item in scored) / len(scored)
        metrics = {"rs/cycle": cycle, "rs/sample_pass_rate": sample_pass_rate, "rs/accepted_this_cycle": sum(item["passed_all"] for item in scored), "rs/accepted_total": len(accepted), "rs/samples_total": cycle * args.samples, "rs/generation_seconds": generation_seconds, "rs/scoring_seconds": scoring_seconds, "rs/elapsed_seconds": time.perf_counter() - cycle_started}
        # Stop clearly when rejection sampling has no positive example to train on.
        if not accepted:
            metrics["rs/stopped_no_accepted_examples"] = 1
            wandb.log(metrics)
            break
        sft_started = time.perf_counter()
        loss = fine_tune_one_epoch(model, tokenizer, task, accepted, args)
        sft_seconds = time.perf_counter() - sft_started
        greedy_started = time.perf_counter()
        greedy = evaluate_greedy(model, tokenizer, task, args)
        metrics.update({"rs/sft_mean_loss": loss, "rs/sft_seconds": sft_seconds, "rs/greedy_seconds": time.perf_counter() - greedy_started, "rs/greedy_pass": int(greedy["passed_all"])})
        wandb.log(metrics)
        # Save adapters only when the caller explicitly enables checkpoint saving.
        if args.save_checkpoints:
            model.save_pretrained(output_dir / f"adapter-cycle-{cycle}")
            tokenizer.save_pretrained(output_dir / f"adapter-cycle-{cycle}")
        (output_dir / f"greedy-cycle-{cycle}.json").write_text(json.dumps(greedy, indent=2), encoding="utf-8")
        if greedy["passed_all"] and sample_pass_rate >= args.target_sample_pass_rate:
            break
    # Close only this pilot's W&B client and return success only for a demonstrated pass.
    run.finish()
    return 0 if greedy["passed_all"] else 1


def main() -> None:
    """Parse pilot limits and launch the selected one-task experiment."""
    parser = argparse.ArgumentParser(description="Run a bounded single-task rejection sampling plus SFT pilot.")
    parser.add_argument("--model", required=True)
    parser.add_argument("--task-id", default="621")
    parser.add_argument("--resume-candidates", default=None)
    parser.add_argument("--resume-greedy", default=None)
    parser.add_argument("--output-dir", default="outputs/rejection-sampling-sft-task621")
    parser.add_argument("--wandb-project", default="grpo-mbpp")
    parser.add_argument("--wandb-run-name", default="mbpp-rejection-sampling-sft-task621-pilot")
    parser.add_argument("--samples", type=int, default=16)
    parser.add_argument("--generation-batch-size", type=int, default=2)
    parser.add_argument("--max-cycles", type=int, default=5)
    parser.add_argument("--target-sample-pass-rate", type=float, default=1.0)
    parser.add_argument("--max-new-tokens", type=int, default=512)
    parser.add_argument("--max-prompt-tokens", type=int, default=512)
    parser.add_argument("--max-response-tokens", type=int, default=512)
    parser.add_argument("--temperature", type=float, default=0.8)
    parser.add_argument("--learning-rate", type=float, default=1e-5)
    parser.add_argument("--timeout", type=float, default=3.0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--device", choices=["cuda", "cpu"], default="cuda")
    parser.add_argument("--cpu-threads", type=int, default=1)
    parser.add_argument("--bf16", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--save-checkpoints", action=argparse.BooleanOptionalAction, default=False)
    args = parser.parse_args()
    # Reject unsafe settings that could turn the tiny pilot into a full-data job.
    if args.samples != 16 or args.max_cycles < 1 or args.max_cycles > 5 or args.generation_batch_size < 1 or args.generation_batch_size > 2 or not 0.0 <= args.target_sample_pass_rate <= 1.0:
        parser.error("The pilot is limited to exactly 16 samples, one to five cycles, and generation batches of at most two.")
    raise SystemExit(run(args))


if __name__ == "__main__":
    main()
