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
import requests

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
BFCL_BASE = "https://raw.githubusercontent.com/ShishirPatil/gorilla/main/berkeley-function-call-leaderboard/bfcl_eval/data/"
BFCL_FILES = ("BFCL_v4_live_simple.json", "BFCL_v4_live_multiple.json", "BFCL_v4_live_parallel.json", "BFCL_v4_live_parallel_multiple.json", "BFCL_v4_live_irrelevance.json", "BFCL_v4_live_relevance.json")


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


def load_bfcl_examples(sample_size: int, seed: int, call_only: bool = False) -> list[Example]:
    """Load a bounded BFCL Live source sample with conservative action labels."""
    # Use only public BFCL source categories and map irrelevance to refusal and all explicit call categories to tool use.
    examples = []
    for filename in BFCL_FILES:
        category = filename.removeprefix("BFCL_v4_live_").removesuffix(".json")
        if call_only and category == "irrelevance":
            continue
        rows = requests.get(BFCL_BASE + filename, timeout=30).text.splitlines()
        for index, line in enumerate(rows):
            row = json.loads(line)
            question = " ".join(str(message.get("content", "")) for turn in row.get("question", []) for message in turn)
            tools = "\n".join(json.dumps(item, sort_keys=True) for item in row.get("function", [])) or "No tools are available."
            label = LABELS.index("cannot_answer") if category == "irrelevance" else LABELS.index("tool_call")
            examples.append(Example(f"Question: {question}\nAvailable tools:\n{tools}", label, f"bfcl-{category}-{index}"))
    return sample_source(examples, sample_size, seed)


def tokenize_bounded(examples: list[Example], tokenizer: object, max_length: int) -> None:
    """Tokenize source examples with an explicit memory-safe maximum length."""
    # Truncate only this mixed-source experiment so long BFCL contexts cannot exhaust GPU memory.
    for item in examples:
        item.token_ids = tokenizer(item.text, add_special_tokens=True, truncation=True, max_length=max_length, verbose=False)["input_ids"]


def main() -> int:
    """Train one source-matched mixture and persist clean evidence."""
    # Parse the mixture, split, and optimization settings before loading model state.
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--pref-sample", type=int, required=True)
    parser.add_argument("--sft-sample", type=int, required=True)
    parser.add_argument("--pool-sample", type=int, default=0)
    parser.add_argument("--bfcl-sample", type=int, default=0)
    parser.add_argument("--bfcl-call-only", action="store_true")
    parser.add_argument("--bfcl-simple-multiple-only", action="store_true")
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
    bfcl = load_bfcl_examples(args.bfcl_sample, args.seed + 3, args.bfcl_call_only) if args.bfcl_sample else []
    if args.bfcl_simple_multiple_only:
        bfcl = [item for item in bfcl if item.source_id.startswith("bfcl-simple-") or item.source_id.startswith("bfcl-multiple-")]
    # Split each source independently so both clean validation sets remain interpretable.
    pref_train, pref_validation = split_examples(pref, 0.2, args.split_seed)
    sft_train, sft_validation = split_examples(sft, 0.2, args.split_seed + 1)
    pool_train, pool_validation = split_examples(pool, 0.2, args.split_seed + 2) if pool else ([], [])
    bfcl_train, bfcl_validation = split_examples(bfcl, 0.2, args.split_seed + 3) if bfcl else ([], [])
    train = pref_train + sft_train + pool_train + bfcl_train
    # Load and tokenize only the training and clean validation partitions.
    model, tokenizer = load_model(device, args.max_length)
    tokenize_bounded(train, tokenizer, args.max_length)
    tokenize_bounded(pref_validation, tokenizer, args.max_length)
    tokenize_bounded(sft_validation, tokenizer, args.max_length)
    tokenize_bounded(pool_validation, tokenizer, args.max_length)
    tokenize_bounded(bfcl_validation, tokenizer, args.max_length)
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
    bfcl_metrics = batch_metrics(model, tokenizer, bfcl_validation, device, list(range(len(LABELS)))) if bfcl_validation else None
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
        "bfcl_sample": args.bfcl_sample,
        "bfcl_training_examples": len(bfcl_train),
        "bfcl_validation_examples": len(bfcl_validation),
        "train_examples": len(train),
        "train_label_counts": dict(Counter(LABELS[item.label] for item in train)),
        "pref_validation_label_counts": dict(Counter(LABELS[item.label] for item in pref_validation)),
        "sft_validation_label_counts": dict(Counter(LABELS[item.label] for item in sft_validation)),
        "losses": losses,
        "train_metrics": train_metrics,
        "pref_validation_metrics": pref_metrics,
        "sft_validation_metrics": sft_metrics,
        "pool_validation_metrics": pool_metrics,
        "bfcl_validation_metrics": bfcl_metrics,
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
    if bfcl_metrics:
        log_record.update({"validation/bfcl_accuracy": bfcl_metrics["accuracy"], "validation/bfcl_macro_f1": bfcl_metrics["macro_f1"]})
    run.log(log_record)
    summary = {"pref_validation_accuracy": pref_metrics["accuracy"], "pref_validation_macro_f1": pref_metrics["macro_f1"], "output_dir": str(args.output_dir)}
    if sft_metrics:
        summary.update({"sft_validation_accuracy": sft_metrics["accuracy"], "sft_validation_macro_f1": sft_metrics["macro_f1"]})
    run.summary.update(summary)
    print(json.dumps({"train": train_metrics, "pref_validation": pref_metrics, "sft_validation": sft_metrics, "pool_validation": pool_metrics, "losses": losses}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
