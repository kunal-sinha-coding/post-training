# This script joins one-shot router labels to the configured MBPP task pool and builds an append-only SFT solution store.
# It accepts only completions whose saved MBPP label is one and verifies every task ID has exactly one label row.
# It binds each accepted completion to the same prompt and full-test fingerprint used by the SFT trainer.
# It writes a fresh solution map and a summary that records the candidate policy and accepted task count.

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from experiments.incremental_rejection_sampling_sft import load_config, load_training_tasks, task_fingerprint


# Join scored labels to normalized training tasks and save only full-pass completions.
def main() -> None:
    # Parse the labeling config and the destination for the fresh accepted-solution map.
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path("configs/router-one-shot-labels-20261013.yaml"))
    parser.add_argument("--labels", type=Path, default=Path("outputs/router-mbpp-easy-one-shot-20261013/router_dataset.jsonl"))
    parser.add_argument("--store", type=Path, default=Path("outputs/rejection-sampling-original-easy-one-shot-20261013/solutions.json"))
    args = parser.parse_args()

    # Resolve relative artifact paths from the repository root before loading data.
    root = Path(__file__).resolve().parents[1]
    config_path = args.config if args.config.is_absolute() else root / args.config
    labels_path = args.labels if args.labels.is_absolute() else root / args.labels
    store_path = args.store if args.store.is_absolute() else root / args.store
    config = load_config(config_path)

    # Load the exact same original and easy task pool used to create the saved labels.
    tasks = load_training_tasks(config)
    label_rows = [json.loads(line) for line in labels_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    labels_by_id = {str(row["task_id"]): row for row in label_rows}
    if len(labels_by_id) != len(label_rows) or set(labels_by_id) != {str(task["task_id"]) for task in tasks}:
        raise ValueError("The one-shot labels do not match the configured original-plus-easy training task pool.")

    # Preserve one passing completion per task with the SFT trainer's prompt-and-test fingerprint.
    store: dict[str, dict[str, Any]] = {}
    for task in tasks:
        task_id = str(task["task_id"])
        row = labels_by_id[task_id]
        if int(row["label_mbpp"]) == 1:
            store[task_id] = {
                "solution": str(row["completion"]),
                "task_fingerprint": task_fingerprint(task),
                "selection": "the sole temperature-zero completion passed every available MBPP-style assertion",
            }

    # Write the isolated store and a reproducibility summary for the SFT launch.
    store_path.parent.mkdir(parents=True, exist_ok=True)
    store_path.write_text(json.dumps(store, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    summary = {
        "experiment": "original-easy-one-shot-pass-filtered-sft-store",
        "task_count": len(tasks),
        "accepted_solution_count": len(store),
        "rejected_count": len(tasks) - len(store),
        "candidate_policy": "exactly one greedy completion per task; accept only if every available assertion passes",
        "label_artifact": str(labels_path),
        "solution_store": str(store_path),
        "solution_store_sha256": hashlib.sha256(store_path.read_bytes()).hexdigest(),
        "sources": {"original": sum(not str(task["task_id"]).startswith("synthetic-") for task in tasks), "easy": sum(str(task["task_id"]).startswith("synthetic-easy-") for task in tasks)},
    }
    summary_path = store_path.parent / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == "__main__":
    # Build the SFT solution store from the completed one-shot label artifact.
    main()
