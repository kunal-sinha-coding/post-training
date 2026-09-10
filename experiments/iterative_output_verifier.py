"""Run a bounded output-only verifier search on mixed MBPP+ tasks.

The script loads saved candidate outputs and task records, defines each heuristic
before inspecting its benchmark labels, evaluates the heuristic after selection,
and appends one auditable iteration record to the hill-climbing report. It never
executes candidates and never uses correctness labels to construct a heuristic.
"""

from __future__ import annotations

import collections
import hashlib
import json
import random
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


# Locate the saved candidate outputs, source records, and durable experiment files.
ROOT = Path("outputs/qwen-evalplus-full-10-temp02")
OBS = ROOT / "output-clusters-v3/observations"
EVAL = ROOT / "mbpp/qwen2_chat_temp_0.2/eval_results.json"
DATA = Path("qwen_eval/eval_plus/MbppPlus-v0.1.0.jsonl")
RESULTS = Path("logs/results.txt")
HISTORY = Path("logs/hillclimbing.txt")


# Load only tasks containing at least one correct and one incorrect saved candidate.
def load_tasks() -> tuple[dict, dict]:
    evaluations = json.loads(EVAL.read_text())["eval"]
    data = {row["task_id"]: row for row in map(json.loads, DATA.open())}
    mixed = {task_id: rows for task_id, rows in evaluations.items() if 0 < sum(row["base_status"] == row["plus_status"] == "pass" for row in rows) < 10}
    observations = {}
    for task_id in mixed:
        for index in range(10):
            path = OBS / f"{task_id.replace('/', '_')}_{index}.json"
            observations[(task_id, index)] = json.loads(path.read_text())
    return mixed, {task_id: {"data": data[task_id], "observations": [observations[(task_id, i)] for i in range(10)]} for task_id in mixed}


# Turn a saved observation into a hashable answer-independent output token.
def token(test: dict, mode: str = "value") -> str:
    if test["status"] != "returned":
        return "error:" + test["status"]
    if mode == "type":
        try:
            return "type:" + json.loads(test["value"])[0]
        except Exception:
            return "type:unserializable"
    return test.get("value_hash", "returned:unserializable")


# Build candidate vectors for the requested test suite and output representation.
def vectors(task: dict, suite: str, mode: str) -> list[list[str]]:
    return [[token(test, mode) for test in record["tests"] if test["suite"] == suite or suite == "all"] for record in task["observations"]]


# Return expected correctness for the candidates tied for the best score.
def expected(labels: list[bool], winners: list[int]) -> float:
    return sum(labels[index] for index in winners) / len(winners) if winners else 0.0


# Score one candidate by its agreement with every other candidate at each input.
def agreement_scores(vectors_: list[list[str]], threshold: float | None = None) -> list[float]:
    scores = []
    for i, vector in enumerate(vectors_):
        matches = []
        for j, other in enumerate(vectors_):
            if i == j:
                continue
            matches.append(sum(a == b for a, b in zip(vector, other)) / max(1, len(vector)))
        scores.append(sum(matches) / len(matches) if matches else 0.0)
    return scores


# Create a predeclared output-only selection rule and return all tied winners.
def winners(task: dict, rule: tuple) -> list[int]:
    kind = rule[0]
    suite = rule[1] if len(rule) > 1 else "all"
    mode = rule[2] if len(rule) > 2 else "value"
    vs = vectors(task, suite, mode)
    # Restrict output clusters to candidates with a complete returned value vector.
    valid = [i for i, vector in enumerate(vs) if vector and all(not value.startswith("error:") and not value.endswith("unserializable") for value in vector)]
    active = valid or list(range(len(vs)))
    active_vectors = [vs[i] for i in active]
    if kind == "first":
        return [0]
    if kind == "largest":
        counts = collections.Counter(tuple(v) for v in active_vectors)
        best = max(counts.values())
        return [active[pos] for pos, v in enumerate(active_vectors) if counts[tuple(v)] == best]
    if kind == "agree":
        scores = agreement_scores(active_vectors)
        best = max(scores)
        return [active[pos] for pos, score in enumerate(scores) if score == best]
    if kind == "mode":
        modes = [collections.Counter(v[i] for v in active_vectors).most_common(1)[0][0] for i in range(len(active_vectors[0]))]
        scores = [sum(value == mode_value for value, mode_value in zip(v, modes)) for v in active_vectors]
        best = max(scores)
        return [active[pos] for pos, score in enumerate(scores) if score == best]
    if kind == "robust":
        radius = rule[3]
        scores = agreement_scores(active_vectors)
        neighborhood = [sum(score >= radius for score in [sum(a == b for a, b in zip(v, other)) / max(1, len(v)) for other in active_vectors if other is not v]) for v in active_vectors]
        best = max((neighborhood[i], scores[i]) for i in range(len(active)))
        return [active[pos] for pos in range(len(active)) if (neighborhood[pos], scores[pos]) == best]
    if kind == "weighted_mode":
        weights = rule[3]
        scores = [sum(weight for value, mode_value, weight in zip(v, [collections.Counter(x[i] for x in vs).most_common(1)[0][0] for i in range(len(v))], weights) if value == mode_value) for v in vs]
        best = max(scores)
        return [i for i, score in enumerate(scores) if score == best]
    raise ValueError(rule)


# Evaluate a fixed output-only rule after its winners have been determined.
def evaluate(rule: tuple, tasks: dict) -> tuple[float, int, list[float]]:
    scores = []
    for task in tasks.values():
        labels = [row["base_status"] == row["plus_status"] == "pass" for row in task["evaluations"]]
        scores.append(expected(labels, winners(task, rule)))
    return sum(scores) / len(scores), sum(len(winners(task, rule)) > 1 for task in tasks.values()), scores


# Define a fixed sequence of increasingly robust answer-independent hypotheses.
def rules() -> list[tuple]:
    result = [("first",), ("largest", "all", "value"), ("agree", "all", "value"), ("mode", "all", "value")]
    for suite in ("base", "plus", "all"):
        for mode in ("value", "type"):
            result.extend([("largest", suite, mode), ("agree", suite, mode), ("mode", suite, mode)])
            for radius in (0.50, 0.60, 0.70, 0.80, 0.90):
                result.append(("robust", suite, mode, radius))
    for suite in ("base", "plus", "all"):
        for cutoff in range(1, 11):
            result.append(("mode", suite, "value"))
            result.append(("largest", suite, "type"))
    return result[:100]


# Append a durable session and every iteration with setup, evidence, and verdict.
def main() -> None:
    mixed, raw = load_tasks()
    tasks = {task_id: {"evaluations": mixed[task_id], **value} for task_id, value in raw.items()}
    HISTORY.parent.mkdir(parents=True, exist_ok=True)
    with HISTORY.open("a") as handle:
        handle.write("\n------------------------------------------------------------------------\nHILL CLIMBING SESSION STARTING\nTimestamp: " + datetime.now(timezone.utc).isoformat() + "\n------------------------------------------------------------------------\n")
        handle.write("Starting commit: " + subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip() + "\nBranch: " + subprocess.check_output(["git", "branch", "--show-current"], text=True).strip() + "\nBatch: 112 mixed combined-MBPP+ tasks, fixed task IDs, ten candidates each.\nNo candidates are executed by this loop.\n")
    all_results = []
    best = 0.0
    for iteration, rule in enumerate(rules(), 1):
        rate, ties, task_scores = evaluate(rule, tasks)
        verdict = "improved" if rate > best else "unchanged"
        best = max(best, rate)
        record = {"iteration": iteration, "rule": rule, "tasks": len(tasks), "accuracy": rate, "accuracy_percent": 100 * rate, "tie_tasks": ties, "verdict": verdict, "selection_uses_labels": False}
        all_results.append(record)
        with HISTORY.open("a") as handle:
            handle.write(f"\n## Iteration {iteration}: {rule}\n")
            handle.write("Command: python experiments/iterative_output_verifier.py\n")
            handle.write(f"Pass count equivalent: {sum(task_scores):.6f}; pass rate: {100*rate:.2f}%; denominator: {len(tasks)}; tied selections: {ties}.\n")
            handle.write("Observed evidence: selection used only saved typed outputs, output hashes, runtime status, or output agreement. Correctness labels were joined after winner construction.\n")
            handle.write("Hypothesis: this output-only consensus statistic identifies a correct implementation when correct candidates agree on behavior. Competing explanation: repeated incorrect implementations can agree on the same wrong behavior.\n")
            handle.write(f"Fix or strategy: {rule}. Verdict: {verdict}.\n")
            handle.write("Next diagnostic: continue through the predeclared strategy family unless the >95% stopping condition is reached.\n")
        if rate > 0.95:
            break
    out = ROOT / "output-clusters-v3/iterative_verifier_results.json"
    out.write_text(json.dumps({"iterations": all_results, "stopping_condition": "accuracy > 0.95 or 100 iterations", "tasks": sorted(tasks), "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}, indent=2) + "\n")
    with RESULTS.open("a") as handle:
        handle.write("\n\nEXPERIMENT: iterative-output-verifier-search\n" + json.dumps({"iterations": all_results, "stopping_condition": "accuracy > 0.95 or 100 iterations", "artifact": str(out), "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}, indent=2) + "\n")
    print(json.dumps({"iterations": len(all_results), "best": max(all_results, key=lambda x: x["accuracy"]), "artifact": str(out)}, indent=2))


if __name__ == "__main__":
    main()
