"""Train a leakage-safe encoder on filtered Glaive and When2Call examples.

The flow samples assistant decision points from Glaive Function Calling v2, removes the
direct class, combines the result with filtered When2Call preference and SFT examples,
creates a deterministic clean split, trains a Jina classifier, and saves metrics without
loading the official test split.
"""
from __future__ import annotations

import argparse
import atexit
import json
import os
import random
import re
from collections import Counter
from pathlib import Path

import torch
from datasets import load_dataset

from experiments.clean_validation_baseline import (
    batch_metrics,
    load_model,
    split_examples,
    train_epoch,
)
from experiments.train_when2call_jina import (
    LABELS,
    LABEL_TO_ID,
    Example,
    prepare_train_examples,
    response_label,
    tokenize_examples,
)


GLAIVE_DATASET = "glaiveai/glaive-function-calling-v2"
WHEN2CALL_DATASET = "nvidia/When2Call"


def normalize_glaive_response(response: str) -> str:
    """Normalize Glaive function-call syntax before applying the shared heuristic."""
    # Convert Glaive's functioncall marker into the canonical tool-call marker.
    if re.search(r"(?i)\b(functioncall|function_call|tool_call)\b", response):
        return "<TOOLCALL>[]</TOOLCALL>"
    return response


def glaive_decision_points(chat: str, system: str) -> list[Example]:
    """Convert one Glaive conversation into assistant decision-point examples."""
    # Preserve the visible history before each assistant action so the encoder sees the decision context.
    blocks = re.split(r"\n\s*\n\s*", str(chat))
    history = [f"SYSTEM: {system}"] if system else []
    examples = []
    for index, block in enumerate(blocks):
        match = re.match(r"(USER|FUNCTION RESPONSE|ASSISTANT):\s*(.*?)(?:\s*<\|endoftext\|>)?$", block, re.IGNORECASE | re.DOTALL)
        if not match:
            continue
        role = match.group(1).upper()
        content = match.group(2).strip()
        if role == "ASSISTANT":
            # Treat Glaive's explicit function-call marker as a tool decision before applying text heuristics.
            label = "tool_call" if re.search(r"(?i)\b(functioncall|function_call|tool_call)\b", content) else response_label(content)
            if label != "direct":
                context = "\n\n".join(history + ["ASSISTANT ACTION:"])
                examples.append(Example(context, LABEL_TO_ID[label], f"glaive-{index}"))
        history.append(f"{role}: {content}")
    return examples


def sample_glaive_examples(sample_size: int, seed: int) -> list[Example]:
    """Reservoir-sample a deterministic number of non-direct Glaive decisions."""
    # Stream the large dataset and keep a bounded sample without materializing all rows.
    rng = random.Random(seed)
    reservoir: list[Example] = []
    seen = 0
    rows = load_dataset(GLAIVE_DATASET, split="train", streaming=True)
    for row in rows:
        for example in glaive_decision_points(row["chat"], row["system"]):
            seen += 1
            if len(reservoir) < sample_size:
                reservoir.append(example)
            else:
                replacement = rng.randrange(seen)
                if replacement < sample_size:
                    reservoir[replacement] = example
    rng.shuffle(reservoir)
    return reservoir


def load_when2call_examples(pref_sample: int, sft_sample: int, seed: int) -> list[Example]:
    """Load bounded non-direct When2Call preference and SFT examples."""
    # Keep both sources available while removing the benchmark-absent direct class.
    pref = prepare_train_examples(load_dataset(WHEN2CALL_DATASET, "train_pref", split="train"))
    sft = prepare_train_examples(load_dataset(WHEN2CALL_DATASET, "train_sft", split="train"))
    pref = [item for item in pref if LABELS[item.label] != "direct"]
    sft = [item for item in sft if LABELS[item.label] != "direct"]
    rng = random.Random(seed)
    rng.shuffle(pref)
    rng.shuffle(sft)
    return pref[:pref_sample] + sft[:sft_sample]


def main() -> int:
    """Train the filtered generic-data encoder and save clean-validation evidence."""
    # Parse bounded data and optimization settings before starting the tracked run.
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--glaive-sample", type=int, default=10000)
    parser.add_argument("--pref-sample", type=int, default=3000)
    parser.add_argument("--sft-sample", type=int, default=3000)
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--seed", type=int, default=20261023)
    parser.add_argument("--split-seed", type=int, default=20261023)
    parser.add_argument("--max-length", type=int, default=4096)
    parser.add_argument("--learning-rate", type=float, default=5e-5)
    parser.add_argument("--weight-decay", type=float, default=0.01)
    args = parser.parse_args()
    # Open W&B before loading data so data and runtime failures are recorded.
    import wandb

    if not os.getenv("WANDB_API_KEY"):
        raise RuntimeError("WANDB_API_KEY is required for clean validation experiments.")
    run = wandb.init(project=os.getenv("WANDB_PROJECT", "when2call-research"), entity=os.getenv("WANDB_ENTITY"), name=f"when2call-glaive-filtered-seed{args.seed}", job_type="clean-validation", config=vars(args))
    atexit.register(run.finish)
    random.seed(args.seed)
    torch.manual_seed(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    # Build the filtered generic and benchmark training pool without loading official labels.
    examples = sample_glaive_examples(args.glaive_sample, args.seed)
    examples.extend(load_when2call_examples(args.pref_sample, args.sft_sample, args.seed + 1))
    train, development = split_examples(examples, 0.2, args.split_seed)
    # Load the existing compact encoder and tokenize only the clean training partitions.
    model, tokenizer = load_model(device, args.max_length)
    tokenize_examples(train, tokenizer)
    tokenize_examples(development, tokenizer)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate, weight_decay=args.weight_decay)
    losses = []
    for epoch in range(args.epochs):
        losses.append(train_epoch(model, tokenizer, train, device, optimizer, "cross_entropy", args.seed + epoch))
    # Measure training and clean held-out performance using all three benchmark classes.
    train_metrics = batch_metrics(model, tokenizer, train, device, list(range(len(LABELS))))
    development_metrics = batch_metrics(model, tokenizer, development, device, list(range(len(LABELS))))
    # Persist the candidate, composition, and clean evidence for asynchronous recording.
    args.output_dir.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(args.output_dir)
    metadata = {
        "dataset": [GLAIVE_DATASET, WHEN2CALL_DATASET],
        "official_test_loaded": False,
        "direct_filtered": True,
        "glaive_sample": args.glaive_sample,
        "pref_sample": args.pref_sample,
        "sft_sample": args.sft_sample,
        "train_examples": len(train),
        "development_examples": len(development),
        "train_label_counts": dict(Counter(LABELS[item.label] for item in train)),
        "development_label_counts": dict(Counter(LABELS[item.label] for item in development)),
        "losses": losses,
        "train_metrics": train_metrics,
        "development_metrics": development_metrics,
        "model": "jinaai/jina-embeddings-v2-small-en",
        "seed": args.seed,
        "split_seed": args.split_seed,
        "max_length": args.max_length,
        "learning_rate": args.learning_rate,
        "weight_decay": args.weight_decay,
        "device": str(device),
    }
    (args.output_dir / "metrics.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    # Log the complete clean evidence while keeping official test labels out of the run.
    run.log({"train/accuracy": train_metrics["accuracy"], "train/macro_f1": train_metrics["macro_f1"], "development/accuracy": development_metrics["accuracy"], "development/macro_f1": development_metrics["macro_f1"], "training/loss": sum(losses) / max(1, len(losses))})
    run.summary.update({"development_accuracy": development_metrics["accuracy"], "development_macro_f1": development_metrics["macro_f1"], "output_dir": str(args.output_dir)})
    print(json.dumps({"train": train_metrics, "development": development_metrics, "losses": losses}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
