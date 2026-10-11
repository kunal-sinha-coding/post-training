# This experiment loads eight MBPP tasks and a base model, samples candidates, keeps full passes, and trains one shared LoRA adapter.
# It repeats rejection sampling and response-only SFT until every sample passes or the configured cycle limit is reached.

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from pathlib import Path
from typing import Any

# Add the repository root so this script can import shared experiment helpers.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from experiments.rejection_sampling_sft import clean_completion, load_model


def load_tasks(task_ids: list[str]) -> list[dict[str, Any]]:
    """Load and normalize all selected MBPP tasks from cached Arrow files."""
    from datasets import Dataset
    from datasets.config import HF_DATASETS_CACHE
    from data import normalize_record

    wanted = {str(task_id) for task_id in task_ids}
    found: dict[str, dict[str, Any]] = {}
    cache_root = Path(HF_DATASETS_CACHE)
    # Search each cached full split until all requested task records are found.
    for arrow_path in cache_root.glob("google-research-datasets___mbpp/full/0.0.0/*/mbpp-*.arrow"):
        for row in Dataset.from_file(str(arrow_path)):
            task_id = str(row.get("task_id"))
            if task_id in wanted and task_id not in found:
                found[task_id] = normalize_record(row, visible_test_count=1)
        if len(found) == len(wanted):
            break
    # Report the exact missing IDs when the local cache is incomplete.
    missing = sorted(wanted - found.keys())
    if missing:
        raise ValueError(f"MBPP task IDs were not found in cached Arrow splits: {missing}")
    return [found[str(task_id)] for task_id in task_ids]


def generate_candidates(model: Any, tokenizer: Any, tasks: list[dict[str, Any]], samples_per_task: int, batch_size: int, max_new_tokens: int, temperature: float, greedy: bool = False) -> list[dict[str, Any]]:
    """Generate candidates for all task prompts in shared GPU batches."""
    import torch

    prompts = [(task, sample_index) for task in tasks for sample_index in range(samples_per_task)]
    outputs: list[dict[str, Any]] = []
    # Generate one bounded batch of distinct task prompts at a time.
    for start in range(0, len(prompts), batch_size):
        current = prompts[start : start + batch_size]
        encoded = tokenizer([task["prompt"] for task, _ in current], return_tensors="pt", padding=True, truncation=True, max_length=1024).to(model.device)
        input_length = encoded["input_ids"].shape[1]
        with torch.inference_mode():
            # Use sampling for candidates and deterministic decoding for controls.
            sampling = {"do_sample": False} if greedy else {"do_sample": True, "temperature": temperature, "top_p": 0.95}
            generated = model.generate(**encoded, **sampling, max_new_tokens=max_new_tokens, pad_token_id=tokenizer.pad_token_id, eos_token_id=tokenizer.eos_token_id)
        # Store each completion with its task ID and within-task sample index.
        for sequence, (task, sample_index) in zip(generated, current):
            outputs.append({"task_id": str(task["task_id"]), "sample_index": sample_index, "completion": clean_completion(tokenizer.decode(sequence[input_length:], skip_special_tokens=True)), "prompt_tokens": input_length})
        del encoded, generated
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    return outputs


def score_candidates(candidates: list[dict[str, Any]], tasks_by_id: dict[str, dict[str, Any]], timeout: float) -> list[dict[str, Any]]:
    """Score each candidate against the assertions for its own task."""
    from sandbox import score_completion

    scored = []
    # Preserve each completion and its detailed assertion results.
    for candidate in candidates:
        task = tasks_by_id[candidate["task_id"]]
        wrapped = f"Code:\n```python\n{clean_completion(candidate['completion'])}\n```"
        _, details = score_completion(wrapped, task["test_code"], timeout_seconds=timeout, reward_function="test_pass", visible_test_count=1)
        scored.append({**candidate, **details, "passed_all": bool(details.get("passed_tests") == details.get("total_tests"))})
    return scored


def train_one_epoch(model: Any, tokenizer: Any, tasks_by_id: dict[str, dict[str, Any]], accepted: list[dict[str, Any]], args: argparse.Namespace) -> float:
    """Train one shuffled response-only cross-entropy epoch over accepted candidates."""
    import torch

    trainable = [parameter for parameter in model.parameters() if parameter.requires_grad]
    optimizer = torch.optim.AdamW(trainable, lr=args.learning_rate)
    indices = list(range(len(accepted)))
    random.Random(args.seed + len(accepted)).shuffle(indices)
    total_loss = 0.0
    model.train()
    # Update once for each accepted completion and mask its task prompt from loss.
    for index in indices:
        item = accepted[index]
        task = tasks_by_id[item["task_id"]]
        prompt_ids = tokenizer(task["prompt"], add_special_tokens=True, truncation=True, max_length=args.max_prompt_tokens, return_tensors="pt")["input_ids"].to(model.device)
        response_ids = tokenizer(clean_completion(item["completion"]), add_special_tokens=False, truncation=True, max_length=args.max_response_tokens, return_tensors="pt")["input_ids"].to(model.device)
        eos = torch.tensor([[tokenizer.eos_token_id]], device=model.device) if tokenizer.eos_token_id is not None else response_ids[:, :0]
        input_ids = torch.cat([prompt_ids, response_ids, eos], dim=1)
        labels = input_ids.clone()
        labels[:, :prompt_ids.shape[1]] = -100
        optimizer.zero_grad(set_to_none=True)
        # Compute causal language-model loss on response tokens only.
        loss = model(input_ids=input_ids, labels=labels).loss
        loss.backward()
        torch.nn.utils.clip_grad_norm_(trainable, 1.0)
        optimizer.step()
        total_loss += float(loss.detach().cpu())
        del input_ids, labels, loss, prompt_ids, response_ids
    # Release optimizer state before the next sampling cycle.
    model.eval()
    del optimizer
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    return total_loss / max(1, len(indices))


def run(args: argparse.Namespace) -> int:
    """Run shared eight-task rejection sampling and SFT with separate W&B tracking."""
    import torch
    import wandb
    from dotenv import load_dotenv

    # Load credentials and seed all local random generators.
    load_dotenv()
    os.environ.pop("WANDB_RUN_ID", None)
    os.environ.pop("WANDB_RESUME", None)
    random.seed(args.seed)
    torch.manual_seed(args.seed)
    tasks = load_tasks(args.task_ids)
    tasks_by_id = {str(task["task_id"]): task for task in tasks}
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    # Start an isolated W&B run with the selected task prompts and tests.
    run = wandb.init(project=args.wandb_project, name=args.wandb_run_name, config={**vars(args), "task_texts": {task_id: task["task_text"] for task_id, task in tasks_by_id.items()}, "task_tests": {task_id: task["test_code"] for task_id, task in tasks_by_id.items()}}, job_type="rejection-sampling-sft-eight-task-pilot", reinit=True)
    model, tokenizer = load_model(args.model, args.bf16, args.device)
    accepted: list[dict[str, Any]] = []
    trace_path = output_dir / "candidates.jsonl"
    # Measure greedy pass rate on every task before the first update.
    greedy_candidates = generate_candidates(model, tokenizer, tasks, 1, args.generation_batch_size, args.max_new_tokens, args.temperature, greedy=True)
    greedy_scores = score_candidates(greedy_candidates, tasks_by_id, args.timeout)
    greedy_rate = sum(item["passed_all"] for item in greedy_scores) / len(greedy_scores)
    (output_dir / "initial_greedy.json").write_text(json.dumps(greedy_scores, indent=2), encoding="utf-8")
    wandb.log({"rs/greedy_pass_rate": greedy_rate, "rs/greedy_pass_count": sum(item["passed_all"] for item in greedy_scores), "rs/greedy_task_count": len(tasks), "rs/cycle": 0})
    # Repeat joint full-pass filtering and SFT until every sampled candidate passes.
    for cycle in range(1, args.max_cycles + 1):
        cycle_started = time.perf_counter()
        generation_started = time.perf_counter()
        generated = generate_candidates(model, tokenizer, tasks, args.samples_per_task, args.generation_batch_size, args.max_new_tokens, args.temperature)
        generation_seconds = time.perf_counter() - generation_started
        scoring_started = time.perf_counter()
        scored = score_candidates(generated, tasks_by_id, args.timeout)
        scoring_seconds = time.perf_counter() - scoring_started
        accepted.extend(item for item in scored if item["passed_all"])
        # Append every candidate with its task ID and assertion outcomes.
        with trace_path.open("a", encoding="utf-8") as handle:
            for item in scored:
                handle.write(json.dumps({"cycle": cycle, **item}, ensure_ascii=False) + "\n")
        pass_count = sum(item["passed_all"] for item in scored)
        sample_rate = pass_count / len(scored)
        per_task = {task_id: sum(item["passed_all"] for item in scored if item["task_id"] == task_id) / args.samples_per_task for task_id in tasks_by_id}
        metrics = {"rs/cycle": cycle, "rs/sample_pass_rate": sample_rate, "rs/accepted_this_cycle": pass_count, "rs/accepted_total": len(accepted), "rs/samples_total": cycle * len(scored), "rs/generation_seconds": generation_seconds, "rs/scoring_seconds": scoring_seconds, **{f"rs/task_{task_id}_pass_rate": rate for task_id, rate in per_task.items()}}
        # Stop if no task candidate can train the shared adapter.
        if not accepted:
            metrics["rs/stopped_no_accepted_examples"] = 1
            metrics["rs/elapsed_seconds"] = time.perf_counter() - cycle_started
            wandb.log(metrics)
            break
        sft_started = time.perf_counter()
        loss = train_one_epoch(model, tokenizer, tasks_by_id, accepted, args)
        sft_seconds = time.perf_counter() - sft_started
        greedy_started = time.perf_counter()
        greedy_candidates = generate_candidates(model, tokenizer, tasks, 1, args.generation_batch_size, args.max_new_tokens, args.temperature, greedy=True)
        greedy_scores = score_candidates(greedy_candidates, tasks_by_id, args.timeout)
        greedy_rate = sum(item["passed_all"] for item in greedy_scores) / len(greedy_scores)
        metrics.update({"rs/sft_mean_loss": loss, "rs/sft_seconds": sft_seconds, "rs/greedy_seconds": time.perf_counter() - greedy_started, "rs/greedy_pass_rate": greedy_rate, "rs/greedy_pass_count": sum(item["passed_all"] for item in greedy_scores), "rs/elapsed_seconds": time.perf_counter() - cycle_started})
        wandb.log(metrics)
        # Save the adapter and greedy outcomes after each completed update.
        model.save_pretrained(output_dir / f"adapter-cycle-{cycle}")
        tokenizer.save_pretrained(output_dir / f"adapter-cycle-{cycle}")
        (output_dir / f"greedy-cycle-{cycle}.json").write_text(json.dumps(greedy_scores, indent=2), encoding="utf-8")
        if sample_rate >= args.target_sample_pass_rate:
            break
    # Close this experiment's W&B run and return success only when the target was met.
    run.finish()
    return 0 if sample_rate >= args.target_sample_pass_rate else 1


def main() -> None:
    """Parse the fixed eight-task pilot limits and launch the experiment."""
    parser = argparse.ArgumentParser(description="Run eight-task rejection sampling plus SFT.")
    parser.add_argument("--model", required=True)
    parser.add_argument("--task-ids", nargs=8, required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--wandb-project", default="grpo-mbpp")
    parser.add_argument("--wandb-run-name", required=True)
    parser.add_argument("--samples-per-task", type=int, default=16)
    parser.add_argument("--generation-batch-size", type=int, default=16)
    parser.add_argument("--max-cycles", type=int, default=20)
    parser.add_argument("--target-sample-pass-rate", type=float, default=1.0)
    parser.add_argument("--max-new-tokens", type=int, default=512)
    parser.add_argument("--max-prompt-tokens", type=int, default=512)
    parser.add_argument("--max-response-tokens", type=int, default=512)
    parser.add_argument("--temperature", type=float, default=0.8)
    parser.add_argument("--learning-rate", type=float, default=1e-5)
    parser.add_argument("--timeout", type=float, default=3.0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--device", choices=["cuda", "cpu"], default="cuda")
    parser.add_argument("--bf16", action=argparse.BooleanOptionalAction, default=True)
    args = parser.parse_args()
    # Keep the pilot at eight tasks, 16 samples each, and bounded generation batches.
    if len(set(args.task_ids)) != 8 or args.samples_per_task != 16 or args.generation_batch_size < 1 or args.generation_batch_size > 16 or args.max_cycles < 1 or not 0.0 <= args.target_sample_pass_rate <= 1.0:
        parser.error("The batch pilot requires eight unique task IDs, 16 samples per task, and a generation batch size from one to 16.")
    raise SystemExit(run(args))


if __name__ == "__main__":
    main()
