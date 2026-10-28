"""Merge synthetic training pools after exact prompt deduplication.

The flow reads only pre-generated synthetic JSONL files, validates each row, removes exact duplicate prompts, writes one combined training pool, and saves its class counts and provenance without loading validation or test data.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


def merge_pools(inputs: list[Path], output_dir: Path) -> dict[str, Any]:
    """Write a deduplicated synthetic pool and its provenance summary."""
    # Keep the first identical prompt and reject conflicts in its training label.
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "balanced_boundary_combined.jsonl"
    seen: dict[str, int] = {}
    rows: list[dict[str, Any]] = []
    duplicates = 0
    for input_path in inputs:
        with input_path.open(encoding="utf-8") as source:
            for line_number, line in enumerate(source, 1):
                row = json.loads(line)
                prompt = row.get("prompt")
                label = row.get("label")
                if not isinstance(prompt, str) or not isinstance(label, int):
                    raise ValueError(f"Invalid training row in {input_path}:{line_number}.")
                if prompt in seen:
                    if seen[prompt] != label:
                        raise ValueError(f"Conflicting labels for duplicate prompt in {input_path}:{line_number}.")
                    duplicates += 1
                    continue
                seen[prompt] = label
                rows.append(row)
    with output_path.open("w", encoding="utf-8") as destination:
        for row in rows:
            destination.write(json.dumps(row, ensure_ascii=False) + "\n")
    summary = {
        "status": "completed",
        "input_pools": [str(path) for path in inputs],
        "output_jsonl": str(output_path),
        "rows_written": len(rows),
        "duplicate_prompts_removed": duplicates,
        "class_counts": dict(sorted(Counter(str(row["label"]) for row in rows).items())),
        "official_test_loaded": False,
        "test_labels_used": False,
    }
    (output_dir / "metrics.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def main() -> int:
    """Parse input pools and write the merged training-only artifact."""
    # Require at least two input pools so this command always tests a real combination.
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, action="append", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if len(args.input) < 2:
        raise ValueError("At least two synthetic pools are required.")
    result = merge_pools(args.input, args.output_dir)
    print(json.dumps(result, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
