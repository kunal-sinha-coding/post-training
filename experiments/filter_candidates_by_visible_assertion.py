"""Filter saved EvalPlus candidates with the assertion visible in each prompt.

The script extracts the single prompt-visible assertion, executes every saved
candidate against that assertion in parallel worker processes, saves each
candidate verdict and exception, and reports only the distribution of survivor
counts without computing benchmark Pass@K metrics.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import re
import signal
from pathlib import Path

from llm_output_verifier import DATA, EVAL


# Extract the assertion shown inside the original MBPP prompt.
def visible_assertion(prompt: str) -> str:
    assertions = re.findall(r"^\s*assert\b.*$", prompt, flags=re.MULTILINE)
    if len(assertions) != 1:
        raise ValueError(f"Expected exactly one visible assertion, received {len(assertions)}")
    return assertions[0].strip()


# Raise a bounded execution exception for a candidate that does not terminate.
def alarm_handler(signum: int, frame: object) -> None:
    raise TimeoutError("Visible assertion execution timed out.")


# Execute one candidate against the visible assertion in an isolated namespace.
def evaluate_candidate(candidate: str, assertion: str, timeout_seconds: float) -> dict:
    signal.signal(signal.SIGALRM, alarm_handler)
    signal.setitimer(signal.ITIMER_REAL, timeout_seconds)
    try:
        scope = {"__name__": "candidate"}
        exec(candidate, scope)
        exec(assertion, scope)
        return {"status": "pass"}
    except BaseException as error:
        return {"status": "fail", "error_type": type(error).__name__, "error": str(error)[:500]}
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)


# Execute all ten candidates for one task in one parallel worker call.
def evaluate_task(job: dict) -> dict:
    verdicts = [evaluate_candidate(candidate, job["assertion"], job["timeout_seconds"]) for candidate in job["candidates"]]
    return {
        "task_id": job["task_id"],
        "prompt": job["prompt"],
        "assertion": job["assertion"],
        "candidate_code_sha256": [hashlib.sha256(candidate.encode()).hexdigest() for candidate in job["candidates"]],
        "verdicts": verdicts,
        "survivor_indices": [index for index, verdict in enumerate(verdicts) if verdict["status"] == "pass"],
    }


# Aggregate survivor-count frequencies without consulting hidden correctness labels.
def distribution(results: dict[str, dict], task_ids: list[str]) -> dict:
    counts = {str(count): 0 for count in range(11)}
    for task_id in task_ids:
        counts[str(len(results[task_id]["survivor_indices"]))] += 1
    total = len(task_ids)
    return {
        str(count): {"tasks": counts[str(count)], "percentage": 100 * counts[str(count)] / total if total else 0.0}
        for count in range(11)
    }


# Run the parallel visible-assertion filter and persist every candidate verdict.
def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=32)
    parser.add_argument("--timeout-seconds", type=float, default=2.0)
    parser.add_argument("--output", type=Path, default=Path("outputs/qwen-evalplus-full-10-temp02/visible-assertion-filter-399.json"))
    args = parser.parse_args()
    tasks = {row["task_id"]: row for row in map(json.loads, DATA.open())}
    evaluations = json.loads(EVAL.read_text())["eval"]
    task_ids = list(evaluations)
    jobs = [
        {
            "task_id": task_id,
            "prompt": tasks[task_id]["prompt"],
            "assertion": visible_assertion(tasks[task_id]["prompt"]),
            "candidates": [row["solution"] for row in evaluations[task_id]],
            "timeout_seconds": args.timeout_seconds,
        }
        for task_id in task_ids
    ]
    results = {}
    with concurrent.futures.ProcessPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(evaluate_task, job): job["task_id"] for job in jobs}
        for completed, future in enumerate(concurrent.futures.as_completed(futures), 1):
            task_id = futures[future]
            results[task_id] = future.result()
            if completed % 25 == 0 or completed == len(task_ids):
                print(f"Evaluated {completed}/{len(task_ids)} tasks", flush=True)
    artifact = {
        "experiment": "visible-assertion-candidate-filter-evalplus-399",
        "tasks": task_ids,
        "workers": args.workers,
        "timeout_seconds": args.timeout_seconds,
        "filter_source": "The one assert statement embedded in each task's raw prompt.",
        "uses_hidden_tests_or_correctness_labels": False,
        "results": {task_id: results[task_id] for task_id in task_ids},
        "survivor_count_distribution": distribution(results, task_ids),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, indent=2) + "\n")
    print(json.dumps(artifact["survivor_count_distribution"], indent=2))


if __name__ == "__main__":
    main()
