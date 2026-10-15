# This script asks Jev once per EvalPlus task whether Qwen 0.5B is suitable or a larger model is needed, then measures the mapped decisions on MBPP and MBPP+.
# Jev receives task prompts only, while benchmark labels are loaded separately and used only after all calls finish.

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from experiments.evaluate_jev_router import query_jev

QUESTION = (
    "Imagine choosing either Qwen/Qwen2.5-Coder-0.5B-Instruct or a larger code model for this task. "
    "Is the task suitable for the 0.5B model, meaning one first-try greedy completion is likely to pass every test? "
    "Answer yes only when the 0.5B model is likely to pass all tests; otherwise answer no because a larger model is the safer choice."
)


# Compute accuracy and confusion counts for one set of router decisions.
def binary_metrics(labels: list[int], predictions: list[int]) -> dict[str, Any]:
    # Count correct and incorrect positive and negative predictions.
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


# Ask Jev once for every task and cache each response as it completes.
def query_tasks(rows: list[dict[str, Any]], cache_path: Path, api_key: str, model: str, workers: int) -> list[dict[str, Any]]:
    # Load existing prompt-matched responses so the run can resume after an interruption.
    cached: dict[str, dict[str, Any]] = {}
    if cache_path.exists():
        for line in cache_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                record = json.loads(line)
                cached[record["task_id"]] = record
    missing = [row for row in rows if str(row["task_id"]) not in cached]

    # Run missing Jev requests concurrently and flush each completed response to disk.
    if missing:
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(query_jev, str(row["prompt"]), model, api_key, 90.0, 5, QUESTION): row
                for row in missing
            }
            with cache_path.open("a", encoding="utf-8") as handle:
                for completed, future in enumerate(concurrent.futures.as_completed(futures), start=1):
                    row = futures[future]
                    response = future.result()
                    record = {
                        "task_id": str(row["task_id"]),
                        "prompt_sha256": hashlib.sha256(str(row["prompt"]).encode("utf-8")).hexdigest(),
                        **response,
                    }
                    handle.write(json.dumps(record) + "\n")
                    handle.flush()
                    cached[record["task_id"]] = record
                    if completed % 50 == 0 or completed == len(missing):
                        print(json.dumps({"completed_calls": completed, "pending_calls": len(missing)}), flush=True)

    # Return responses in the same order as their source prompts.
    return [cached[str(row["task_id"])] for row in rows]


# Load EvalPlus tasks, issue one call per task, and save accuracy on both label sets.
def main() -> None:
    # Parse dataset, artifact, model, and API concurrency settings.
    parser = argparse.ArgumentParser()
    parser.add_argument("--eval-data", type=Path, default=Path("outputs/router-evalplus-greedy-dual-label-20261013/router_evalplus_labels.jsonl"))
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/router-jev-model-size-evalplus-20261015"))
    parser.add_argument("--model", default="jev-latest")
    parser.add_argument("--workers", type=int, default=48)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    load_dotenv(root / ".env")
    api_key = os.getenv("JEV_API_KEY")
    if not api_key:
        raise RuntimeError("JEV_API_KEY is missing from the repository .env file.")

    # Load prompts and keep labels out of all Jev request payloads.
    rows = [json.loads(line) for line in args.eval_data.read_text(encoding="utf-8").splitlines() if line.strip()]
    args.output_dir.mkdir(parents=True, exist_ok=True)
    records = query_tasks(rows, args.output_dir / "jev_predictions.jsonl", api_key, args.model, args.workers)
    predictions = [int(float(record["probability"]) >= 0.5) for record in records]

    # Join the two labels after inference and compute separate benchmark metrics.
    labels_mbpp = [int(row["label_mbpp"]) for row in rows]
    labels_mbpp_plus = [int(row["label_mbpp_plus"]) for row in rows]
    metrics = {
        "evalplus_mbpp": binary_metrics(labels_mbpp, predictions),
        "evalplus_mbpp_plus": binary_metrics(labels_mbpp_plus, predictions),
    }

    # Save per-task decisions and the full setup, usage, and metric record.
    prediction_path = args.output_dir / "predictions.jsonl"
    with prediction_path.open("w", encoding="utf-8") as handle:
        for row, record, prediction in zip(rows, records, predictions, strict=True):
            handle.write(json.dumps({
                "task_id": str(row["task_id"]),
                "label_mbpp": int(row["label_mbpp"]),
                "label_mbpp_plus": int(row["label_mbpp_plus"]),
                "positive_probability": float(record["probability"]),
                "prediction_0_5_suitable": prediction,
                "model_returned": record["model_returned"],
            }) + "\n")
    result = {
        "experiment": "jev-model-size-framing-evalplus-20261015",
        "model_requested": args.model,
        "model_returned": sorted({record["model_returned"] for record in records}),
        "question": QUESTION,
        "decision_mapping": "Jev probability at least 0.5 means Qwen 0.5B is suitable and predicts a pass; lower probability predicts a need for a larger model and a Qwen 0.5B failure.",
        "decision_threshold": 0.5,
        "eval_task_count": len(rows),
        "api_call_count": len(records),
        "concurrent_requests": args.workers,
        "eval_data": str(args.eval_data),
        "eval_data_sha256": hashlib.sha256(args.eval_data.read_bytes()).hexdigest(),
        "metrics": metrics,
        "token_usage": {
            "input_tokens": sum(int(record["input_tokens"]) for record in records),
            "output_tokens": sum(int(record["output_tokens"]) for record in records),
        },
        "artifacts": {
            "raw_scores": str(args.output_dir / "jev_predictions.jsonl"),
            "predictions": str(prediction_path),
            "metrics": str(args.output_dir / "metrics.json"),
        },
    }
    (args.output_dir / "metrics.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2), flush=True)


if __name__ == "__main__":
    main()
