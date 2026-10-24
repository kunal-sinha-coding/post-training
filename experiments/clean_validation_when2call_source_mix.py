"""Train source-matched When2Call mixtures and evaluate separate SFT and preference validation splits.

The flow loads only the released When2Call SFT and preference training sources, removes the direct class,
samples each source deterministically, creates source-specific clean validation partitions, trains the Jina
encoder, and saves training and both validation metric sets without loading official test labels.
"""
from __future__ import annotations

import argparse
import atexit
import json
import os
import random
from collections import Counter
from pathlib import Path

import torch
from datasets import load_dataset

from experiments.clean_validation_baseline import (
    load_model,
    load_sft_training_rows,
    load_training_rows,
    split_examples,
    train_epoch,
)
from experiments.train_when2call_jina import (
    LABELS,
    Example,
    batch_metrics,
    prepare_train_examples,
    tokenize_examples,
)


POOL_DATASET = "Emulated-Inc/tool-decision-training-pool"


def sample_source(examples: list[Example], sample_size: int, seed: int) -> list[Example]:
    """Select a deterministic balanced sample from one training source."""
    # Shuffle a copied source so the source record order never controls the candidate composition.
    items = list(examples)
    random.Random(seed).shuffle(items)
    return items[:sample_size]


def filter_direct(examples: list[Example]) -> list[Example]:
    """Remove the benchmark-absent direct response class from a source."""
    # Keep only the three classes that occur in the current When2Call test distribution.
    direct_label = LABELS.index("direct")
    return [item for item in examples if item.label != direct_label]


def load_pool_examples(sample_size: int, seed: int) -> list[Example]:
    """Load and sample the previously identified decision-training pool."""
    # Reuse the pool's When2Call-compatible fields while excluding malformed and direct rows.
    rows = load_dataset(POOL_DATASET, split="train", streaming=True)
    examples = []
    for index, row in enumerate(rows):
        if not isinstance(row.get("chosen_response"), dict) or not row["chosen_response"].get("content"):
            continue
        examples.extend(prepare_train_examples([row], source_offset=index))
        if len(examples) >= sample_size * 4:
            break
    return sample_source(filter_direct(examples), sample_size, seed)


def main() -> int:
    """Train one source-matched mixture and persist clean evidence."""
    # Parse the mixture, split, and optimization settings before loading model state.
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--pref-sample", type=int, required=True)
    parser.add_argument("--sft-sample", type=int, required=True)
    parser.add_argument("--pool-sample", type=int, default=0)
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--seed", type=int, default=20261031)
    parser.add_argument("--split-seed", type=int, default=20261031)
    parser.add_argument("--max-length", type=int, default=4096)
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--learning-rate", type=float, default=1e-5)
    parser.add_argument("--weight-decay", type=float, default=0.005)
    args = parser.parse_args()
    # Open W&B before data loading so source and runtime failures are recorded.
    import wandb

    if not os.getenv("WANDB_API_KEY"):
        raise RuntimeError("WANDB_API_KEY is required for clean validation experiments.")
    run = wandb.init(project=os.getenv("WANDB_PROJECT", "when2call-research"), entity=os.getenv("WANDB_ENTITY"), name=f"when2call-source-mix-seed{args.seed}", job_type="clean-validation", config=vars(args))
    atexit.register(run.finish)
    random.seed(args.seed)
    torch.manual_seed(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    # Prepare filtered and independently sampled preference and SFT sources.
    pref = sample_source(filter_direct(prepare_train_examples(load_training_rows())), args.pref_sample, args.seed)
    sft = sample_source(filter_direct(prepare_train_examples(load_sft_training_rows())), args.sft_sample, args.seed + 1)
    pool = load_pool_examples(args.pool_sample, args.seed + 2) if args.pool_sample else []
    # Split each source independently so both clean validation sets remain interpretable.
    pref_train, pref_validation = split_examples(pref, 0.2, args.split_seed)
    sft_train, sft_validation = split_examples(sft, 0.2, args.split_seed + 1)
    pool_train, pool_validation = split_examples(pool, 0.2, args.split_seed + 2) if pool else ([], [])
    train = pref_train + sft_train + pool_train
    # Load and tokenize only the training and clean validation partitions.
    model, tokenizer = load_model(device, args.max_length)
    tokenize_examples(train, tokenizer)
    tokenize_examples(pref_validation, tokenizer)
    tokenize_examples(sft_validation, tokenizer)
    tokenize_examples(pool_validation, tokenizer)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate, weight_decay=args.weight_decay)
    losses = []
    # Run the requested number of complete training epochs over the mixed source pool.
    for epoch in range(args.epochs):
        losses.append(train_epoch(model, tokenizer, train, device, optimizer, "cross_entropy", args.seed + epoch, batch_size=args.batch_size))
    # Measure training performance and both source-specific held-out validation sets.
    train_metrics = batch_metrics(model, tokenizer, train, device, list(range(len(LABELS))))
    pref_metrics = batch_metrics(model, tokenizer, pref_validation, device, list(range(len(LABELS))))
    sft_metrics = batch_metrics(model, tokenizer, sft_validation, device, list(range(len(LABELS)))) if sft_validation else None
    pool_metrics = batch_metrics(model, tokenizer, pool_validation, device, list(range(len(LABELS)))) if pool_validation else None
    # Save the candidate and complete clean evidence without loading official test labels.
    args.output_dir.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(args.output_dir)
    metadata = {
        "dataset": "nvidia/When2Call",
        "official_test_loaded": False,
        "direct_filtered": True,
        "pref_sample": args.pref_sample,
        "sft_sample": args.sft_sample,
        "pref_training_examples": len(pref_train),
        "pref_validation_examples": len(pref_validation),
        "sft_training_examples": len(sft_train),
        "sft_validation_examples": len(sft_validation),
        "pool_sample": args.pool_sample,
        "pool_training_examples": len(pool_train),
        "pool_validation_examples": len(pool_validation),
        "train_examples": len(train),
        "train_label_counts": dict(Counter(LABELS[item.label] for item in train)),
        "pref_validation_label_counts": dict(Counter(LABELS[item.label] for item in pref_validation)),
        "sft_validation_label_counts": dict(Counter(LABELS[item.label] for item in sft_validation)),
        "losses": losses,
        "train_metrics": train_metrics,
        "pref_validation_metrics": pref_metrics,
        "sft_validation_metrics": sft_metrics,
        "pool_validation_metrics": pool_metrics,
        "model": "jinaai/jina-embeddings-v2-small-en",
        "seed": args.seed,
        "split_seed": args.split_seed,
        "max_length": args.max_length,
        "batch_size": args.batch_size,
        "learning_rate": args.learning_rate,
        "weight_decay": args.weight_decay,
        "device": str(device),
    }
    (args.output_dir / "metrics.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    # Log all evidence categories while keeping official test labels out of selection.
    log_record = {"train/accuracy": train_metrics["accuracy"], "train/macro_f1": train_metrics["macro_f1"], "validation/pref_accuracy": pref_metrics["accuracy"], "validation/pref_macro_f1": pref_metrics["macro_f1"], "validation/sft_accuracy": sft_metrics["accuracy"], "validation/sft_macro_f1": sft_metrics["macro_f1"], "training/loss": sum(losses) / max(1, len(losses))}
    if pool_metrics:
        log_record.update({"validation/pool_accuracy": pool_metrics["accuracy"], "validation/pool_macro_f1": pool_metrics["macro_f1"]})
    run.log(log_record)
    summary = {"pref_validation_accuracy": pref_metrics["accuracy"], "pref_validation_macro_f1": pref_metrics["macro_f1"], "output_dir": str(args.output_dir)}
    if sft_metrics:
        summary.update({"sft_validation_accuracy": sft_metrics["accuracy"], "sft_validation_macro_f1": sft_metrics["macro_f1"]})
    run.summary.update(summary)
    print(json.dumps({"train": train_metrics, "pref_validation": pref_metrics, "sft_validation": sft_metrics, "pool_validation": pool_metrics, "losses": losses}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
