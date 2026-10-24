"""Audit previously identified BFCL and APIGen sources before using them for encoder training.

The flow downloads public BFCL Live source files, records category and structural statistics, checks APIGen
access without reading any When2Call test labels, and writes an auditable JSON report for the next planning step.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import requests


BFCL_BASE = "https://raw.githubusercontent.com/ShishirPatil/gorilla/main/berkeley-function-call-leaderboard/bfcl_eval/data/"
BFCL_FILES = ("BFCL_v4_live_simple.json", "BFCL_v4_live_multiple.json", "BFCL_v4_live_parallel.json", "BFCL_v4_live_parallel_multiple.json", "BFCL_v4_live_irrelevance.json", "BFCL_v4_live_relevance.json")


def read_jsonl(url: str) -> list[dict]:
    """Download one public JSONL source file and parse its records."""
    # Use a bounded timeout and fail clearly when a source is unavailable.
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    return [json.loads(line) for line in response.text.splitlines() if line.strip()]


def summarize_bfcl() -> dict:
    """Summarize BFCL Live categories without loading the official When2Call test split."""
    # Count source categories and simple structural features that affect the encoder distribution.
    category_counts = Counter()
    tool_counts = Counter()
    question_lengths = []
    failures = []
    for filename in BFCL_FILES:
        try:
            rows = read_jsonl(BFCL_BASE + filename)
        except Exception as exc:
            failures.append({"file": filename, "error": repr(exc)})
            continue
        category = filename.removeprefix("BFCL_v4_live_").removesuffix(".json")
        category_counts[category] += len(rows)
        for row in rows:
            # Record only public source structure and never any When2Call benchmark answer.
            question = row.get("question", [[{"content": ""}]])
            text = " ".join(str(message.get("content", "")) for turn in question for message in turn)
            question_lengths.append(len(text))
            tool_counts[len(row.get("function", []))] += 1
    return {"files": list(BFCL_FILES), "category_counts": dict(category_counts), "tool_count_histogram": dict(tool_counts), "question_length": {"count": len(question_lengths), "mean": sum(question_lengths) / max(1, len(question_lengths)), "max": max(question_lengths, default=0)}, "failures": failures}


def check_apigen_access() -> dict:
    """Check whether the previously identified APIGen dataset is downloadable in this environment."""
    # Record access status only so a gated source never silently becomes a training dependency.
    try:
        from datasets import load_dataset
        load_dataset("Salesforce/xlam-function-calling-60k", split="train", streaming=True)
        return {"dataset": "Salesforce/xlam-function-calling-60k", "accessible": True}
    except Exception as exc:
        return {"dataset": "Salesforce/xlam-function-calling-60k", "accessible": False, "error": type(exc).__name__, "message": str(exc)[:500]}


def main() -> int:
    """Run the external source audit and save its reproducible report."""
    # Parse the output path before running network checks.
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    # Combine source summaries into one report for evidence-based planning.
    report = {"bfcl": summarize_bfcl(), "apigen": check_apigen_access(), "uses_when2call_test_labels": False}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
