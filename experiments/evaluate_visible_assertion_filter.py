"""Measure EvalPlus Pass@K after filtering candidates by the visible assertion.

The script loads the saved answer-independent survivor lists, keeps their
original candidate order, computes Pass@K after joining benchmark labels, and
reports both full-suite metrics and metrics conditional on having survivors.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from llm_output_verifier import EVAL


# Compute Pass@K for a filtered candidate pool, counting empty pools as misses.
def curves(task_ids: list[str], survivors: dict[str, list[int]], evaluations: dict) -> dict:
    result = {}
    for suite, field in (("base", "base_status"), ("plus", "plus_status"), ("combined", None)):
        result[suite] = {}
        for k in range(1, 11):
            hits = 0
            for task_id in task_ids:
                prefix = survivors[task_id][:k]
                hits += any(
                    evaluations[task_id][index]["base_status"] == "pass"
                    if suite == "base"
                    else evaluations[task_id][index]["plus_status"] == "pass"
                    if suite == "plus"
                    else evaluations[task_id][index]["base_status"] == evaluations[task_id][index]["plus_status"] == "pass"
                    for index in prefix
                )
            result[suite][f"pass_at_{k}"] = hits / len(task_ids) if task_ids else 0.0
    return result


# Compute the accuracy of selecting the first surviving candidate.
def first_selection(task_ids: list[str], survivors: dict[str, list[int]], evaluations: dict) -> dict:
    result = {}
    for suite, field in (("base", "base_status"), ("plus", "plus_status"), ("combined", None)):
        hits = 0
        selected = 0
        for task_id in task_ids:
            if not survivors[task_id]:
                continue
            selected += 1
            index = survivors[task_id][0]
            hits += (
                evaluations[task_id][index][field] == "pass"
                if field
                else evaluations[task_id][index]["base_status"] == evaluations[task_id][index]["plus_status"] == "pass"
            )
        result[suite] = {"correct": hits, "tasks_with_survivors": selected, "accuracy_conditional": hits / selected if selected else 0.0, "accuracy_full_suite": hits / len(task_ids) if task_ids else 0.0}
    return result


# Evaluate the saved filtered pools without using labels during selection.
def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--filter", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    filtered = json.loads(args.filter.read_text())
    evaluations = json.loads(EVAL.read_text())["eval"]
    task_ids = filtered["tasks"]
    survivors = {task_id: filtered["results"][task_id]["survivor_indices"] for task_id in task_ids}
    nonempty = [task_id for task_id in task_ids if survivors[task_id]]
    report = {
        "experiment": "visible-assertion-filter-reranking-evalplus-399",
        "filter_artifact": str(args.filter),
        "selection": "First surviving candidate in original candidate-index order.",
        "selection_uses_correctness_labels": False,
        "tasks_total": len(task_ids),
        "tasks_with_survivors": len(nonempty),
        "tasks_without_survivors": len(task_ids) - len(nonempty),
        "first_survivor_metrics": first_selection(task_ids, survivors, evaluations),
        "pass_at_k_full_suite": curves(task_ids, survivors, evaluations),
        "pass_at_k_conditional_on_survivors": curves(nonempty, survivors, evaluations),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
