"""Score saved candidate answers with Qwen 7B and compare likelihood aggregators.

The script loads each MBPP task, standard test, and saved candidate output,
scores the answer text with teacher-forced Qwen 7B mean token log likelihood,
caches every per-test score, ranks candidates with several answer-independent
aggregators, and measures Pass@K only after each ranking is fixed.
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from llm_output_verifier import DATA, EVAL, OBS


# Decode the typed observation representation into a JSON value for scoring.
def decode_value(text: str) -> object:
    value = json.loads(text)
    kind, payload = value
    if kind in {"none", "bool", "int", "str", "float"}:
        return payload
    if kind in {"list", "tuple", "set", "frozenset"}:
        return [decode_value(json.dumps(item)) for item in payload]
    if kind == "dict":
        return {str(decode_value(json.dumps(key))): decode_value(json.dumps(item)) for key, item in payload}
    return {"__unsupported_type__": kind}


# Render one observed answer in the JSON format used by the answer predictor.
def answer_text(value: str) -> str:
    return json.dumps(decode_value(value), ensure_ascii=False, separators=(",", ":"))


# Build the shared task-and-test prompt whose answer continuation is scored.
def build_prompt(task: dict, test_index: int) -> str:
    test = {"test_index": test_index, "inputs": task["base_input"][test_index]}
    return (
        "Solve the following Python programming task mentally. "
        "Predict the exact returned value for the supplied standard test input. "
        "The answer is a JSON value and must contain no explanation.\n\n"
        f"TASK:\n{task['prompt']}\n\n"
        f"ENTRY POINT: {task['entry_point']}\n\n"
        f"STANDARD TEST:\n{json.dumps(test, ensure_ascii=False)}\n\n"
        "ANSWER:\n"
    )


# Load the saved base-test outputs for all ten candidates of one task.
def load_scores_input(task_id: str, evaluations: dict) -> list[list[str | None]]:
    rows = []
    for candidate_index in range(len(evaluations[task_id])):
        observation = json.loads((OBS / f"{task_id.replace('/', '_')}_{candidate_index}.json").read_text())
        by_index = {
            row["index"]: answer_text(row["value"])
            for row in observation["tests"]
            if row["suite"] == "base_input" and row["status"] == "returned" and "value" in row
        }
        rows.append([by_index.get(index) for index in range(3)])
    return rows


# Compute mean token log likelihood for a batch of prompt and answer pairs.
def score_batch(model: object, tokenizer: object, pairs: list[tuple[str, str]], max_length: int) -> list[float]:
    encoded = []
    target_lengths = []
    for prompt, answer in pairs:
        prompt_ids = tokenizer(prompt, add_special_tokens=False)["input_ids"]
        target_ids = tokenizer(answer, add_special_tokens=False)["input_ids"]
        ids = (prompt_ids + target_ids)[-max_length:]
        target_start = max(0, len(prompt_ids) - max(0, max_length - len(prompt_ids) - len(target_ids)))
        target_start = len(ids) - len(target_ids)
        encoded.append(ids)
        target_lengths.append((target_start, len(target_ids)))
    width = max(len(ids) for ids in encoded)
    pad = tokenizer.pad_token_id
    input_ids = torch.full((len(encoded), width), pad, dtype=torch.long, device=model.device)
    attention = torch.zeros_like(input_ids)
    offsets = []
    for row_index, ids in enumerate(encoded):
        input_ids[row_index, :len(ids)] = torch.tensor(ids, device=model.device)
        attention[row_index, :len(ids)] = 1
        offsets.append((target_lengths[row_index][0], target_lengths[row_index][1], len(ids)))
    with torch.inference_mode():
        logits = model(input_ids=input_ids, attention_mask=attention).logits
    scores = []
    for row_index, (target_start, target_length, sequence_length) in enumerate(offsets):
        if target_start == 0 or target_length == 0 or target_start + target_length > sequence_length:
            scores.append(float("-inf"))
            continue
        token_logits = logits[row_index, target_start - 1:target_start + target_length - 1]
        token_ids = input_ids[row_index, target_start:target_start + target_length]
        log_probs = torch.log_softmax(token_logits.float(), dim=-1)
        scores.append(float(log_probs.gather(1, token_ids.unsqueeze(1)).mean().item()))
    return scores


# Aggregate per-test candidate scores into one task-level ranking score.
def aggregate(values: list[float], strategy: str) -> float:
    finite = [value for value in values if isinstance(value, (int, float)) and math.isfinite(value)]
    if not finite:
        return float("-inf")
    if strategy == "mean":
        return statistics.fmean(finite)
    if strategy == "median":
        return statistics.median(finite)
    if strategy == "minimum":
        return min(finite)
    if strategy == "trimmed_mean":
        trimmed = finite[1:-1] if len(finite) >= 3 else finite
        return statistics.fmean(trimmed)
    if strategy == "weighted_mean":
        weights = list(range(1, len(finite) + 1))
        return sum(weight * value for weight, value in zip(weights, finite)) / sum(weights)
    if strategy == "worst_penalty":
        mean = statistics.fmean(finite)
        return mean - 0.5 * (mean - min(finite))
    raise ValueError(f"Unknown strategy: {strategy}")


# Rank candidates independently on each test and sum their ranks.
def rank_sum(values: list[list[float]]) -> list[int]:
    scores = [0] * len(values)
    test_count = max((len(row) for row in values), default=0)
    for test_index in range(test_count):
        # Treat missing or failed candidate outputs as worse than every returned answer.
        test_values = [row[test_index] if test_index < len(row) and isinstance(row[test_index], (int, float)) else float("-inf") for row in values]
        order = sorted(range(len(values)), key=lambda index: (-test_values[index], index))
        for rank, candidate_index in enumerate(order):
            scores[candidate_index] += rank
    return scores


# Build all candidate rankings from the cached per-test likelihood scores.
def rankings_for_task(scores: list[list[float]]) -> dict[str, list[int]]:
    strategies = ("mean", "median", "minimum", "trimmed_mean", "weighted_mean", "rank_sum", "worst_penalty")
    rankings = {}
    rank_scores = rank_sum(scores)
    for strategy in strategies:
        if strategy == "rank_sum":
            rankings[strategy] = sorted(range(len(scores)), key=lambda index: (rank_scores[index], index))
        else:
            rankings[strategy] = sorted(range(len(scores)), key=lambda index: (-aggregate(scores[index], strategy), index))
    return rankings


# Compute MBPP and MBPP+ Pass@K after a fixed candidate ranking.
def pass_curves(task_ids: list[str], rankings: dict[str, dict[str, list[int]]], evaluations: dict) -> dict:
    report = {}
    for strategy in rankings[task_ids[0]]:
        report[strategy] = {}
        for suite, field in (("base", "base_status"), ("plus", "plus_status")):
            curve = {}
            for k in range(1, 11):
                hits = sum(
                    any(evaluations[task_id][index][field] == "pass" for index in rankings[task_id][strategy][:k])
                    for task_id in task_ids
                )
                curve[f"pass_at_{k}"] = hits / len(task_ids)
            report[strategy][suite] = curve
    return report


# Score every uncached candidate/test answer and save progress after each batch.
def score_all(args: argparse.Namespace, model: object, tokenizer: object, tasks: dict, evaluations: dict, cached: dict) -> dict:
    pending = []
    for task_id in args.task_ids:
        candidates = load_scores_input(task_id, evaluations)
        task_scores = cached.setdefault("scores", {}).setdefault(task_id, [[] for _ in candidates])
        # Represent candidates with no returned outputs as three missing scores.
        for candidate_index in range(len(candidates)):
            if len(task_scores[candidate_index]) == 0:
                task_scores[candidate_index] = [None] * len(candidates[candidate_index])
        for candidate_index, answers in enumerate(candidates):
            if len(task_scores[candidate_index]) == len(answers):
                continue
            for test_index, answer in enumerate(answers):
                if answer is not None:
                    pending.append((task_id, candidate_index, test_index, build_prompt(tasks[task_id], test_index), answer))
    for start in range(0, len(pending), args.batch_size):
        batch = pending[start:start + args.batch_size]
        values = score_batch(model, tokenizer, [(row[3], row[4]) for row in batch], args.max_length)
        for (task_id, candidate_index, test_index, _, _), value in zip(batch, values):
            row = cached["scores"][task_id][candidate_index]
            while len(row) <= test_index:
                row.append(None)
            row[test_index] = value
        args.output.write_text(json.dumps(cached, indent=2) + "\n")
        print(f"Scored {min(start + len(batch), len(pending))}/{len(pending)} candidate-test answers", flush=True)
    return cached


# Run scoring, ranking, and post-selection evaluation for the full suite.
def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--tasks", type=int, default=399)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--max-length", type=int, default=4096)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    data = {row["task_id"]: row for row in map(json.loads, DATA.open())}
    evaluations = json.loads(EVAL.read_text())["eval"]
    args.task_ids = list(evaluations)[:args.tasks]
    cached = json.loads(args.output.read_text()) if args.output.exists() else {"scores": {}}
    tokenizer = AutoTokenizer.from_pretrained(args.model, trust_remote_code=False)
    tokenizer.padding_side = "right"
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(args.model, torch_dtype=torch.bfloat16, device_map="auto", trust_remote_code=False)
    model.eval()
    cached = score_all(args, model, tokenizer, data, evaluations, cached)
    rankings = {task_id: rankings_for_task(cached["scores"][task_id]) for task_id in args.task_ids}
    artifact = {
        "experiment": "qwen7b-answer-loglikelihood-reranking-399",
        "model": args.model,
        "tasks": args.task_ids,
        "score_definition": "Mean log probability per answer token conditioned on task prompt, entry point, one standard test, and ANSWER prefix.",
        "selection_uses_correctness_labels": False,
        "strategies": ["mean", "median", "minimum", "trimmed_mean", "weighted_mean", "rank_sum", "worst_penalty"],
        "scores": cached["scores"],
        "rankings": rankings,
        "metrics": pass_curves(args.task_ids, rankings, evaluations),
    }
    args.report.write_text(json.dumps(artifact, indent=2) + "\n")
    print(json.dumps(artifact["metrics"], indent=2))


if __name__ == "__main__":
    main()
