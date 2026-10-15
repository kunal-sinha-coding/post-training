# This script makes ten independent Jev decisions for each EvalPlus task, saves every response, and measures three vote rules and each single call against MBPP and MBPP+ labels.
# Jev receives only task prompts; benchmark labels are loaded separately and used only after all decisions are complete.

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import statistics
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from experiments.evaluate_jev_router import query_jev


# Return accuracy and confusion counts for one set of binary decisions.
def binary_metrics(labels: list[int], predictions: list[int]) -> dict[str, Any]:
    # Count correct and incorrect positive and negative decisions.
    tp = sum(label == 1 and prediction == 1 for label, prediction in zip(labels, predictions, strict=True))
    fp = sum(label == 0 and prediction == 1 for label, prediction in zip(labels, predictions, strict=True))
    tn = sum(label == 0 and prediction == 0 for label, prediction in zip(labels, predictions, strict=True))
    fn = sum(label == 1 and prediction == 0 for label, prediction in zip(labels, predictions, strict=True))
    return {
        "accuracy": (tp + tn) / len(labels) if labels else 0.0,
        "true_positive": tp,
        "false_positive": fp,
        "true_negative": tn,
        "false_negative": fn,
        "positive_prediction_fraction": sum(predictions) / len(predictions) if predictions else 0.0,
    }


# Score every missing task and call pair while saving responses as they finish.
def score_calls(rows: list[dict[str, Any]], cache_path: Path, cache: dict[tuple[str, int], dict[str, Any]], api_key: str, model: str, workers: int) -> None:
    # Build one request for each uncached task and call index.
    missing = [(row, call_index) for row in rows for call_index in range(1, 11) if (str(row["task_id"]), call_index) not in cache]
    if not missing:
        print("All 10 calls per task are already saved.", flush=True)
        return

    # Run independent API requests in parallel and keep each completed response resumable.
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(
                query_jev,
                str(row["prompt"]),
                model,
                api_key,
                90.0,
                5,
                "Assume one first-try, greedy generation by Qwen/Qwen2.5-Coder-0.5B-Instruct for this programming task, checked against all task tests. Can the model solve it and pass every test?",
            ): (row, call_index)
            for row, call_index in missing
        }
        with cache_path.open("a", encoding="utf-8") as handle:
            for completed, future in enumerate(concurrent.futures.as_completed(futures), start=1):
                row, call_index = futures[future]
                result = future.result()
                record = {
                    "task_id": str(row["task_id"]),
                    "call_index": call_index,
                    "prompt_sha256": hashlib.sha256(str(row["prompt"]).encode("utf-8")).hexdigest(),
                    **result,
                }
                handle.write(json.dumps(record) + "\n")
                handle.flush()
                cache[(record["task_id"], call_index)] = record
                if completed % 100 == 0 or completed == len(missing):
                    print(json.dumps({"completed_calls": completed, "pending_calls": len(missing)}), flush=True)


# Compute individual-call and aggregated-vote accuracies for both benchmark label sets.
def summarize(rows: list[dict[str, Any]], cache: dict[tuple[str, int], dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    # Build aligned labels and ten binary votes for each task.
    labels = {
        "mbpp": [int(row["label_mbpp"]) for row in rows],
        "mbpp_plus": [int(row["label_mbpp_plus"]) for row in rows],
    }
    votes = [[int(float(cache[(str(row["task_id"]), call_index)]["probability"]) >= 0.5) for call_index in range(1, 11)] for row in rows]

    # Apply strict majority, any-yes, and unanimous-yes decision rules.
    yes_counts = [sum(task_votes) for task_votes in votes]
    aggregates = {
        "majority_yes_strict": [int(count > 5) for count in yes_counts],
        "yes_if_any_call_says_yes": [int(count >= 1) for count in yes_counts],
        "yes_only_if_all_calls_say_yes": [int(count == 10) for count in yes_counts],
    }

    # Measure all vote rules and each individual call against both held-out labels.
    metrics: dict[str, Any] = {"task_count": len(rows), "call_count": len(rows) * 10, "decision_threshold": 0.5, "tie_policy": "A 5-5 majority tie is no.", "vote_rules": {}, "single_call_accuracy": {}}
    for label_name, split_labels in labels.items():
        metrics["vote_rules"][label_name] = {rule: binary_metrics(split_labels, predictions) for rule, predictions in aggregates.items()}
        call_accuracies = [binary_metrics(split_labels, [task_votes[index] for task_votes in votes])["accuracy"] for index in range(10)]
        metrics["single_call_accuracy"][label_name] = {
            "by_call": call_accuracies,
            "mean": statistics.mean(call_accuracies),
            "standard_deviation": statistics.pstdev(call_accuracies),
        }

    # Save per-task labels, individual decisions, and aggregate predictions for audit.
    predictions = []
    for row, task_votes, count in zip(rows, votes, yes_counts, strict=True):
        predictions.append({
            "task_id": str(row["task_id"]),
            "label_mbpp": int(row["label_mbpp"]),
            "label_mbpp_plus": int(row["label_mbpp_plus"]),
            "probabilities": [float(cache[(str(row["task_id"]), call_index)]["probability"]) for call_index in range(1, 11)],
            "votes_yes": count,
            "majority_yes_strict": int(count > 5),
            "yes_if_any_call_says_yes": int(count >= 1),
            "yes_only_if_all_calls_say_yes": int(count == 10),
        })
    return metrics, predictions


# Load the EvalPlus task prompts, score ten calls per task, and write reproducible metrics.
def main() -> None:
    # Parse paths and request concurrency, then load local API credentials.
    parser = argparse.ArgumentParser()
    parser.add_argument("--eval-data", type=Path, default=Path("outputs/router-evalplus-greedy-dual-label-20261013/router_evalplus_labels.jsonl"))
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/router-jev-vote-ensemble-evalplus-20261015"))
    parser.add_argument("--model", default="jev-latest")
    parser.add_argument("--workers", type=int, default=48)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    load_dotenv(root / ".env")
    api_key = os.getenv("JEV_API_KEY")
    if not api_key:
        raise RuntimeError("JEV_API_KEY is missing from the repository .env file.")

    # Load evaluation prompts and resumable Jev responses without exposing labels to Jev.
    rows = [json.loads(line) for line in args.eval_data.read_text(encoding="utf-8").splitlines() if line.strip()]
    args.output_dir.mkdir(parents=True, exist_ok=True)
    cache_path = args.output_dir / "jev_calls.jsonl"
    cache: dict[tuple[str, int], dict[str, Any]] = {}
    if cache_path.exists():
        for line in cache_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                record = json.loads(line)
                cache[(str(record["task_id"]), int(record["call_index"]))] = record

    # Request all missing calls and summarize only after the prediction cache is complete.
    score_calls(rows, cache_path, cache, api_key, args.model, args.workers)
    metrics, predictions = summarize(rows, cache)

    # Record the resolved model, prompt policy, data hash, usage, and local artifacts.
    result = {
        "experiment": "jev-ten-call-vote-ensemble-evalplus-20261015",
        "model_requested": args.model,
        "model_returned": sorted({cache[(str(row["task_id"]), call_index)]["model_returned"] for row in rows for call_index in range(1, 11)}),
        "question": "Can one greedy Qwen/Qwen2.5-Coder-0.5B-Instruct completion pass every test for this programming task?",
        "repeated_prompt_policy": "Ten independent API calls with the same prompt and question per task; no seed control is exposed by the API.",
        "decision_threshold": 0.5,
        "majority_tie_policy": "A 5-5 tie is no.",
        "eval_task_count": len(rows),
        "api_call_count": len(rows) * 10,
        "eval_data": str(args.eval_data),
        "eval_data_sha256": hashlib.sha256(args.eval_data.read_bytes()).hexdigest(),
        "concurrent_requests": args.workers,
        "metrics": metrics,
        "token_usage": {
            "input_tokens": sum(int(record["input_tokens"]) for record in cache.values()),
            "output_tokens": sum(int(record["output_tokens"]) for record in cache.values()),
        },
        "artifacts": {
            "raw_calls": str(cache_path),
            "predictions": str(args.output_dir / "predictions.jsonl"),
            "metrics": str(args.output_dir / "metrics.json"),
        },
    }
    (args.output_dir / "predictions.jsonl").write_text("".join(json.dumps(row) + "\n" for row in predictions), encoding="utf-8")
    (args.output_dir / "metrics.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2), flush=True)


if __name__ == "__main__":
    main()
