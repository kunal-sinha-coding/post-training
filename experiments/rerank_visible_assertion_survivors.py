"""Rerank visible-assertion survivors using saved Qwen 7B likelihoods.

The script identifies which stored standard test matches the visible prompt
assertion, removes that test from the likelihood aggregate, ranks survivors by
mean or median score on the remaining tests, and measures selected accuracy
and Pass@K only after the answer-independent ranking is fixed.
"""

from __future__ import annotations

import argparse
import ast
import json
import math
import re
import statistics
from pathlib import Path

from llm_output_verifier import DATA, EVAL


# Normalize literal tuples and lists so prompt inputs match JSON dataset inputs.
def normalize(value: object) -> object:
    if isinstance(value, (tuple, list)):
        return [normalize(item) for item in value]
    if isinstance(value, dict):
        return {key: normalize(item) for key, item in value.items()}
    return value


# Identify the stored base-test index represented by the visible assertion.
def visible_test_index(task: dict) -> int | None:
    line = re.findall(r"^\s*assert\s+.*$", task["prompt"], flags=re.MULTILINE)[0].strip()
    expression = ast.parse(line).body[0].test
    calls = [node for node in ast.walk(expression) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == task["entry_point"]]
    if len(calls) != 1:
        return None
    arguments = normalize([ast.literal_eval(argument) for argument in calls[0].args])
    matches = [index for index, inputs in enumerate(task["base_input"]) if normalize(inputs) == arguments]
    return matches[0] if len(matches) == 1 else None


# Rank surviving candidates using an aggregate over the other standard tests.
def rank_candidates(task_id: str, survivor_indices: list[int], scores: dict, other_tests: list[int], strategy: str) -> list[int]:
    def score(candidate_index: int) -> float:
        row = scores[task_id][candidate_index] + [None] * (3 - len(scores[task_id][candidate_index]))
        values = [value for index in other_tests if isinstance((value := row[index]), (int, float)) and math.isfinite(value)]
        if not values:
            return float("-inf")
        return sum(values) / len(values) if strategy == "mean" else statistics.median(values)
    return sorted(survivor_indices, key=lambda index: (-score(index), index))


# Compute filtered Pass@K for a fixed likelihood ranking.
def curves(task_ids: list[str], rankings: dict[str, list[int]], evaluations: dict) -> dict:
    result = {}
    for suite, field in (("base", "base_status"), ("plus", "plus_status"), ("combined", None)):
        result[suite] = {}
        for k in range(1, 11):
            hits = 0
            for task_id in task_ids:
                hits += any(
                    evaluations[task_id][index][field] == "pass"
                    if field
                    else evaluations[task_id][index]["base_status"] == evaluations[task_id][index]["plus_status"] == "pass"
                    for index in rankings[task_id][:k]
                )
            result[suite][f"pass_at_{k}"] = hits / len(task_ids) if task_ids else 0.0
    return result


# Measure first-ranked candidate accuracy on full and nonempty task sets.
def selected_metrics(task_ids: list[str], rankings: dict[str, list[int]], evaluations: dict) -> dict:
    result = {}
    for suite, field in (("base", "base_status"), ("plus", "plus_status"), ("combined", None)):
        hits = sum(
            bool(rankings[task_id]) and (
                evaluations[task_id][rankings[task_id][0]][field] == "pass"
                if field
                else evaluations[task_id][rankings[task_id][0]]["base_status"] == evaluations[task_id][rankings[task_id][0]]["plus_status"] == "pass"
            )
            for task_id in task_ids
        )
        nonempty = [task_id for task_id in task_ids if rankings[task_id]]
        result[suite] = {"correct": hits, "full_suite_accuracy": hits / len(task_ids), "conditional_accuracy": sum(
            evaluations[task_id][rankings[task_id][0]][field] == "pass"
            if field
            else evaluations[task_id][rankings[task_id][0]]["base_status"] == evaluations[task_id][rankings[task_id][0]]["plus_status"] == "pass"
            for task_id in nonempty
        ) / len(nonempty) if nonempty else 0.0, "tasks_with_selection": len(nonempty)}
    return result


# Run both likelihood rerankers over the saved visible-assertion survivors.
def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--filter", type=Path, required=True)
    parser.add_argument("--scores", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    tasks = {row["task_id"]: row for row in map(json.loads, DATA.open())}
    evaluations = json.loads(EVAL.read_text())["eval"]
    filtered = json.loads(args.filter.read_text())
    score_artifact = json.loads(args.scores.read_text())
    task_ids = filtered["tasks"]
    rankings = {"mean": {}, "median": {}}
    test_indices = {}
    fallback_tasks = []
    for task_id in task_ids:
        visible_index = visible_test_index(tasks[task_id])
        standard_test_count = min(3, len(tasks[task_id]["base_input"]))
        matched_visible_index = visible_index if visible_index is not None and visible_index < standard_test_count else None
        other_tests = [index for index in range(standard_test_count) if index != matched_visible_index] if matched_visible_index is not None else list(range(standard_test_count))
        if visible_index is None:
            fallback_tasks.append(task_id)
        test_indices[task_id] = {"visible_test_index": visible_index, "aggregated_test_indices": other_tests}
        survivors = filtered["results"][task_id]["survivor_indices"]
        for strategy in rankings:
            rankings[strategy][task_id] = rank_candidates(task_id, survivors, score_artifact["scores"], other_tests, strategy)
    report = {
        "experiment": "visible-assertion-filter-likelihood-tiebreak-evalplus-399",
        "filter_artifact": str(args.filter),
        "score_artifact": str(args.scores),
        "selection_uses_correctness_labels": False,
        "tie_break_definition": "Among visible-assertion survivors, rank by Qwen 7B mean or median answer log likelihood on the remaining stored standard tests, then candidate index.",
        "tasks": task_ids,
        "tasks_with_survivors": sum(bool(filtered["results"][task_id]["survivor_indices"]) for task_id in task_ids),
        "fallback_tasks_without_visible_test_match": fallback_tasks,
        "test_indices": test_indices,
        "rankings": rankings,
        "metrics": {strategy: {"selected": selected_metrics(task_ids, rankings[strategy], evaluations), "pass_at_k": curves(task_ids, rankings[strategy], evaluations), "pass_at_k_conditional_on_survivors": curves([task_id for task_id in task_ids if rankings[strategy][task_id]], rankings[strategy], evaluations)} for strategy in rankings},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report["metrics"], indent=2))


if __name__ == "__main__":
    main()
