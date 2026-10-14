# This script compares Jev prompt and state variants on fixed MBPP task IDs, saves per-task scores, and logs comparable metrics to W&B.
# It separates a stratified MBPP development fold from the untouched EvalPlus benchmark.

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import random
import re
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

try:
    from .evaluate_jev_router import evaluate_split, query_jev
except ImportError:
    from evaluate_jev_router import evaluate_split, query_jev


# Split normalized task-text groups into a fixed stratified development fold.
def development_rows(rows: list[dict[str, Any]], seed: int = 42, fraction: float = 0.2) -> list[dict[str, Any]]:
    # Keep duplicate task descriptions in one fold and select a stable share from each label class.
    groups: dict[tuple[int, str], list[dict[str, Any]]] = {}
    for row in rows:
        text = re.sub(r"\s+", " ", str(row.get("task_text") or row["prompt"])).strip().casefold()
        groups.setdefault((int(row["label_mbpp"]), text), []).append(row)
    rng = random.Random(seed)
    selected: list[dict[str, Any]] = []
    for label in (0, 1):
        class_groups = [group for (group_label, _), group in groups.items() if group_label == label]
        rng.shuffle(class_groups)
        target = round(sum(len(group) for group in class_groups) * fraction)
        count = 0
        for group in class_groups:
            if count >= target:
                break
            selected.extend(group)
            count += len(group)
    return selected


# Normalize the Qwen prompt by keeping its task docstring and removing chat wrappers.
def normalized_state(row: dict[str, Any]) -> str:
    # Extract the triple-quoted problem text while preserving visible assertions.
    match = re.search(r'"""(.*?)"""', str(row["prompt"]), re.DOTALL)
    return match.group(1).strip() if match else str(row["prompt"]).strip()


# Build the requested prompt state and question for one experimental condition.
def variant_input(row: dict[str, Any], variant: str) -> tuple[Any, str]:
    # Change only the question wording or state formatting defined by the selected condition.
    base_question = "Assume exactly one first-try, greedy generation by Qwen/Qwen2.5-Coder-0.5B-Instruct for this programming task, with its completion checked against all task tests. Is the model likely to pass every test?"
    if variant == "baseline":
        return str(row["prompt"]), base_question
    if variant == "precise_question":
        question = "Using only this task prompt, estimate the probability that one greedy, no-retry completion from Qwen/Qwen2.5-Coder-0.5B-Instruct will pass every test. A task counts as success only if all tests pass."
        return str(row["prompt"]), question
    if variant == "normalized_prompt":
        return normalized_state(row), base_question
    raise ValueError(f"Unknown prompt variant: {variant}")


# Query Jev for one task while keeping responses local and resumable.
def score_variant(rows: list[dict[str, Any]], variant: str, cache_path: Path, api_key: str, model: str, workers: int, timeout: float, retries: int) -> list[dict[str, Any]]:
    # Reuse valid cached scores and append each new API result immediately.
    cache: dict[str, dict[str, Any]] = {}
    if cache_path.exists():
        for line in cache_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                item = json.loads(line)
                cache[str(item["task_id"])] = item
    missing = []
    for row in rows:
        state, question = variant_input(row, variant)
        fingerprint = hashlib.sha256(json.dumps({"state": state, "question": question}, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
        cached = cache.get(str(row["task_id"]))
        if cached and cached["input_sha256"] == fingerprint:
            continue
        missing.append((row, state, question, fingerprint))
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    def request(item: tuple[dict[str, Any], Any, str, str]) -> tuple[str, dict[str, Any]]:
        # Call Jev with the exact state and question for this condition.
        row, state, question, fingerprint = item
        result = query_jev(state, model, api_key, timeout, retries, instructions=question)
        return str(row["task_id"]), {
            "variant": variant,
            "task_id": str(row["task_id"]),
            "input_sha256": fingerprint,
            **result,
        }
    if missing:
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor, cache_path.open("a", encoding="utf-8") as handle:
            futures = [executor.submit(request, item) for item in missing]
            for index, future in enumerate(concurrent.futures.as_completed(futures), start=1):
                task_id, record = future.result()
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
                handle.flush()
                cache[task_id] = record
                if index % 25 == 0 or index == len(missing):
                    print(json.dumps({"variant": variant, "new_scores": index, "remaining": len(missing) - index}), flush=True)
    return [cache[str(row["task_id"])] for row in rows]


# Compute all requested Jev metrics and log one W&B run for the selected development stage.
def main() -> None:
    # Parse the experiment stage and the controlled prompt variants.
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=("pilot", "development", "benchmark"), default="development")
    parser.add_argument("--variants", nargs="+", choices=("baseline", "precise_question", "normalized_prompt"), default=("baseline", "normalized_prompt"))
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--model", default="jev-latest")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    load_dotenv(root / ".env")
    api_key = os.getenv("JEV_API_KEY")
    if not api_key or not os.getenv("WANDB_API_KEY"):
        raise RuntimeError("JEV_API_KEY and WANDB_API_KEY must be set in the repository .env file.")

    # Load the fixed labeled task files and select a stable development or benchmark split.
    train_path = root / "outputs/router-mbpp-original-one-shot-20261013/router_dataset.jsonl"
    eval_path = root / "outputs/router-evalplus-greedy-dual-label-20261013/router_evalplus_labels.jsonl"
    train_rows = [json.loads(line) for line in train_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    eval_rows = [json.loads(line) for line in eval_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    dev_rows = development_rows(train_rows, args.seed)
    if args.stage == "pilot":
        # Select five positives and five negatives from the fixed development fold.
        rng = random.Random(args.seed)
        dev_rows = [row for label in (0, 1) for row in rng.sample([item for item in dev_rows if int(item["label_mbpp"]) == label], 5)]
    elif args.stage == "benchmark":
        # Report the complete training and EvalPlus sets only after selecting a prompt on development labels.
        dev_rows = train_rows

    # Ask Jev for each selected variant and compute per-set classification and ranking metrics.
    output_dir = root / "outputs/jev-prompt-study-20261014"
    scored: dict[str, list[dict[str, Any]]] = {}
    metrics: dict[str, dict[str, Any]] = {}
    for variant in args.variants:
        variant_rows = [("development" if args.stage != "benchmark" else "train", dev_rows)]
        if args.stage == "benchmark":
            variant_rows.append(("evalplus", eval_rows))
        scored[variant] = []
        metrics[variant] = {}
        for split, rows in variant_rows:
            score_path = output_dir / f"{args.stage}-{variant}-{split}-scores.jsonl"
            records = score_variant(rows, variant, score_path, api_key, args.model, args.workers, 90, 4)
            probabilities = [float(item["probability"]) for item in records]
            label_keys = ("label_mbpp", "label_mbpp_plus") if split == "evalplus" else ("label_mbpp",)
            for label_key in label_keys:
                metric_name = f"evalplus_{label_key.removeprefix('label_')}" if split == "evalplus" else split
                labels = [int(row[label_key]) for row in rows]
                metrics[variant][metric_name] = evaluate_split(labels, probabilities)
            scored[variant].append({"split": split, "rows": rows, "records": records, "probabilities": probabilities})

    # Log all metrics and threshold sweeps for every prompt variant to one W&B run.
    import wandb

    run_name = f"jev-prompt-{args.stage}-20261014"
    run = wandb.init(
        entity="kunal-personal",
        project="grpo-mbpp",
        name=run_name,
        job_type="router-prompt-study",
        config={
            "stage": args.stage,
            "model_requested": args.model,
            "model_returned": sorted({item["model_returned"] for variants in scored.values() for split in variants for item in split["records"]}),
            "variants": args.variants,
            "development_seed": args.seed,
            "development_fraction": 0.2,
            "decision_threshold": 0.5,
            "training_labels": str(train_path),
            "eval_labels": str(eval_path),
            "selection_rule": "Use MBPP training development fold only; EvalPlus is measured only in the benchmark stage after prompt selection.",
            "api_key_source": "repository .env JEV_API_KEY",
        },
    )
    payload: dict[str, Any] = {}
    full_result: dict[str, Any] = {"stage": args.stage, "metrics": metrics, "variants": args.variants}
    all_predictions = []
    for variant in args.variants:
        for metric_name, result in metrics[variant].items():
            thresholds = result["threshold_metrics"]
            prefix = f"{variant}/{metric_name}"
            payload.update({f"{prefix}/{key}": value for key, value in result.items() if key != "threshold_metrics"})
            for threshold, values in thresholds.items():
                payload.update({f"{prefix}/{threshold}/{key}": value for key, value in values.items()})
        for split_data in scored[variant]:
            for row, record, probability in zip(split_data["rows"], split_data["records"], split_data["probabilities"], strict=True):
                all_predictions.append({
                    "variant": variant,
                    "split": split_data["split"],
                    "task_id": str(row["task_id"]),
                    "label_mbpp": row.get("label_mbpp"),
                    "label_mbpp_plus": row.get("label_mbpp_plus"),
                    "probability": probability,
                    "prediction": int(probability >= 0.5),
                })
        payload[f"{variant}/tasks_scored"] = sum(len(split["records"]) for split in scored[variant])
        payload[f"{variant}/input_tokens"] = sum(item["input_tokens"] for split in scored[variant] for item in split["records"])
        payload[f"{variant}/output_tokens"] = sum(item["output_tokens"] for split in scored[variant] for item in split["records"])
    run.log(payload, step=0)

    # Save per-task scores and complete metrics locally and as a W&B artifact.
    predictions_path = output_dir / f"{args.stage}-predictions.jsonl"
    metrics_path = output_dir / f"{args.stage}-metrics.json"
    predictions_path.write_text("".join(json.dumps(row) + "\n" for row in all_predictions), encoding="utf-8")
    metrics_path.write_text(json.dumps(full_result, indent=2) + "\n", encoding="utf-8")
    artifact = wandb.Artifact(f"jev-prompt-{args.stage}-20261014", type="evaluation")
    artifact.add_file(str(predictions_path))
    artifact.add_file(str(metrics_path))
    for variant in args.variants:
        for split in scored[variant]:
            artifact.add_file(str(output_dir / f"{args.stage}-{variant}-{split['split']}-scores.jsonl"))
    run.log_artifact(artifact)
    run.finish()
    print(json.dumps(full_result, indent=2), flush=True)


if __name__ == "__main__":
    main()
