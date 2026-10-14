# This script asks Jev whether Qwen2.5-Coder-0.5B-Instruct will solve each task, caches each probability, computes router metrics, and logs the experiment to W&B.
# It uses existing one-shot Qwen labels for the 591 MBPP training tasks and 378 EvalPlus tasks.

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import math
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


# Ask Jev for the probability that the small Qwen model passes every test on one greedy completion.
def query_jev(prompt: str, model: str, api_key: str, timeout: float, retries: int) -> dict[str, Any]:
    # Send one typed yes-or-no decision and retry temporary HTTP or network failures.
    payload = {
        "model": model,
        "state": prompt,
        "questions": {
            "qwen_pass": {
                "type": "noul",
                "instructions": "Assume exactly one first-try, greedy generation by Qwen/Qwen2.5-Coder-0.5B-Instruct for this programming task, with its completion checked against all task tests. Is the model likely to pass every test?",
                "criteria": {
                    "true": "The model passes every test on its first completion.",
                    "false": "The model does not pass every test on its first completion.",
                },
            }
        },
    }
    request = urllib.request.Request(
        "https://api.typesafe.ai/v1/systemone",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                result = json.loads(response.read())
            probability = float(result["answers"]["qwen_pass"]["noul"])
            if not 0 <= probability <= 1:
                raise ValueError("Jev returned a probability outside [0, 1].")
            return {
                "probability": probability,
                "model_returned": result.get("model"),
                "input_tokens": int(result.get("usage", {}).get("input_tokens", 0)),
                "output_tokens": int(result.get("usage", {}).get("output_tokens", 0)),
            }
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
            if attempt >= retries:
                raise RuntimeError(f"Jev request failed after {retries + 1} attempts: {type(error).__name__}") from error
            time.sleep(min(2**attempt, 30))
    raise RuntimeError("Jev request did not return a result.")


# Compute binary retrieval metrics from labels and Jev probabilities.
def binary_metrics(labels: list[int], probabilities: list[float], threshold: float = 0.5) -> dict[str, Any]:
    # Convert probabilities to labels and count the confusion matrix entries.
    predictions = [int(probability >= threshold) for probability in probabilities]
    tp = sum(label == 1 and prediction == 1 for label, prediction in zip(labels, predictions, strict=True))
    fp = sum(label == 0 and prediction == 1 for label, prediction in zip(labels, predictions, strict=True))
    tn = sum(label == 0 and prediction == 0 for label, prediction in zip(labels, predictions, strict=True))
    fn = sum(label == 1 and prediction == 0 for label, prediction in zip(labels, predictions, strict=True))
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    return {
        "accuracy": (tp + tn) / len(labels) if labels else 0.0,
        "precision": precision,
        "recall": recall,
        "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0,
        "true_positive": tp,
        "false_positive": fp,
        "true_negative": tn,
        "false_negative": fn,
        "positive_prediction_fraction": sum(predictions) / len(predictions) if predictions else 0.0,
    }


# Compute probability ranking metrics with exact ties grouped.
def ranking_metrics(labels: list[int], probabilities: list[float]) -> dict[str, Any]:
    # Accumulate average precision and trapezoidal PR and ROC areas at each unique score.
    ordered = sorted(zip(probabilities, labels, strict=True), reverse=True)
    positives = sum(labels)
    negatives = len(labels) - positives
    tp = fp = 0
    previous_recall = previous_fpr = 0.0
    previous_precision = 1.0
    average_precision = pr_area = roc_area = 0.0
    index = 0
    while index < len(ordered):
        score = ordered[index][0]
        while index < len(ordered) and ordered[index][0] == score:
            label = ordered[index][1]
            tp += label
            fp += 1 - label
            index += 1
        precision = tp / (tp + fp)
        recall = tp / positives if positives else 0.0
        fpr = fp / negatives if negatives else 0.0
        average_precision += (recall - previous_recall) * precision
        pr_area += (recall - previous_recall) * (precision + previous_precision) / 2
        roc_area += (fpr - previous_fpr) * (recall + previous_recall) / 2
        previous_recall, previous_fpr, previous_precision = recall, fpr, precision
    return {
        "auprc": average_precision,
        "average_precision": average_precision,
        "pr_auc_trapezoidal": pr_area,
        "roc_auc": roc_area if positives and negatives else None,
        "positive_prevalence": positives / len(labels) if labels else 0.0,
    }


# Calculate log loss, threshold metrics, and ranking metrics for one labeled split.
def evaluate_split(labels: list[int], probabilities: list[float]) -> dict[str, Any]:
    # Report default-threshold scores, retrieval areas, and all requested threshold sweeps.
    clipped = [min(max(probability, 1e-12), 1 - 1e-12) for probability in probabilities]
    log_loss = -sum(label * math.log(probability) + (1 - label) * math.log(1 - probability) for label, probability in zip(labels, clipped, strict=True)) / len(labels)
    metrics = binary_metrics(labels, probabilities)
    metrics.update(ranking_metrics(labels, probabilities))
    metrics["loss"] = log_loss
    metrics["threshold_metrics"] = {
        f"threshold_{value / 10:.1f}": binary_metrics(labels, probabilities, value / 10)
        for value in range(1, 10)
    }
    return metrics


# Load cached Jev scores and infer only tasks that have no saved prediction.
def score_split(split: str, rows: list[dict[str, Any]], label_keys: list[str], cache: dict[tuple[str, str], dict[str, Any]], output_path: Path, model: str, api_key: str, timeout: float, retries: int, workers: int) -> list[dict[str, Any]]:
    # Preserve completed calls in JSONL as each concurrent inference finishes.
    missing = []
    scored = []
    for row in rows:
        key = (split, str(row["task_id"]))
        if key in cache:
            scored.append(cache[key])
        else:
            missing.append((key, row))
    if missing:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(query_jev, str(row["prompt"]), model, api_key, timeout, retries): (key, row)
                for key, row in missing
            }
            with output_path.open("a", encoding="utf-8") as handle:
                for future in concurrent.futures.as_completed(futures):
                    key, row = futures[future]
                    result = future.result()
                    record = {
                        "split": split,
                        "task_id": key[1],
                        "prompt_sha256": hashlib.sha256(str(row["prompt"]).encode("utf-8")).hexdigest(),
                        **result,
                    }
                    handle.write(json.dumps(record) + "\n")
                    handle.flush()
                    cache[key] = record
                    scored.append(record)
                    if len(cache) % 50 == 0:
                        print(json.dumps({"scored_tasks": len(cache), "new_split": split}), flush=True)
    by_id = {(record["split"], record["task_id"]): record for record in scored}
    return [by_id[(split, str(row["task_id"]))] if (split, str(row["task_id"])) in by_id else cache[(split, str(row["task_id"]))] for row in rows]


# Score the training and EvalPlus prompts, then save and log the same router metrics as the MiniLM runs.
def main() -> None:
    # Parse inputs and load local secrets before starting the remote inference run.
    parser = argparse.ArgumentParser()
    parser.add_argument("--train-data", type=Path, default=Path("outputs/router-mbpp-original-one-shot-20261013/router_dataset.jsonl"))
    parser.add_argument("--eval-data", type=Path, default=Path("outputs/router-evalplus-greedy-dual-label-20261013/router_evalplus_labels.jsonl"))
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/router-jev-original-evalplus-20261014"))
    parser.add_argument("--model", default="jev-latest")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--timeout", type=float, default=90)
    parser.add_argument("--retries", type=int, default=4)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    load_dotenv(root / ".env")
    api_key = os.getenv("JEV_API_KEY")
    if not api_key:
        raise RuntimeError("JEV_API_KEY is missing from the repository .env file.")
    if not os.getenv("WANDB_API_KEY"):
        raise RuntimeError("WANDB_API_KEY is missing from the repository .env file.")

    # Read both labeled datasets and load any task scores saved by a previous partial run.
    train_rows = [json.loads(line) for line in args.train_data.read_text(encoding="utf-8").splitlines() if line.strip()]
    eval_rows = [json.loads(line) for line in args.eval_data.read_text(encoding="utf-8").splitlines() if line.strip()]
    args.output_dir.mkdir(parents=True, exist_ok=True)
    cache_path = args.output_dir / "jev_predictions.jsonl"
    cache: dict[tuple[str, str], dict[str, Any]] = {}
    if cache_path.exists():
        for line in cache_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                record = json.loads(line)
                cache[(record["split"], str(record["task_id"]))] = record

    # Query Jev for each missing training and evaluation prompt while retaining resumable scores.
    train_predictions = score_split("train", train_rows, ["label_mbpp"], cache, cache_path, args.model, api_key, args.timeout, args.retries, args.workers)
    eval_predictions = score_split("evalplus", eval_rows, ["label_mbpp", "label_mbpp_plus"], cache, cache_path, args.model, api_key, args.timeout, args.retries, args.workers)
    train_probabilities = [float(record["probability"]) for record in train_predictions]
    eval_probabilities = [float(record["probability"]) for record in eval_predictions]
    train_labels = [int(row["label_mbpp"]) for row in train_rows]
    eval_mbpp_labels = [int(row["label_mbpp"]) for row in eval_rows]
    eval_plus_labels = [int(row["label_mbpp_plus"]) for row in eval_rows]

    # Compute all benchmark metrics against the same one-shot Qwen labels as prior router runs.
    metrics = {
        "train": evaluate_split(train_labels, train_probabilities),
        "evalplus_mbpp": evaluate_split(eval_mbpp_labels, eval_probabilities),
        "evalplus_mbpp_plus": evaluate_split(eval_plus_labels, eval_probabilities),
    }
    result = {
        "experiment": "jev-zero-shot-router-qwen05-one-shot-labels-20261014",
        "model_requested": args.model,
        "model_returned": sorted({record["model_returned"] for record in train_predictions + eval_predictions}),
        "question": "Probability that one greedy Qwen/Qwen2.5-Coder-0.5B-Instruct completion passes every task test.",
        "decision_threshold": 0.5,
        "training_count": len(train_rows),
        "eval_count": len(eval_rows),
        "train_data": str(args.train_data),
        "eval_data": str(args.eval_data),
        "metrics": metrics,
        "token_usage": {
            "input_tokens": sum(int(record["input_tokens"]) for record in train_predictions + eval_predictions),
            "output_tokens": sum(int(record["output_tokens"]) for record in train_predictions + eval_predictions),
        },
        "artifacts": {
            "predictions": str(args.output_dir / "predictions.jsonl"),
            "raw_scores": str(cache_path),
            "metrics": str(args.output_dir / "metrics.json"),
        },
    }
    predictions_path = args.output_dir / "predictions.jsonl"
    with predictions_path.open("w", encoding="utf-8") as handle:
        for split, rows, records, labels in (
            ("train", train_rows, train_predictions, train_labels),
            ("evalplus", eval_rows, eval_predictions, eval_mbpp_labels),
        ):
            for row, record, label in zip(rows, records, labels, strict=True):
                probability = float(record["probability"])
                handle.write(json.dumps({
                    "split": split,
                    "task_id": str(row["task_id"]),
                    "label_mbpp": label,
                    "label_mbpp_plus": row.get("label_mbpp_plus"),
                    "prediction": int(probability >= 0.5),
                    "positive_probability": probability,
                    "model_returned": record["model_returned"],
                }) + "\n")
    metrics_path = args.output_dir / "metrics.json"
    metrics_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    # Log final metrics and threshold sweeps to W&B and upload reproducibility artifacts.
    import wandb

    run = wandb.init(
        entity="kunal-personal",
        project="grpo-mbpp",
        name="router-jev-original-evalplus-20261014",
        job_type="router-evaluation",
        config={
            "model_requested": args.model,
            "model_returned": result["model_returned"],
            "decision_api": "https://api.typesafe.ai/v1/systemone",
            "task_target": result["question"],
            "decision_threshold": 0.5,
            "train_data": str(args.train_data),
            "eval_data": str(args.eval_data),
            "train_task_count": len(train_rows),
            "eval_task_count": len(eval_rows),
            "concurrent_requests": args.workers,
            "label_policy": "one greedy Qwen 0.5B completion per task; EvalPlus MBPP and MBPP+ labels remain separate",
            "selection_policy": "no learned checkpoint or threshold selection; report Jev at 0.5 and threshold sweep",
            "api_key_source": "repository .env JEV_API_KEY",
        },
    )
    run.define_metric("evaluation_step")
    for prefix in ("train", "evalplus_mbpp", "evalplus_mbpp_plus"):
        run.define_metric(f"{prefix}/*", step_metric="evaluation_step")
    payload: dict[str, Any] = {"evaluation_step": 0}
    for split_name, split_metrics in metrics.items():
        prefix = "train" if split_name == "train" else split_name
        threshold_metrics = split_metrics.pop("threshold_metrics")
        payload.update({f"{prefix}/{key}": value for key, value in split_metrics.items()})
        for threshold_name, values in threshold_metrics.items():
            payload.update({f"{prefix}/{threshold_name}/{key}": value for key, value in values.items()})
    payload.update({
        "jev/tasks_scored": len(train_predictions) + len(eval_predictions),
        "jev/input_tokens": result["token_usage"]["input_tokens"],
        "jev/output_tokens": result["token_usage"]["output_tokens"],
    })
    run.log(payload, step=0)
    artifact = wandb.Artifact("router-jev-qwen05-one-shot-20261014", type="evaluation")
    artifact.add_file(str(metrics_path))
    artifact.add_file(str(predictions_path))
    artifact.add_file(str(cache_path))
    run.log_artifact(artifact)
    run.finish()
    print(json.dumps(result, indent=2), flush=True)


if __name__ == "__main__":
    main()
