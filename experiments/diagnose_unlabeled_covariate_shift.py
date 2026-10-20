"""Measure unlabeled train and official test input shift without reading test labels.

The flow opens W&B, loads only question and tool fields from cached Arrow files, computes
length, tool-count, and tool-name overlap summaries, and saves aggregate covariate statistics.
"""
from __future__ import annotations

import atexit
import json
import os
import re
from pathlib import Path

from datasets import Dataset


def summarize(rows: object) -> dict[str, float]:
    """Summarize visible question and tool-context features for one split."""
    # Compute only unlabeled input statistics and never access answer or label fields.
    question_lengths = []
    tool_counts = []
    tool_names = set()
    for row in rows:
        question = str(row.get("question", ""))
        tools = row.get("tools", [])
        question_lengths.append(len(question.split()))
        tool_counts.append(len(tools))
        for serialized in tools:
            match = re.search(r'"name"\s*:\s*"([^"]+)"', str(serialized))
            if match:
                tool_names.add(match.group(1).lower())
    return {
        "rows": len(question_lengths),
        "mean_question_words": sum(question_lengths) / max(1, len(question_lengths)),
        "p95_question_words": sorted(question_lengths)[max(0, int(len(question_lengths) * 0.95) - 1)],
        "mean_tool_count": sum(tool_counts) / max(1, len(tool_counts)),
        "tool_name_vocabulary": len(tool_names),
    }


def main() -> int:
    """Run the unlabeled covariate diagnostic and persist aggregate statistics."""
    # Initialize W&B before loading either split so diagnostic failures are tracked.
    import wandb
    if not os.getenv("WANDB_API_KEY"):
        raise RuntimeError("WANDB_API_KEY is required for covariate diagnostics.")
    run = wandb.init(project=os.getenv("WANDB_PROJECT", "when2call-research"), entity=os.getenv("WANDB_ENTITY"), name="when2call-unlabeled-covariate-shift", job_type="data-diagnostic", config={"test_labels_loaded": False})
    atexit.register(run.finish)
    train_path = Path("/workspace/.cache/huggingface/datasets/nvidia___when2_call/train_pref/0.0.0/0582f7749df63a96fdc3070932e83e72396ace53/when2_call-train.arrow")
    test_path = Path("/workspace/.cache/huggingface/datasets/nvidia___when2_call/test/0.0.0/0582f7749df63a96fdc3070932e83e72396ace53/when2_call-mcq.arrow")
    train = summarize(Dataset.from_file(str(train_path)))
    test = summarize(Dataset.from_file(str(test_path)))
    result = {"test_labels_loaded": False, "train_pref": train, "test_inputs_only": test}
    Path("outputs/unlabeled-covariate-shift.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    run.log({f"train/{key}": value for key, value in train.items() if key != "rows"} | {f"test_inputs_only/{key}": value for key, value in test.items() if key != "rows"})
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    # Run the diagnostic as a module entry point.
    raise SystemExit(main())
