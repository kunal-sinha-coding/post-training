"""Rank saved EvalPlus candidates by agreement with GPT-predicted outputs.

The script loads cached GPT-5 mini predictions and saved candidate observations,
scores every candidate by its fraction of matching standard-test outputs, ranks
the ten candidates without correctness labels, and computes Pass@K only after
the ranking is fixed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from llm_output_verifier import EVAL, OBS
from llm_test_answer_predictor import encode


# Score each candidate against predicted outputs using only standard-test traces.
def rank_task(task_id: str, prediction_row: dict, evaluations: dict) -> list[dict]:
    predicted = {
        item["test_index"]: json.dumps(encode(item["value"]), separators=(",", ":"))
        for item in prediction_row["predictions"]
    }
    ranked = []
    for candidate_index in range(len(evaluations[task_id])):
        observation = json.loads((OBS / f"{task_id.replace('/', '_')}_{candidate_index}.json").read_text())
        observed = {
            row["index"]: row.get("value")
            for row in observation["tests"]
            if row["suite"] == "base_input"
        }
        matches = sum(observed.get(index) == value for index, value in predicted.items())
        ranked.append({
            "candidate_index": candidate_index,
            "matches": matches,
            "tests": len(predicted),
            "match_fraction": matches / len(predicted) if predicted else 0.0,
        })
    return sorted(ranked, key=lambda row: (-row["matches"], row["candidate_index"]))


# Measure empirical Pass@K after answer-independent candidate ranking.
def metrics(task_ids: list[str], rankings: dict[str, list[dict]], evaluations: dict) -> dict:
    result = {}
    for suite, field in (("base", "base_status"), ("plus", "plus_status"), ("combined", None)):
        curves = {}
        for k in range(1, 11):
            hits = 0
            for task_id in task_ids:
                prefix = rankings[task_id][:k]
                labels = evaluations[task_id]
                hits += any(
                    labels[row["candidate_index"]]["base_status"] == "pass"
                    if suite == "base"
                    else labels[row["candidate_index"]]["plus_status"] == "pass"
                    if suite == "plus"
                    else labels[row["candidate_index"]]["base_status"] == labels[row["candidate_index"]]["plus_status"] == "pass"
                    for row in prefix
                )
            curves[f"pass_at_{k}"] = hits / len(task_ids) if task_ids else 0.0
        result[suite] = curves
    return result


# Compute the ordinary original-order Pass@K curves for the same task set.
def baseline_metrics(task_ids: list[str], evaluations: dict) -> dict:
    rankings = {
        task_id: [{"candidate_index": index} for index in range(len(evaluations[task_id]))]
        for task_id in task_ids
    }
    return metrics(task_ids, rankings, evaluations)


# Run the deterministic answer-independent reranking and save every score.
def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--predictions", type=Path, default=Path("outputs/qwen-evalplus-full-10-temp02/llm-test-answer-predictions-399.json"))
    parser.add_argument("--output", type=Path, default=Path("outputs/qwen-evalplus-full-10-temp02/llm-prediction-reranking-399.json"))
    args = parser.parse_args()
    predictions = json.loads(args.predictions.read_text())
    evaluations = json.loads(EVAL.read_text())["eval"]
    task_ids = predictions["tasks"]
    rankings = {
        task_id: rank_task(task_id, predictions["results"][task_id], evaluations)
        for task_id in task_ids
    }
    report = {
        "experiment": "llm-prediction-reranking-evalplus-399",
        "prediction_artifact": str(args.predictions),
        "candidate_observation_artifact": str(OBS),
        "selection_uses_correctness_labels": False,
        "tie_break": "Original candidate index ascending after matching-score descending.",
        "task_ids": task_ids,
        "rankings": rankings,
        "metrics": metrics(task_ids, rankings, evaluations),
        "baseline_original_order": baseline_metrics(task_ids, evaluations),
        "prediction_artifact_sha256": hashlib.sha256(args.predictions.read_bytes()).hexdigest(),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"metrics": report["metrics"], "baseline_original_order": report["baseline_original_order"]}, indent=2))


if __name__ == "__main__":
    main()
