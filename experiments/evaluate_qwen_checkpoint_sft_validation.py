"""Measure saved Qwen adapters on a clean, capped When2Call validation sample.

The flow loads the independent `train_sft` source, infers its existing action labels, selects one
deterministic stratified sample of at most 500 rows, evaluates each frozen adapter, and records only
validation metrics. It also attaches the post hoc validation record to the original training artifact.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
from collections import Counter
from pathlib import Path

import torch
import wandb

from experiments.clean_validation_baseline import load_sft_training_rows
from experiments.train_qwen_when2call import ClassificationRow, evaluate, label_token_ids, load_model, make_prompt
from experiments.train_when2call_jina import LABELS, response_label


def load_validation_rows(sample_size: int, seed: int) -> tuple[list[ClassificationRow], dict]:
    """Build one fixed stratified sample from the separate supervised training configuration."""
    # Format every eligible source row with the same prompt and response-to-label mapping used in training.
    grouped = {label: [] for label in range(len(LABELS))}
    for row in load_sft_training_rows():
        assistants = [message for message in row["messages"] if message["role"] == "assistant"]
        if assistants:
            label = LABELS.index(response_label(assistants[-1]["content"]))
            grouped[label].append(ClassificationRow(make_prompt(row), label, None))
    # Select proportional class counts, then reserve one slot for any class present in the source but absent from the random sample.
    available = [row for rows in grouped.values() for row in rows]
    if sample_size >= len(available):
        selected = list(available)
    else:
        exact = {label: sample_size * len(rows) / len(available) for label, rows in grouped.items()}
        counts = {label: int(value) for label, value in exact.items()}
        remainder = sample_size - sum(counts.values())
        for label in sorted(grouped, key=lambda value: (exact[value] - counts[value], -value), reverse=True)[:remainder]:
            counts[label] += 1
        selected = []
        for label, rows in grouped.items():
            selected.extend(random.Random(seed + label).sample(rows, counts[label]))
        random.Random(seed).shuffle(selected)
        # Keep rare observed labels in the sample so their validation F1 is measurable.
        for label in sorted(set(grouped) - {row.label for row in selected}):
            if not grouped[label]:
                continue
            replacement = random.Random(seed + label).choice(grouped[label])
            selected_counts = Counter(row.label for row in selected)
            replace_index = max((index for index, row in enumerate(selected) if selected_counts[row.label] > 1), key=lambda index: selected_counts[selected[index].label])
            selected[replace_index] = replacement
    # Hash prompt-label pairs so the exact sample can be reproduced without storing source text.
    row_hashes = sorted(hashlib.sha256((row.prompt + "\n" + str(row.label)).encode()).hexdigest() for row in selected)
    metadata = {
        "source": "nvidia/When2Call:train_sft",
        "source_rows": len(available),
        "sample_rows": len(selected),
        "sample_seed": seed,
        "sample_fingerprint": hashlib.sha256("\n".join(row_hashes).encode()).hexdigest(),
        "label_counts": dict(sorted(Counter(row.label for row in selected).items())),
        "source_independent_of_train_pref_and_bfcl": True,
    }
    return selected, metadata


def main() -> int:
    """Evaluate each requested adapter and attach its clean validation result to the run record."""
    # Parse frozen checkpoint paths and capped validation controls before loading any model weights.
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="Qwen/Qwen2.5-1.5B-Instruct")
    parser.add_argument("--checkpoint", type=Path, action="append", required=True)
    parser.add_argument("--run-metrics", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--sample-size", type=int, default=500)
    parser.add_argument("--seed", type=int, default=20261057)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--max-length", type=int, default=4096)
    parser.add_argument("--lora-rank", type=int, default=16)
    args = parser.parse_args()
    # Reject an invalid evaluation cap and require online tracking before reading the validation source.
    if not 1 <= args.sample_size <= 500:
        parser.error("--sample-size must be between 1 and 500.")
    if not os.getenv("WANDB_API_KEY"):
        raise RuntimeError("WANDB_API_KEY is required for Qwen research measurements.")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    validation_rows, sample_metadata = load_validation_rows(args.sample_size, args.seed)
    run = wandb.init(
        project=os.getenv("WANDB_PROJECT", "when2call-research"),
        entity=os.getenv("WANDB_ENTITY"),
        name=args.output_dir.name,
        job_type="posthoc-clean-validation-measurement",
        config={"model": args.model, "checkpoints": [str(path) for path in args.checkpoint], "validation": sample_metadata, "test_data_loaded": False},
    )
    # Keep model evaluation deterministic and use a single fixed sample for every candidate checkpoint.
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    all_results = {}
    for checkpoint in args.checkpoint:
        if not checkpoint.is_dir():
            raise FileNotFoundError(f"Checkpoint does not exist: {checkpoint}")
        model, tokenizer = load_model(args.model, device, args.lora_rank, str(checkpoint))
        metrics = evaluate(model, tokenizer, validation_rows, label_token_ids(tokenizer), device, args.max_length, args.batch_size)
        all_results[str(checkpoint)] = metrics
        run.log({f"{checkpoint.name}/accuracy": metrics["accuracy"], f"{checkpoint.name}/macro_f1": metrics["macro_f1"], f"{checkpoint.name}/examples": metrics["examples"]})
        del model, tokenizer
        if device.type == "cuda":
            torch.cuda.empty_cache()
    # Record aggregate validation evidence while preserving the original test-independent selection rule.
    result = {
        "status": "completed",
        "measurement": "posthoc_clean_validation",
        "purpose": "Fill missing held-out validation measurements for the fixed two-epoch full-data BFCL experiment.",
        "validation_sample": sample_metadata,
        "checkpoint_metrics": all_results,
        "sft_validation_metrics": all_results,
        "official_test_data_loaded": False,
        "official_test_loaded": False,
        "test_status": "not measured; this is a validation-only follow-up",
        "test_labels_used_for_selection": False,
        "wandb_run_id": run.id,
        "wandb_run_url": run.url,
        "device": str(device),
    }
    output_metrics = args.output_dir / "metrics.json"
    output_metrics.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    original_metrics = json.loads(args.run_metrics.read_text(encoding="utf-8"))
    epoch_by_checkpoint = {str(record.get("checkpoint")): record for record in original_metrics.get("epoch_records", [])}
    for checkpoint, metrics in all_results.items():
        record = epoch_by_checkpoint.get(checkpoint)
        if record is not None:
            record["heldout_validation_metrics"] = metrics
            record["validation_source"] = sample_metadata["source"]
            record["validation_examples"] = metrics["examples"]
            record["validation_measurement_timing"] = "posthoc after the fixed training schedule; not used for checkpoint selection"
    original_metrics["posthoc_clean_validation_measurement"] = {"artifact": str(output_metrics), "validation_sample": sample_metadata, "checkpoint_metrics": all_results, "selection_use": "none"}
    args.run_metrics.write_text(json.dumps(original_metrics, indent=2) + "\n", encoding="utf-8")
    run.finish()
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    # Return a nonzero process status if validation fails so the watchdog can report the failure.
    raise SystemExit(main())
