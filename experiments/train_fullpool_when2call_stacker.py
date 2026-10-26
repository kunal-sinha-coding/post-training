"""Fit and evaluate a regularized encoder and Qwen probability fusion model.

The flow draws at most 500 examples from the clean When2Call SFT source, divides them into
disjoint meta-training and validation partitions, scores frozen Qwen and encoder checkpoints,
fits a small linear fusion layer, selects by clean validation accuracy, and saves aggregate
metrics plus frozen coefficients. It does not load the official test split.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import subprocess
import time
from pathlib import Path

import torch

from experiments.clean_validation_baseline import load_sft_training_rows, split_examples
from experiments.existing_when2call_hybrid import ENCODERS, QWEN_BASE, encoder_logits, hybrid_probabilities
from experiments.heterogeneous_when2call import artifact_digest
from experiments.train_qwen_when2call import ClassificationRow, label_token_ids, load_model, make_prompt, score_rows, write_heartbeat
from experiments.train_when2call_jina import LABELS, metric_values, prepare_train_examples
import experiments.train_when2call_jina as jina_training


QWEN_CHECKPOINT = "outputs/qwen-when2call-fullpool-base-seed20261055/epoch-02"


def metric_summary(labels: torch.Tensor, probabilities: torch.Tensor) -> dict:
    """Return accuracy and all-class macro F1 for one partition."""
    # Reduce predictions immediately so no row-level outcomes are written.
    result = metric_values(labels.tolist(), probabilities.argmax(-1).tolist(), list(range(len(LABELS))))
    return {key: result[key] for key in ("accuracy", "macro_f1")}


def sample_indices(examples: list, split_seed: int, sample_seed: int, limit: int) -> list[int]:
    """Draw a deterministic label-stratified sample from the clean SFT holdout."""
    # Keep the sample independent of the frozen encoder and Qwen training rows.
    _, development = split_examples(examples, 0.2, split_seed)
    groups = {label: [] for label in range(len(LABELS))}
    for item in development:
        groups[item.label].append(int(item.source_id))
    rng = random.Random(sample_seed)
    for indices in groups.values():
        rng.shuffle(indices)
    total = sum(len(indices) for indices in groups.values())
    quotas = {label: len(indices) * min(limit, total) / total for label, indices in groups.items()}
    counts = {label: min(len(groups[label]), int(quotas[label])) for label in groups}
    for label in sorted(groups, key=lambda key: quotas[key] - counts[key], reverse=True):
        if sum(counts.values()) >= min(limit, total):
            break
        if counts[label] < len(groups[label]):
            counts[label] += 1
    selected = [index for label in groups for index in groups[label][:counts[label]]]
    rng.shuffle(selected)
    return selected


def partition_indices(indices: list[int], examples: list, split_seed: int) -> tuple[list[int], list[int]]:
    """Split the capped sample into disjoint, stratified fit and validation sets."""
    # Divide each action class separately so both roles retain its available examples.
    groups = {label: [] for label in range(len(LABELS))}
    for index in indices:
        groups[examples[index].label].append(index)
    rng = random.Random(split_seed)
    fitting, validation = [], []
    for group in groups.values():
        rng.shuffle(group)
        midpoint = (len(group) + 1) // 2
        fitting.extend(group[:midpoint])
        validation.extend(group[midpoint:])
    rng.shuffle(fitting)
    rng.shuffle(validation)
    if not fitting or not validation:
        raise ValueError("The capped SFT sample must provide non-empty fit and validation sets.")
    return fitting, validation


def main() -> int:
    """Train the fusion layer on clean SFT data and save its validation-selected artifact."""
    # Freeze the data sample, optimization settings, and model artifacts before loading any rows.
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--split-seed", type=int, default=20261075)
    parser.add_argument("--sample-seed", type=int, default=20261076)
    parser.add_argument("--meta-split-seed", type=int, default=20261077)
    parser.add_argument("--max-examples", type=int, default=500)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--learning-rate", type=float, default=0.02)
    parser.add_argument("--weight-decay", type=float, default=0.1)
    parser.add_argument("--patience", type=int, default=10)
    args = parser.parse_args()
    # Enforce the evaluation sample cap before loading clean validation data.
    if args.max_examples < 2 or args.max_examples > 500:
        raise ValueError("The combined clean SFT sample must contain between 2 and 500 examples.")
    import wandb
    if not os.getenv("WANDB_API_KEY"):
        raise RuntimeError("WANDB_API_KEY is required for this validation experiment.")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    run = wandb.init(
        project=os.getenv("WANDB_PROJECT", "when2call-research"),
        entity=os.getenv("WANDB_ENTITY"),
        name="fullpool-qwen-encoder-regularized-stacker-validation",
        job_type="clean-validation",
        config={"encoder": ENCODERS[2], "qwen_checkpoint": QWEN_CHECKPOINT, "qwen_base": QWEN_BASE, "source": "nvidia/When2Call train_sft", "split_seed": args.split_seed, "sample_seed": args.sample_seed, "meta_split_seed": args.meta_split_seed, "max_examples": args.max_examples, "epochs": args.epochs, "learning_rate": args.learning_rate, "weight_decay": args.weight_decay, "patience": args.patience, "official_test_loaded": False},
    )
    started = time.time()
    try:
        # Build the deterministic sample and keep the fit and validation indices disjoint.
        sft_rows = list(load_sft_training_rows())
        examples = prepare_train_examples(sft_rows)
        sampled = sample_indices(examples, args.split_seed, args.sample_seed, args.max_examples)
        fitting, validation = partition_indices(sampled, examples, args.meta_split_seed)
        all_indices = fitting + validation
        qwen_rows = [ClassificationRow(make_prompt(sft_rows[index]), examples[index].label, None) for index in all_indices]
        labels = torch.tensor([examples[index].label for index in all_indices], dtype=torch.long)
        fit_positions = torch.arange(len(fitting))
        validation_positions = torch.arange(len(fitting), len(all_indices))
        # Score both frozen members once on the same capped clean sample.
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        jina_training.MAX_LENGTH = 4096
        write_heartbeat(args.output_dir / "heartbeat.json", "encoder-scoring")
        encoder = encoder_logits(ENCODERS[2], [examples[index] for index in all_indices], args, device).softmax(-1)
        model, tokenizer = load_model(QWEN_BASE, device, 16)
        if not hasattr(model, "load_adapter"):
            raise TypeError("The Qwen base did not produce a PEFT model.")
        model.load_adapter(QWEN_CHECKPOINT, adapter_name="frozen")
        model.set_adapter("frozen")
        model.eval()
        qwen_scores = []
        with torch.inference_mode():
            for start in range(0, len(qwen_rows), args.batch_size):
                write_heartbeat(args.output_dir / "heartbeat.json", "qwen-scoring", start)
                batch = qwen_rows[start:start + args.batch_size]
                qwen_scores.append(score_rows(model, tokenizer, batch, label_token_ids(tokenizer), device, 4096).exp().cpu())
        qwen = torch.cat(qwen_scores)
        del model, tokenizer, qwen_scores
        # Fit a small regularized classifier over the two probability vectors.
        features = torch.cat((encoder, qwen), dim=-1).float()
        torch.manual_seed(args.meta_split_seed)
        stacker = torch.nn.Linear(features.shape[-1], len(LABELS))
        optimizer = torch.optim.AdamW(stacker.parameters(), lr=args.learning_rate, weight_decay=args.weight_decay)
        fit_x, fit_y = features[fit_positions], labels[fit_positions]
        validation_x, validation_y = features[validation_positions], labels[validation_positions]
        best_accuracy = -1.0
        best_epoch = 0
        best_state = None
        stale_epochs = 0
        history = []
        for epoch in range(1, args.epochs + 1):
            # Apply one deterministic full-batch optimizer update and record its loss.
            stacker.train()
            optimizer.zero_grad(set_to_none=True)
            loss = torch.nn.functional.cross_entropy(stacker(fit_x), fit_y)
            loss.backward()
            optimizer.step()
            # Use only the clean validation partition to choose the fusion checkpoint.
            stacker.eval()
            with torch.inference_mode():
                validation_probs = stacker(validation_x).softmax(-1)
                validation_metrics = metric_summary(validation_y, validation_probs)
                fit_metrics = metric_summary(fit_y, stacker(fit_x).softmax(-1))
            history.append({"epoch": epoch, "training_loss": float(loss.item()), "training_metrics": fit_metrics, "validation_metrics": validation_metrics})
            run.log({"epoch": epoch, "training/loss": float(loss.item()), "training/accuracy": fit_metrics["accuracy"], "training/macro_f1": fit_metrics["macro_f1"], "validation/accuracy": validation_metrics["accuracy"], "validation/macro_f1": validation_metrics["macro_f1"]})
            write_heartbeat(args.output_dir / "heartbeat.json", "stacker-training", epoch)
            if validation_metrics["accuracy"] > best_accuracy:
                best_accuracy = validation_metrics["accuracy"]
                best_epoch = epoch
                best_state = {key: value.detach().cpu().clone() for key, value in stacker.state_dict().items()}
                stale_epochs = 0
            else:
                stale_epochs += 1
            if stale_epochs >= args.patience:
                break
        if best_state is None:
            raise RuntimeError("No validation-selected fusion checkpoint was produced.")
        # Restore the highest validation-accuracy fusion checkpoint and compare it with frozen baselines.
        stacker.load_state_dict(best_state)
        stacker.eval()
        with torch.inference_mode():
            stacker_train = metric_summary(fit_y, stacker(fit_x).softmax(-1))
            stacker_validation = metric_summary(validation_y, stacker(validation_x).softmax(-1))
        average_validation = metric_summary(validation_y, (encoder[validation_positions] + qwen[validation_positions]) / 2)
        request60_validation = metric_summary(validation_y, hybrid_probabilities(encoder[validation_positions], qwen[validation_positions], "request_conf_60"))
        qwen_validation = metric_summary(validation_y, qwen[validation_positions])
        encoder_validation = metric_summary(validation_y, encoder[validation_positions])
        # Save only model coefficients, sample fingerprints, and aggregate metrics.
        artifact = {"feature_order": ["encoder_probability_" + label for label in LABELS] + ["qwen_probability_" + label for label in LABELS], "class_order": LABELS, "coefficients": stacker.weight.detach().cpu().tolist(), "intercepts": stacker.bias.detach().cpu().tolist(), "l2": args.weight_decay, "fit_examples": len(fitting), "validation_examples": len(validation), "fit_indices_sha256": hashlib.sha256(",".join(map(str, fitting)).encode()).hexdigest(), "validation_indices_sha256": hashlib.sha256(",".join(map(str, validation)).encode()).hexdigest(), "base_qwen_checkpoint": QWEN_CHECKPOINT, "encoder_checkpoint": ENCODERS[2], "selection_metric": "clean validation accuracy", "selected_epoch": best_epoch, "official_test_loaded": False}
        artifact["git_commit"] = subprocess.check_output(["git", "-c", "safe.directory=/workspace/post-training", "rev-parse", "HEAD"], text=True).strip()
        artifact["artifact_sha256"] = {str(path): artifact_digest(path) for path in (Path(ENCODERS[2]) / "model_state.pt", Path(ENCODERS[2]) / "encoder_config.json", Path(QWEN_CHECKPOINT) / "adapter_model.safetensors", Path(QWEN_CHECKPOINT) / "adapter_config.json")}
        artifact["wandb_run_id"] = run.id
        artifact["wandb_run_url"] = run.url
        artifact_path = args.output_dir / "stacker.json"
        artifact_path.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
        result = {"status": "completed", "official_test_loaded": False, "training_metrics": stacker_train, "heldout_validation_metrics": stacker_validation, "baseline_validation_metrics": {"qwen_sft": qwen_validation, "encoder_single": encoder_validation, "single_average": average_validation, "single_request_conf_60": request60_validation}, "training_examples": len(fitting), "validation_examples": len(validation), "sampled_examples": len(sampled), "selected_epoch": best_epoch, "history": history, "stacker_artifact": str(artifact_path), "stacker_artifact_sha256": artifact_digest(artifact_path), "runtime_seconds": time.time() - started, "git_commit": artifact["git_commit"], "wandb_run_id": run.id, "wandb_run_url": run.url}
        (args.output_dir / "metrics.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        run.summary.update({"status": "completed", "training_accuracy": stacker_train["accuracy"], "validation_accuracy": stacker_validation["accuracy"], "output_dir": str(args.output_dir)})
        write_heartbeat(args.output_dir / "heartbeat.json", "completed")
        print(json.dumps({"training": stacker_train, "validation": stacker_validation, "baselines": result["baseline_validation_metrics"], "selected_epoch": best_epoch}, indent=2))
    except BaseException as error:
        run.summary.update({"status": "failed", "error": repr(error)})
        write_heartbeat(args.output_dir / "heartbeat.json", "failed")
        raise
    finally:
        run.finish()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
