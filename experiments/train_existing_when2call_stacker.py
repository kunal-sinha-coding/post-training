"""Fit a linear meta-classifier from two frozen When2Call model families.

The flow holds out a fixed partition of the SFT source, scores frozen encoder and Qwen
members once, fits a small linear classifier on one part of that partition, and measures
only aggregate metrics on the other part. It does not load official test data or save row outputs.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import time

import torch

from experiments.clean_validation_baseline import load_sft_training_rows, split_examples
from experiments.existing_when2call_hybrid import ENCODERS, QWEN, QWEN_BASE, encoder_logits
from experiments.train_qwen_when2call import ClassificationRow, label_token_ids, load_model, make_prompt, score_rows, write_heartbeat
from experiments.train_when2call_jina import LABELS, metric_values, prepare_train_examples


def aggregate(labels: torch.Tensor, logits: torch.Tensor) -> dict[str, float]:
    # Reduce one partition to accuracy and four-class macro F1 only.
    result = metric_values(labels.tolist(), logits.argmax(-1).tolist(), list(range(len(LABELS))))
    return {key: result[key] for key in ("accuracy", "macro_f1")}


def main() -> int:
    # Freeze source and split settings before model scoring and meta-classifier fitting.
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--holdout-seed", type=int, default=20261026)
    parser.add_argument("--meta-split-seed", type=int, default=20261027)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--epochs", type=int, default=200)
    parser.add_argument("--learning-rate", type=float, default=0.05)
    parser.add_argument("--weight-decay", type=float, default=0.01)
    args = parser.parse_args()
    import wandb
    if not os.getenv("WANDB_API_KEY"):
        raise RuntimeError("WANDB_API_KEY is required for clean validation experiments.")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    run = wandb.init(
        project=os.getenv("WANDB_PROJECT", "when2call-research"),
        entity=os.getenv("WANDB_ENTITY"),
        name="existing-when2call-linear-stacker-validation",
        job_type="clean-validation",
        config={"encoder": ENCODERS[2], "qwen": QWEN, "qwen_base": QWEN_BASE, "source": "nvidia/When2Call train_sft", "holdout_seed": args.holdout_seed, "meta_split_seed": args.meta_split_seed, "epochs": args.epochs, "learning_rate": args.learning_rate, "weight_decay": args.weight_decay, "official_test_loaded": False},
    )
    started = time.time()
    try:
        # Build the validation source without loading the official test split.
        rows = list(load_sft_training_rows())
        examples = prepare_train_examples(rows)
        _, holdout = split_examples(examples, 0.2, args.holdout_seed)
        meta_train, meta_validation = split_examples(holdout, 0.33, args.meta_split_seed)
        selected = {int(item.source_id) for item in (*meta_train, *meta_validation)}
        indices = sorted(selected)
        by_id = {int(item.source_id): item for item in examples}
        scoring_examples = [by_id[index] for index in indices]
        labels = torch.tensor([item.label for item in scoring_examples], dtype=torch.long)
        positions = {source_id: position for position, source_id in enumerate(indices)}
        train_indices = torch.tensor([positions[int(item.source_id)] for item in meta_train], dtype=torch.long)
        validation_indices = torch.tensor([positions[int(item.source_id)] for item in meta_validation], dtype=torch.long)
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        write_heartbeat(args.output_dir / "heartbeat.json", "encoder-scoring")
        encoder = encoder_logits(ENCODERS[2], scoring_examples, args, device).softmax(-1)
        model, tokenizer = load_model(QWEN_BASE, device, 16)
        if not hasattr(model, "load_adapter"):
            raise TypeError("The Qwen base did not produce a PEFT model.")
        model.load_adapter(QWEN, adapter_name="frozen")
        model.set_adapter("frozen")
        model.eval()
        qwen_rows = [ClassificationRow(make_prompt(rows[index]), by_id[index].label, None) for index in indices]
        qwen_scores = []
        with torch.inference_mode():
            for start in range(0, len(qwen_rows), args.batch_size):
                write_heartbeat(args.output_dir / "heartbeat.json", "qwen-scoring", start)
                qwen_scores.append(score_rows(model, tokenizer, qwen_rows[start:start + args.batch_size], label_token_ids(tokenizer), device, 4096).exp().cpu())
        qwen = torch.cat(qwen_scores)
        features = torch.cat((encoder, qwen), dim=-1).float()
        del model, tokenizer, qwen_scores
        if len(torch.unique(labels[train_indices])) != len(LABELS):
            raise ValueError("The meta-training partition does not contain all four labels.")
        torch.manual_seed(args.meta_split_seed)
        stacker = torch.nn.Linear(features.shape[-1], len(LABELS))
        optimizer = torch.optim.AdamW(stacker.parameters(), lr=args.learning_rate, weight_decay=args.weight_decay)
        train_x, train_y = features[train_indices], labels[train_indices]
        for epoch in range(args.epochs):
            optimizer.zero_grad(set_to_none=True)
            loss = torch.nn.functional.cross_entropy(stacker(train_x), train_y)
            loss.backward()
            optimizer.step()
            if epoch % 20 == 0:
                write_heartbeat(args.output_dir / "heartbeat.json", "stacker-training", epoch)
        with torch.inference_mode():
            train_logits = stacker(train_x)
            validation_x = features[validation_indices]
            validation_y = labels[validation_indices]
            validation_logits = stacker(validation_x)
            average_train = ((encoder[train_indices] + qwen[train_indices]) / 2).clamp_min(1e-8).log()
            average_validation = ((encoder[validation_indices] + qwen[validation_indices]) / 2).clamp_min(1e-8).log()
            results = {
                "stacker_train": aggregate(train_y, train_logits),
                "average_train": aggregate(train_y, average_train),
                "stacker_validation": aggregate(validation_y, validation_logits),
                "average_validation": aggregate(validation_y, average_validation),
            }
        for name, value in results.items():
            run.log({f"{name}/accuracy": value["accuracy"], f"{name}/macro_f1": value["macro_f1"]})
        artifact = {
            "feature_order": ["encoder_probability_" + label for label in LABELS] + ["qwen_probability_" + label for label in LABELS],
            "class_order": LABELS,
            "coefficients": stacker.weight.detach().tolist(),
            "intercepts": stacker.bias.detach().tolist(),
            "fit_source": "nvidia/When2Call train_sft held-out partition",
            "holdout_seed": args.holdout_seed,
            "meta_split_seed": args.meta_split_seed,
            "meta_training_examples": len(meta_train),
            "meta_validation_examples": len(meta_validation),
            "training_configuration": {"epochs": args.epochs, "learning_rate": args.learning_rate, "weight_decay": args.weight_decay},
            "validation_metrics": results,
            "official_test_loaded": False,
        }
        artifact["git_commit"] = subprocess.check_output(["git", "-c", "safe.directory=/workspace/post-training", "rev-parse", "HEAD"], text=True).strip()
        artifact["wandb_run_id"] = run.id
        artifact["wandb_run_url"] = run.url
        (args.output_dir / "stacker.json").write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
        metadata = {**artifact, "status": "completed", "train_metrics": results["stacker_train"], "development_metrics": results["stacker_validation"], "runtime_seconds": time.time() - started}
        (args.output_dir / "metrics.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
        run.summary.update({"status": "completed", "train_accuracy": results["stacker_train"]["accuracy"], "validation_accuracy": results["stacker_validation"]["accuracy"], "validation_macro_f1": results["stacker_validation"]["macro_f1"], "output_dir": str(args.output_dir)})
        write_heartbeat(args.output_dir / "heartbeat.json", "completed")
        print(json.dumps({"examples": {"meta_train": len(meta_train), "meta_validation": len(meta_validation)}, "metrics": results}, indent=2))
    except BaseException as error:
        run.summary.update({"status": "failed", "error": repr(error)})
        write_heartbeat(args.output_dir / "heartbeat.json", "failed")
        raise
    finally:
        run.finish()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
