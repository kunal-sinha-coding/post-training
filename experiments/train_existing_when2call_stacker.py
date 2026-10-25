"""Fit a linear meta-classifier from two frozen When2Call model families.

The flow builds disjoint meta-training and validation partitions from the SFT source and
an encoder-held-out BFCL source, scores both frozen members once, fits a three-action
linear classifier, and saves aggregate metrics and frozen coefficients only. It never
loads official test data or writes row predictions.
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
from experiments.clean_validation_when2call_source_mix import load_bfcl_examples
from experiments.existing_when2call_hybrid import ENCODERS, QWEN, QWEN_BASE, encoder_logits
from experiments.train_qwen_when2call import ClassificationRow, label_token_ids, load_model, make_prompt, score_rows, write_heartbeat
from experiments.train_when2call_jina import LABELS, Example, metric_values, prepare_train_examples
import experiments.train_when2call_jina as jina_training


def aggregate(labels: torch.Tensor, logits: torch.Tensor) -> dict[str, float]:
    # Reduce one partition to accuracy and four-class macro F1 only.
    result = metric_values(labels.tolist(), logits.argmax(-1).tolist(), list(range(len(LABELS))))
    return {key: result[key] for key in ("accuracy", "macro_f1")}


def bfcl_prompt(example: Example) -> str:
    # Format a BFCL input with the same Qwen prompt structure used by its trainer.
    question, _, tool_text = example.text.partition("\nAvailable tools:\n")
    user_text = question.removeprefix("Question: ")
    return make_prompt({"messages": [{"role": "user", "content": user_text}], "tools": tool_text.splitlines()})


def main() -> int:
    # Freeze source and split settings before model scoring and meta-classifier fitting.
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--holdout-seed", type=int, default=20261026)
    parser.add_argument("--meta-split-seed", type=int, default=20261027)
    parser.add_argument("--bfcl-source-seed", type=int, default=20261051)
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
        config={"encoder": ENCODERS[2], "qwen": QWEN, "qwen_base": QWEN_BASE, "sources": ["nvidia/When2Call train_sft", "BFCL live simple and multiple call-only holdout"], "holdout_seed": args.holdout_seed, "meta_split_seed": args.meta_split_seed, "bfcl_source_seed": args.bfcl_source_seed, "epochs": args.epochs, "learning_rate": args.learning_rate, "weight_decay": args.weight_decay, "official_test_loaded": False},
    )
    started = time.time()
    try:
        # Create a stratified SFT-source partition that neither frozen model used for training.
        sft_rows = list(load_sft_training_rows())
        sft_examples = prepare_train_examples(sft_rows)
        _, sft_holdout = split_examples(sft_examples, 0.2, args.holdout_seed)
        sft_train, sft_validation = split_examples(sft_holdout, 0.33, args.meta_split_seed)
        sft_by_id = {int(item.source_id): item for item in sft_examples}
        sft_pairs = [(sft_by_id[int(item.source_id)], make_prompt(sft_rows[int(item.source_id)]), "train") for item in sft_train]
        sft_pairs += [(sft_by_id[int(item.source_id)], make_prompt(sft_rows[int(item.source_id)]), "validation") for item in sft_validation]
        # Recreate the BFCL heldout source that was not used to train the selected encoder.
        bfcl_source = load_bfcl_examples(1500, args.bfcl_source_seed, call_only=True)
        _, bfcl_holdout = split_examples(bfcl_source, 0.2, args.bfcl_source_seed)
        bfcl_train, bfcl_validation = split_examples(bfcl_holdout, 0.33, args.meta_split_seed + 1)
        bfcl_pairs = [(item, bfcl_prompt(item), "train") for item in bfcl_train]
        bfcl_pairs += [(item, bfcl_prompt(item), "validation") for item in bfcl_validation]
        pairs = sft_pairs + bfcl_pairs
        examples = [item[0] for item in pairs]
        qwen_rows = [ClassificationRow(item[1], item[0].label, None) for item in pairs]
        labels = torch.tensor([item.label for item in examples], dtype=torch.long)
        train_indices = torch.tensor([index for index, item in enumerate(pairs) if item[2] == "train" and item[0].label < 3], dtype=torch.long)
        validation_indices = torch.tensor([index for index, item in enumerate(pairs) if item[2] == "validation"], dtype=torch.long)
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        jina_training.MAX_LENGTH = 4096
        args.output_dir.mkdir(parents=True, exist_ok=True)
        write_heartbeat(args.output_dir / "heartbeat.json", "encoder-scoring")
        encoder = encoder_logits(ENCODERS[2], examples, args, device).softmax(-1)
        model, tokenizer = load_model(QWEN_BASE, device, 16)
        if not hasattr(model, "load_adapter"):
            raise TypeError("The Qwen base did not produce a PEFT model.")
        model.load_adapter(QWEN, adapter_name="frozen")
        model.set_adapter("frozen")
        model.eval()
        qwen_scores = []
        with torch.inference_mode():
            for start in range(0, len(qwen_rows), args.batch_size):
                write_heartbeat(args.output_dir / "heartbeat.json", "qwen-scoring", start)
                qwen_scores.append(score_rows(model, tokenizer, qwen_rows[start:start + args.batch_size], label_token_ids(tokenizer), device, 4096).exp().cpu())
        qwen = torch.cat(qwen_scores)
        features = torch.cat((encoder, qwen), dim=-1).float()
        del model, tokenizer, qwen_scores
        if set(labels[train_indices].tolist()) != {0, 1, 2}:
            raise ValueError("The independent meta-training sources must contain all three benchmark action classes.")
        # Fit a small three-action classifier because the independent SFT source has no tool-call rows.
        torch.manual_seed(args.meta_split_seed)
        stacker = torch.nn.Linear(features.shape[-1], 3)
        optimizer = torch.optim.AdamW(stacker.parameters(), lr=args.learning_rate, weight_decay=args.weight_decay)
        train_x, train_y = features[train_indices], labels[train_indices]
        class_counts = torch.bincount(train_y, minlength=3).float()
        class_weights = (class_counts.mean() / class_counts).sqrt()
        for epoch in range(args.epochs):
            optimizer.zero_grad(set_to_none=True)
            loss = torch.nn.functional.cross_entropy(stacker(train_x), train_y, weight=class_weights)
            loss.backward()
            optimizer.step()
            if epoch % 20 == 0:
                write_heartbeat(args.output_dir / "heartbeat.json", "stacker-training", epoch)
        # Compare the fitted stacker with equal averaging on disjoint meta-training and validation partitions.
        with torch.inference_mode():
            validation_x = features[validation_indices]
            validation_y = labels[validation_indices]
            stacker_validation = stacker(validation_x)
            average_validation = ((encoder[validation_indices] + qwen[validation_indices]) / 2).clamp_min(1e-8).log()
            results = {
                "stacker_train": aggregate(train_y, stacker(train_x)),
                "average_train": aggregate(train_y, ((encoder[train_indices] + qwen[train_indices]) / 2).clamp_min(1e-8).log()),
                "stacker_validation": aggregate(validation_y, stacker_validation),
                "average_validation": aggregate(validation_y, average_validation),
            }
        for name, value in results.items():
            run.log({f"{name}/accuracy": value["accuracy"], f"{name}/macro_f1": value["macro_f1"]})
        # Store only frozen model coefficients, split sizes, and aggregate metrics.
        artifact = {
            "feature_order": ["encoder_probability_" + label for label in LABELS] + ["qwen_probability_" + label for label in LABELS],
            "class_order": LABELS[:3],
            "coefficients": stacker.weight.detach().tolist(),
            "intercepts": stacker.bias.detach().tolist(),
            "fit_sources": ["nvidia/When2Call train_sft holdout", "encoder-held-out BFCL call-only partition"],
            "holdout_seed": args.holdout_seed,
            "meta_split_seed": args.meta_split_seed,
            "bfcl_source_seed": args.bfcl_source_seed,
            "meta_training_examples": len(train_indices),
            "meta_validation_examples": len(validation_indices),
            "meta_training_source_counts": {"train_sft": len(sft_train), "bfcl": len(bfcl_train)},
            "meta_validation_source_counts": {"train_sft": len(sft_validation), "bfcl": len(bfcl_validation)},
            "training_configuration": {"epochs": args.epochs, "learning_rate": args.learning_rate, "weight_decay": args.weight_decay, "class_weights": class_weights.tolist()},
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
        print(json.dumps({"examples": {"meta_train": len(train_indices), "meta_validation": len(validation_indices)}, "metrics": results}, indent=2))
    except BaseException as error:
        run.summary.update({"status": "failed", "error": repr(error)})
        write_heartbeat(args.output_dir / "heartbeat.json", "failed")
        raise
    finally:
        run.finish()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
