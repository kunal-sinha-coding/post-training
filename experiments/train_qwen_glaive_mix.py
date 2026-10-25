"""Train Qwen SFT on preference data plus filtered Glaive decisions.

The flow loads the When2Call preference training split and a deterministic Glaive sample,
creates separate source validation partitions, trains a fresh LoRA adapter, and records
training and clean validation metrics. The official test split is never loaded here.
"""
from __future__ import annotations

import argparse
import atexit
import json
import os
import random
from pathlib import Path

import torch

from experiments.clean_validation_glaive import sample_glaive_examples
from experiments.train_qwen_when2call import (
    ClassificationRow,
    DATASET_NAME,
    evaluate,
    label_token_ids,
    load_model,
    load_rows,
    make_prompt,
    prepare_rows,
    split_rows,
    train_epoch,
    write_heartbeat,
)
from experiments.train_when2call_jina import LABELS


def prepare_glaive_rows(sample_size: int, seed: int) -> list[ClassificationRow]:
    # Convert non-direct Glaive assistant decisions to the existing Qwen action prompt.
    examples = sample_glaive_examples(sample_size, seed)
    return [ClassificationRow(make_prompt({"messages": [{"role": "user", "content": item.text}], "tools": []}), item.label, None) for item in examples]


def main() -> int:
    # Freeze dataset, split, and optimization settings before initializing the tracked run.
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="Qwen/Qwen2.5-1.5B-Instruct")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--glaive-sample", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=20261028)
    parser.add_argument("--split-seed", type=int, default=20261028)
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--max-length", type=int, default=4096)
    parser.add_argument("--learning-rate", type=float, default=2e-5)
    parser.add_argument("--weight-decay", type=float, default=0.01)
    parser.add_argument("--lora-rank", type=int, default=16)
    args = parser.parse_args()
    import wandb
    if not os.getenv("WANDB_API_KEY"):
        raise RuntimeError("WANDB_API_KEY is required for Qwen experiments.")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    run = wandb.init(
        project=os.getenv("WANDB_PROJECT", "when2call-research"),
        entity=os.getenv("WANDB_ENTITY"),
        name=f"qwen-glaive{args.glaive_sample}-pref-full-{args.output_dir.name}",
        job_type="qwen-when2call-clean-validation",
        config={**vars(args), "dataset": [DATASET_NAME + ":train_pref", "glaiveai/glaive-function-calling-v2"], "glaive_direct_filtered": True, "official_test_loaded": False},
    )
    atexit.register(run.finish)
    random.seed(args.seed)
    torch.manual_seed(args.seed)
    try:
        # Split the full preference source and Glaive source independently to preserve source-specific validation.
        pref_train, pref_validation = split_rows(prepare_rows(load_rows()), args.split_seed)
        glaive_train, glaive_validation = split_rows(prepare_glaive_rows(args.glaive_sample, args.seed + 1), args.split_seed + 1)
        training_rows = pref_train + glaive_train
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        write_heartbeat(args.output_dir / "heartbeat.json", "model-loading")
        model, tokenizer = load_model(args.model, device, args.lora_rank)
        token_ids = label_token_ids(tokenizer)
        optimizer = torch.optim.AdamW((parameter for parameter in model.parameters() if parameter.requires_grad), lr=args.learning_rate, weight_decay=args.weight_decay)
        losses = []
        # Train a fresh adapter for the requested epochs over both predeclared sources.
        for epoch in range(args.epochs):
            losses.append(train_epoch(model, tokenizer, training_rows, token_ids, "sft", device, optimizer, args.max_length, args.batch_size, 0.1, args.seed + epoch, args.output_dir / "heartbeat.json"))
        # Measure training and both source-specific clean validation partitions.
        train_metrics = evaluate(model, tokenizer, training_rows, token_ids, device, args.max_length, args.batch_size, args.output_dir / "heartbeat.json")
        pref_metrics = evaluate(model, tokenizer, pref_validation, token_ids, device, args.max_length, args.batch_size, args.output_dir / "heartbeat.json")
        glaive_metrics = evaluate(model, tokenizer, glaive_validation, token_ids, device, args.max_length, args.batch_size, args.output_dir / "heartbeat.json")
        model.save_pretrained(args.output_dir)
        tokenizer.save_pretrained(args.output_dir)
        # Persist exact source sizes and aggregate metrics without official benchmark access.
        config = {key: str(value) if isinstance(value, Path) else value for key, value in vars(args).items()}
        metadata = {
            "model": args.model,
            "objective": "sft",
            "dataset": [DATASET_NAME + ":train_pref", "glaiveai/glaive-function-calling-v2"],
            "official_test_loaded": False,
            "glaive_direct_filtered": True,
            "preference_training_examples": len(pref_train),
            "preference_validation_examples": len(pref_validation),
            "glaive_training_examples": len(glaive_train),
            "glaive_validation_examples": len(glaive_validation),
            "train_examples": len(training_rows),
            "train_metrics": train_metrics,
            "preference_validation_metrics": pref_metrics,
            "glaive_validation_metrics": glaive_metrics,
            "losses": losses,
            "label_order": LABELS,
            "label_tokens": token_ids,
            "config": config,
            "device": str(device),
            "wandb_run_id": run.id,
            "wandb_run_url": run.url,
        }
        (args.output_dir / "metrics.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
        run.summary.update({"status": "completed", "train_accuracy": train_metrics["accuracy"], "pref_validation_accuracy": pref_metrics["accuracy"], "glaive_validation_accuracy": glaive_metrics["accuracy"], "output_dir": str(args.output_dir)})
        write_heartbeat(args.output_dir / "heartbeat.json", "completed")
        print(json.dumps({"train": train_metrics, "preference_validation": pref_metrics, "glaive_validation": glaive_metrics}, indent=2))
    except BaseException as error:
        run.summary.update({"status": "failed", "error": repr(error)})
        write_heartbeat(args.output_dir / "heartbeat.json", "failed")
        raise
    finally:
        run.finish()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
