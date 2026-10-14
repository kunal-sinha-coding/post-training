# This script trains MiniLM on the selected MBPP router dataset and evaluates both training and EvalPlus data.
# It uses the saved one-greedy-attempt labels and a binary CLS classification head.
# It reports retrieval metrics at a configurable optimizer-step interval.
# It selects a checkpoint on a grouped validation split and uses EvalPlus only for final measurement.
# It can freeze MiniLM and cache its deterministic CLS features to train only the linear head.
# It logs ranking areas and retrieval metrics at thresholds from 0.1 through 0.9.

from __future__ import annotations

import argparse
import json
import random
import re
import time
from pathlib import Path
from typing import Any

import torch
from transformers import AutoModel, AutoTokenizer


# Calculate binary retrieval metrics with label one as the retrieved positive class.
def binary_metrics(labels: list[int], predictions: list[int]) -> dict[str, Any]:
    # Count true positive, false positive, true negative, and false negative predictions.
    tp = sum(label == 1 and prediction == 1 for label, prediction in zip(labels, predictions, strict=True))
    fp = sum(label == 0 and prediction == 1 for label, prediction in zip(labels, predictions, strict=True))
    tn = sum(label == 0 and prediction == 0 for label, prediction in zip(labels, predictions, strict=True))
    fn = sum(label == 1 and prediction == 0 for label, prediction in zip(labels, predictions, strict=True))
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if precision + recall else 0.0
    return {
        "accuracy": (tp + tn) / len(labels) if labels else 0.0,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "true_positive": tp,
        "false_positive": fp,
        "true_negative": tn,
        "false_negative": fn,
    }


# Tokenize all prompts once and keep tensors on the host until each batch is evaluated.
def ranking_metrics(labels: list[int], probabilities: list[float]) -> dict[str, Any]:
    # Integrate precision and recall at distinct scores so tied predictions remain one group.
    ordered = sorted(zip(probabilities, labels, strict=True), reverse=True)
    positives = sum(labels)
    negatives = len(labels) - positives
    tp = fp = 0
    previous_recall = previous_fpr = 0.0
    previous_precision = 1.0
    average_precision = pr_area = roc_area = 0.0
    index = 0
    while index < len(ordered):
        score = ordered[index][0]
        while index < len(ordered) and ordered[index][0] == score:
            label = ordered[index][1]
            tp += label
            fp += 1 - label
            index += 1
        precision = tp / (tp + fp)
        recall = tp / positives if positives else 0.0
        fpr = fp / negatives if negatives else 0.0
        average_precision += (recall - previous_recall) * precision
        pr_area += (recall - previous_recall) * (precision + previous_precision) / 2
        roc_area += (fpr - previous_fpr) * (recall + previous_recall) / 2
        previous_recall, previous_fpr, previous_precision = recall, fpr, precision
    return {"auprc": average_precision, "average_precision": average_precision, "pr_auc_trapezoidal": pr_area, "roc_auc": roc_area if positives and negatives else None, "positive_prevalence": positives / len(labels) if labels else 0.0}


# Measure retrieval at each requested probability threshold.
def threshold_metrics(labels: list[int], probabilities: list[float]) -> dict[str, Any]:
    # Apply the positive decision rule at thresholds from 0.1 through 0.9.
    result = {}
    for value in range(1, 10):
        threshold = value / 10
        predictions = [int(probability >= threshold) for probability in probabilities]
        result[f"threshold_{threshold:.1f}"] = {**binary_metrics(labels, predictions), "positive_prediction_fraction": sum(predictions) / len(predictions)}
    return result


# Split normalized task-text groups into fixed stratified training and validation folds.
def split_rows(rows: list[dict[str, Any]], validation_fraction: float, seed: int) -> tuple[list[int], list[int]]:
    # Keep duplicate task descriptions together so they cannot leak across the split.
    groups: dict[tuple[int, str], list[int]] = {}
    for index, row in enumerate(rows):
        normalized = re.sub(r"\s+", " ", str(row.get("task_text", row["prompt"]))).strip().casefold()
        groups.setdefault((int(row["label_mbpp"]), normalized), []).append(index)
    randomizer = random.Random(seed)
    validation_indexes: set[int] = set()
    # Select a deterministic fraction of each class while retaining whole text groups.
    for label in (0, 1):
        class_groups = [indexes for (group_label, _), indexes in groups.items() if group_label == label]
        randomizer.shuffle(class_groups)
        target = round(sum(len(indexes) for indexes in class_groups) * validation_fraction)
        selected = 0
        for indexes in class_groups:
            if selected >= target:
                break
            validation_indexes.update(indexes)
            selected += len(indexes)
    train_indexes = [index for index in range(len(rows)) if index not in validation_indexes]
    return train_indexes, sorted(validation_indexes)


# Tokenize task prompts and read the requested binary target.
def encode_rows(tokenizer: Any, rows: list[dict[str, Any]], max_length: int, label_key: str = "label") -> tuple[dict[str, torch.Tensor], list[int]]:
    # Apply the same maximum input length to every task and read the requested binary target.
    encoded = tokenizer(
        [row["prompt"] for row in rows],
        padding=True,
        truncation=True,
        max_length=max_length,
        return_tensors="pt",
    )
    labels = [int(row[label_key]) for row in rows]
    return dict(encoded), labels


# Predict labels and positive probabilities in bounded batches without dropout.
def encoder_features(encoder: Any, encoded: dict[str, torch.Tensor], device: torch.device, batch_size: int) -> torch.Tensor:
    # Cache deterministic CLS features without building encoder gradients.
    encoder.eval()
    features = []
    with torch.no_grad():
        for start in range(0, len(encoded["input_ids"]), batch_size):
            batch = {key: value[start:start + batch_size].to(device) for key, value in encoded.items()}
            features.append(encoder(**batch).last_hidden_state[:, 0].cpu())
    return torch.cat(features)


# Predict labels using encoder outputs or previously cached frozen features.
def predict_rows(
    encoder: Any,
    head: torch.nn.Module,
    dropout: torch.nn.Module,
    encoded: dict[str, torch.Tensor],
    labels: list[int],
    device: torch.device,
    batch_size: int,
    cached_features: torch.Tensor | None = None,
) -> tuple[dict[str, Any], list[int], list[float]]:
    # Run batched inference, then calculate the four retrieval metrics from argmax labels.
    encoder.eval()
    head.eval()
    dropout.eval()
    predictions: list[int] = []
    probabilities: list[float] = []
    with torch.no_grad():
        for start in range(0, len(labels), batch_size):
            # Reuse fixed features when the encoder is frozen.
            if cached_features is not None:
                features = cached_features[start:start + batch_size].to(device)
            else:
                batch = {key: value[start:start + batch_size].to(device) for key, value in encoded.items()}
                features = encoder(**batch).last_hidden_state[:, 0]
            logits = head(dropout(features))
            positive_probability = logits.softmax(dim=-1)[:, 1]
            probabilities.extend(float(value) for value in positive_probability.cpu())
            predictions.extend(int(value) for value in logits.argmax(dim=-1).cpu())
    return binary_metrics(labels, predictions), predictions, probabilities


# Measure mean cross entropy over a dataset with the same deterministic inference path as evaluation.
def dataset_loss(encoder: Any, head: torch.nn.Module, dropout: torch.nn.Module, encoded: dict[str, torch.Tensor], labels: list[int], device: torch.device, batch_size: int, cached_features: torch.Tensor | None = None) -> float:
    # Compute loss in bounded batches without retaining gradients.
    encoder.eval()
    head.eval()
    dropout.eval()
    losses = []
    loss_function = torch.nn.CrossEntropyLoss(reduction="sum")
    with torch.no_grad():
        for start in range(0, len(labels), batch_size):
            # Use cached CLS values only for the frozen encoder baseline.
            if cached_features is not None:
                features = cached_features[start:start + batch_size].to(device)
            else:
                batch = {key: value[start:start + batch_size].to(device) for key, value in encoded.items()}
                features = encoder(**batch).last_hidden_state[:, 0]
            batch_labels = torch.tensor(labels[start:start + batch_size], dtype=torch.long, device=device)
            losses.append(float(loss_function(head(dropout(features)), batch_labels).cpu()))
    return sum(losses) / len(labels) if labels else 0.0


# Train the requested encoder and head parameters and evaluate both label sets at fixed intervals.
def main() -> None:
    # Parse paths, training settings, and the W&B project for this full-data router run.
    parser = argparse.ArgumentParser()
    parser.add_argument("--train-data", type=Path, default=Path("outputs/router-mbpp-easy-one-shot-20261013/router_dataset.jsonl"))
    parser.add_argument("--eval-data", type=Path, default=Path("outputs/router-evalplus-greedy-dual-label-20261013/router_evalplus_labels.jsonl"))
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/router-minilm-easy-dual-eval-20261013"))
    parser.add_argument("--model", default="microsoft/MiniLM-L12-H384-uncased")
    parser.add_argument("--freeze-encoder", action="store_true", help="Train only the linear head on cached pretrained CLS features.")
    parser.add_argument("--unfreeze-last-layer", action="store_true", help="Train MiniLM's final transformer layer and the classification head.")
    parser.add_argument("--validation-fraction", type=float, default=0.2)
    parser.add_argument("--encoder-learning-rate", type=float, default=5e-6)
    parser.add_argument("--early-stopping-patience", type=int, default=5)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--epochs", type=int, default=5)
    parser.add_argument("--max-steps", type=int)
    parser.add_argument("--run-name", default="router-minilm-original-only-1m-20261013")
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--eval-batch-size", type=int, default=32)
    parser.add_argument("--eval-every-steps", type=int, default=10)
    parser.add_argument("--max-length", type=int, default=512)
    parser.add_argument("--learning-rate", type=float, default=5e-5)
    parser.add_argument("--wandb-project", default="grpo-mbpp")
    parser.add_argument("--wandb-entity", default="kunal-personal")
    args = parser.parse_args()
    if args.freeze_encoder and args.unfreeze_last_layer:
        parser.error("Choose either --freeze-encoder or --unfreeze-last-layer.")
    if not 0 < args.validation_fraction < 1:
        parser.error("The validation fraction must be between zero and one.")

    # Set all random seeds before shuffling training examples and initializing the classifier head.
    random.seed(args.seed)
    torch.manual_seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)

    # Load the original training labels and canonical EvalPlus rows and validate their targets.
    train_rows = [json.loads(line) for line in args.train_data.read_text(encoding="utf-8").splitlines() if line.strip()]
    eval_rows = [json.loads(line) for line in args.eval_data.read_text(encoding="utf-8").splitlines() if line.strip()]
    train_labels = [int(row["label_mbpp"]) for row in train_rows]
    eval_mbpp_labels = [int(row["label_mbpp"]) for row in eval_rows]
    eval_mbpp_plus_labels = [int(row["label_mbpp_plus"]) for row in eval_rows]
    if any(label not in (0, 1) for label in train_labels + eval_mbpp_labels + eval_mbpp_plus_labels):
        raise ValueError("Every MBPP and MBPP+ router label must be zero or one.")

    # Make one fixed grouped stratified split before tokenizing the data.
    train_indexes, validation_indexes = split_rows(train_rows, args.validation_fraction, args.seed)
    source_train_rows = train_rows
    train_rows = [source_train_rows[index] for index in train_indexes]
    validation_rows = [source_train_rows[index] for index in validation_indexes]
    # Load MiniLM, initialize the CLS classification head, and tokenize all selected rows.
    tokenizer = AutoTokenizer.from_pretrained(args.model)
    encoder = AutoModel.from_pretrained(args.model)
    train_encoded, train_labels = encode_rows(tokenizer, train_rows, args.max_length, "label_mbpp")
    validation_encoded, validation_labels = encode_rows(tokenizer, validation_rows, args.max_length, "label_mbpp")
    eval_encoded, _ = encode_rows(tokenizer, eval_rows, args.max_length, "label_mbpp")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    encoder.to(device)
    dropout = torch.nn.Dropout(0.1).to(device)
    head = torch.nn.Linear(int(encoder.config.hidden_size), 2).to(device)
    # Freeze all encoder weights, then optionally enable only the final transformer layer.
    train_features = validation_features = eval_features = None
    if args.freeze_encoder or args.unfreeze_last_layer:
        encoder.requires_grad_(False)
    if args.unfreeze_last_layer:
        encoder.encoder.layer[-1].requires_grad_(True)
    if args.freeze_encoder:
        encoder.eval()
        train_features = encoder_features(encoder, train_encoded, device, args.eval_batch_size)
        validation_features = encoder_features(encoder, validation_encoded, device, args.eval_batch_size)
        eval_features = encoder_features(encoder, eval_encoded, device, args.eval_batch_size)
    # Use separate learning rates so the pretrained encoder receives smaller updates.
    if args.unfreeze_last_layer:
        optimizer = torch.optim.AdamW([
            {"params": encoder.encoder.layer[-1].parameters(), "lr": args.encoder_learning_rate},
            {"params": head.parameters(), "lr": args.learning_rate},
        ])
    else:
        parameters = list(head.parameters()) if args.freeze_encoder else list(encoder.parameters()) + list(head.parameters())
        optimizer = torch.optim.AdamW(parameters, lr=args.learning_rate)
    loss_function = torch.nn.CrossEntropyLoss()

    # Create the W&B run before training and track all configuration and source artifacts.
    import wandb

    eval_summary = json.loads((args.eval_data.parent / "summary.json").read_text(encoding="utf-8"))
    run = wandb.init(
        entity=args.wandb_entity,
        project=args.wandb_project,
        name=args.run_name,
        job_type="router-full-training",
        config={
            "train_data": str(args.train_data),
            "eval_data": str(args.eval_data),
            "output_dir": str(args.output_dir),
            "seed": args.seed,
            "epochs": args.epochs,
            "max_steps": args.max_steps,
            "batch_size": args.batch_size,
            "eval_batch_size": args.eval_batch_size,
            "eval_every_steps": args.eval_every_steps,
            "max_length": args.max_length,
            "learning_rate": args.learning_rate,
            "encoder_learning_rate": args.encoder_learning_rate,
            "validation_fraction": args.validation_fraction,
            "early_stopping_patience": args.early_stopping_patience,
            "wandb_project": args.wandb_project,
            "wandb_entity": args.wandb_entity,
            "model": args.model,
            "freeze_encoder": args.freeze_encoder,
            "unfreeze_last_layer": args.unfreeze_last_layer,
            "encoder_trainable_parameters": sum(parameter.numel() for parameter in encoder.parameters() if parameter.requires_grad),
            "head_trainable_parameters": sum(parameter.numel() for parameter in head.parameters()),
            "head_architecture": f"Dropout(0.1) then Linear({encoder.config.hidden_size}, 2)",
            "positive_class": 1,
            "metric_prediction_rule": "argmax over two logits",
            "thresholds": [value / 10 for value in range(1, 10)],
            "auprc_definition": "average precision with exact score ties grouped",
            "train_target": "passes every available MBPP-style task assertion on one greedy completion",
            "eval_targets": ["passes all MBPP base tests", "passes all MBPP+ base and extra tests"],
            "source_train_task_count": len(source_train_rows),
            "train_task_count": len(train_rows),
            "train_label_counts": {"positive": sum(train_labels), "negative": len(train_labels) - sum(train_labels)},
            "validation_task_count": len(validation_rows),
            "validation_label_counts": {"positive": sum(validation_labels), "negative": len(validation_labels) - sum(validation_labels)},
            "eval_task_count": len(eval_rows),
            "eval_label_counts": {"solved": eval_summary["plus_solved"], "unsolved": eval_summary["plus_unsolved"]},
            "eval_base_label_counts": {"solved": eval_summary["base_solved"], "unsolved": eval_summary["base_unsolved"]},
            "evaluation_cadence": args.eval_every_steps,
            "logging_mode": "live during training",
        },
    )
    run.define_metric("optimizer_step")
    run.define_metric("train/*", step_metric="optimizer_step")
    run.define_metric("validation/*", step_metric="optimizer_step")
    run.define_metric("evalplus_mbpp/*", step_metric="optimizer_step")
    run.define_metric("evalplus_mbpp_plus/*", step_metric="optimizer_step")
    train_artifact = wandb.Artifact("router-mbpp-original-only-one-shot-labels-20261013", type="dataset")
    train_artifact.add_file(str(args.train_data))
    train_artifact.add_file(str(args.train_data.parent / "completions.json"))
    run.log_artifact(train_artifact)
    eval_artifact = wandb.Artifact("router-evalplus-dual-labels-20261013", type="dataset")
    eval_artifact.add_file(str(args.eval_data))
    eval_artifact.add_file(str(args.eval_data.parent / "summary.json"))
    run.log_artifact(eval_artifact)

    # Evaluate an initial untrained baseline so later retrieval metrics have a clear reference.
    args.output_dir.mkdir(parents=True, exist_ok=True)
    metrics_path = args.output_dir / "evaluation_history.jsonl"
    predictions_path = args.output_dir / "predictions.jsonl"
    history: list[dict[str, Any]] = []
    metrics_path.unlink(missing_ok=True)
    predictions_path.unlink(missing_ok=True)

    # Measure training and validation metrics, and optionally the final EvalPlus benchmark.
    def evaluate_and_log(step: int, include_evalplus: bool = False) -> dict[str, Any]:
        # Compute metrics and cross entropy for the training and validation folds.
        train_metrics, train_predictions, train_probabilities = predict_rows(
            encoder, head, dropout, train_encoded, train_labels, device, args.eval_batch_size, train_features
        )
        validation_metrics, validation_predictions, validation_probabilities = predict_rows(
            encoder, head, dropout, validation_encoded, validation_labels, device, args.eval_batch_size, validation_features
        )
        # Calculate ranking areas and threshold sweeps separately for both training folds.
        threshold_results = {}
        for name, metrics, labels, probabilities in [
            ("training", train_metrics, train_labels, train_probabilities),
            ("validation", validation_metrics, validation_labels, validation_probabilities),
        ]:
            metrics.update(ranking_metrics(labels, probabilities))
            threshold_results[name] = threshold_metrics(labels, probabilities)
        record = {
            "optimizer_step": step,
            "training": train_metrics,
            "validation": validation_metrics,
            "threshold_metrics": threshold_results,
        }
        record["training"]["loss"] = dataset_loss(encoder, head, dropout, train_encoded, train_labels, device, args.eval_batch_size, train_features)
        record["validation"]["loss"] = dataset_loss(encoder, head, dropout, validation_encoded, validation_labels, device, args.eval_batch_size, validation_features)
        # Evaluate EvalPlus only at the selected checkpoint after training is complete.
        if include_evalplus:
            eval_mbpp_metrics, eval_predictions, eval_probabilities = predict_rows(
                encoder, head, dropout, eval_encoded, eval_mbpp_labels, device, args.eval_batch_size, eval_features
            )
            eval_mbpp_plus_metrics = binary_metrics(eval_mbpp_plus_labels, eval_predictions)
            for metrics, labels in ((eval_mbpp_metrics, eval_mbpp_labels), (eval_mbpp_plus_metrics, eval_mbpp_plus_labels)):
                metrics.update(ranking_metrics(labels, eval_probabilities))
            record["evalplus_mbpp"] = eval_mbpp_metrics
            record["evalplus_mbpp_plus"] = eval_mbpp_plus_metrics
            threshold_results["evalplus_mbpp"] = threshold_metrics(eval_mbpp_labels, eval_probabilities)
            threshold_results["evalplus_mbpp_plus"] = threshold_metrics(eval_mbpp_plus_labels, eval_probabilities)
        history.append(record)
        with metrics_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record) + "\n")
        prediction_sets = [
            ("training", train_rows, train_labels, train_predictions, train_probabilities),
            ("validation", validation_rows, validation_labels, validation_predictions, validation_probabilities),
        ]
        if include_evalplus:
            prediction_sets.append(("evalplus", eval_rows, eval_mbpp_labels, eval_predictions, eval_probabilities))
        with predictions_path.open("w", encoding="utf-8") as handle:
            for split, rows, labels, predictions, probabilities in prediction_sets:
                for row, label, prediction, probability in zip(rows, labels, predictions, probabilities, strict=True):
                    handle.write(json.dumps({
                        "optimizer_step": step,
                        "split": split,
                        "task_id": str(row["task_id"]),
                        "label_mbpp": label,
                        "label_mbpp_plus": row.get("label_mbpp_plus"),
                        "prediction": prediction,
                        "positive_probability": probability,
                    }) + "\n")
        payload = {"optimizer_step": step}
        payload.update({f"train/{key}": value for key, value in train_metrics.items()})
        payload.update({f"validation/{key}": value for key, value in validation_metrics.items()})
        if include_evalplus:
            payload.update({f"evalplus_mbpp/{key}": value for key, value in eval_mbpp_metrics.items()})
            payload.update({f"evalplus_mbpp_plus/{key}": value for key, value in eval_mbpp_plus_metrics.items()})
        # Publish every threshold as its own metric series indexed by optimizer step.
        for name, thresholds in threshold_results.items():
            prefix = "train" if name == "training" else name
            for threshold_name, metrics in thresholds.items():
                payload.update({f"{prefix}/{threshold_name}/{key}": value for key, value in metrics.items()})
        run.log(payload, step=step)
        print(json.dumps(record), flush=True)
        return record

    # Report the untrained baseline before the first optimizer update.
    initial_record = evaluate_and_log(0)

    # Shuffle the labeled training set until the configured update budget or early stop.
    global_step = 0
    # Use an exact update budget when supplied, or derive the legacy budget from epochs.
    target_steps = args.max_steps if args.max_steps is not None else args.epochs * ((len(train_rows) + args.batch_size - 1) // args.batch_size)
    if target_steps <= 0:
        parser.error("The training budget must be greater than zero.")
    started = time.time()
    labels_tensor = torch.tensor(train_labels, dtype=torch.long)
    loss_history_path = args.output_dir / "training_loss.jsonl"
    loss_history_path.unlink(missing_ok=True)
    best_validation_ap = float(initial_record["validation"]["average_precision"])
    best_step = 0
    stale_evaluations = 0
    # Keep the initial checkpoint in case validation AP never improves.
    torch.save(encoder.state_dict(), args.output_dir / "best_encoder_state.pt")
    torch.save(head.state_dict(), args.output_dir / "best_classification_head.pt")
    while global_step < target_steps and stale_evaluations < args.early_stopping_patience:
        # Shuffle one new pass through the selected training tasks.
        order = torch.randperm(len(train_rows))
        for start in range(0, len(train_rows), args.batch_size):
            # Stop at the exact optimizer-step budget, including a partial final epoch.
            if global_step >= target_steps:
                break
            indexes = order[start:start + args.batch_size]
            batch = {key: value[indexes].to(device) for key, value in train_encoded.items()}
            batch_labels = labels_tensor[indexes].to(device)
            encoder.train(not args.freeze_encoder)
            head.train()
            dropout.train()
            optimizer.zero_grad(set_to_none=True)
            # Reuse cached features only when every encoder weight is frozen.
            features = train_features[indexes].to(device) if train_features is not None else encoder(**batch).last_hidden_state[:, 0]
            logits = head(dropout(features))
            loss = loss_function(logits, batch_labels)
            loss.backward()
            optimizer.step()
            global_step += 1
            loss_value = float(loss.detach().cpu())
            with loss_history_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps({"optimizer_step": global_step, "loss": loss_value}) + "\n")
            run.log({"train/loss": loss_value}, step=global_step)
            if global_step == 100:
                # Save one durable model checkpoint after the first 100 optimizer updates.
                checkpoint_dir = args.output_dir / "checkpoint-100" / "encoder"
                encoder.save_pretrained(checkpoint_dir, safe_serialization=True)
                tokenizer.save_pretrained(checkpoint_dir)
                torch.save(head.state_dict(), args.output_dir / "checkpoint-100" / "classification_head.pt")
            if global_step % args.eval_every_steps == 0:
                current_record = evaluate_and_log(global_step)
                current_ap = float(current_record["validation"]["average_precision"])
                if current_ap > best_validation_ap:
                    # Save the checkpoint that has the best validation average precision.
                    best_validation_ap = current_ap
                    best_step = global_step
                    stale_evaluations = 0
                    torch.save(encoder.state_dict(), args.output_dir / "best_encoder_state.pt")
                    torch.save(head.state_dict(), args.output_dir / "best_classification_head.pt")
                else:
                    stale_evaluations += 1
                if stale_evaluations >= args.early_stopping_patience:
                    print(json.dumps({"early_stopping_step": global_step, "best_step": best_step, "best_validation_average_precision": best_validation_ap}), flush=True)
                    break

    # Restore the validation-selected weights before measuring EvalPlus once.
    encoder.load_state_dict(torch.load(args.output_dir / "best_encoder_state.pt", map_location=device, weights_only=True))
    head.load_state_dict(torch.load(args.output_dir / "best_classification_head.pt", map_location=device, weights_only=True))
    final_record = evaluate_and_log(global_step, include_evalplus=True)

    # Save the final encoder, classification head, metrics, and complete run configuration.
    encoder.eval()
    head.eval()
    encoder_dir = args.output_dir / "encoder"
    encoder.save_pretrained(encoder_dir, safe_serialization=True)
    tokenizer.save_pretrained(encoder_dir)
    torch.save(head.state_dict(), args.output_dir / "classification_head.pt")
    metadata = {
        "experiment": "MiniLM router capacity comparison with grouped training validation and separate MBPP and MBPP+ retrieval evaluation",
        "model": args.model,
        "architecture": {
            "encoder": "frozen pretrained MiniLM" if args.freeze_encoder else ("pretrained MiniLM with final transformer layer fine-tuned" if args.unfreeze_last_layer else "fully fine-tuned MiniLM"),
            "pooling": "last hidden state at CLS position",
            "head": f"Dropout(0.1) then Linear({encoder.config.hidden_size}, 2)",
            "encoder_parameters": sum(parameter.numel() for parameter in encoder.parameters()),
            "head_parameters": sum(parameter.numel() for parameter in head.parameters()),
        },
        "train_data": str(args.train_data),
        "eval_data": str(args.eval_data),
            "source_train_task_count": len(source_train_rows),
            "train_task_count": len(train_rows),
            "validation_task_count": len(validation_rows),
        "eval_task_count": len(eval_rows),
        "configuration": {
            "seed": args.seed,
            "epochs": args.epochs,
            "max_steps": args.max_steps,
            "batch_size": args.batch_size,
            "eval_batch_size": args.eval_batch_size,
            "eval_every_steps": args.eval_every_steps,
            "max_length": args.max_length,
            "learning_rate": args.learning_rate,
            "encoder_learning_rate": args.encoder_learning_rate,
            "validation_fraction": args.validation_fraction,
            "early_stopping_patience": args.early_stopping_patience,
            "optimizer": "AdamW",
            "loss": "cross entropy",
            "device": str(device),
        },
        "optimizer_steps": global_step,
        "elapsed_seconds": time.time() - started,
        "best_validation_step": best_step,
        "best_validation_average_precision": best_validation_ap,
        "final_metrics": final_record,
        "evaluation_history": str(metrics_path),
        "predictions": str(predictions_path),
        "training_loss": str(loss_history_path),
    }
    metadata_path = args.output_dir / "experiment.json"
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    model_artifact = wandb.Artifact(f"minilm-router-original-only-{args.run_name}", type="model")
    model_artifact.add_dir(str(args.output_dir))
    run.log_artifact(model_artifact)
    run.summary["optimizer_steps"] = global_step
    run.summary["best_validation_step"] = best_step
    run.summary["best_validation_average_precision"] = best_validation_ap
    run.summary["final_train_metrics"] = final_record["training"]
    run.summary["final_validation_metrics"] = final_record["validation"]
    run.summary["final_evalplus_mbpp_metrics"] = final_record["evalplus_mbpp"]
    run.summary["final_evalplus_mbpp_plus_metrics"] = final_record["evalplus_mbpp_plus"]
    run.summary["elapsed_seconds"] = metadata["elapsed_seconds"]
    run_url = run.url
    run.finish()
    print(json.dumps({"wandb_url": run_url, "output_dir": str(args.output_dir), "final_metrics": history[-1]}, indent=2), flush=True)


if __name__ == "__main__":
    # Start full-data router training with live W&B metrics.
    main()
