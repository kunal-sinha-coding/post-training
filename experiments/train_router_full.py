# This script trains MiniLM on the full filtered MBPP router dataset and evaluates both train and EvalPlus data.
# It uses the saved one-greedy-attempt labels and a binary CLS classification head.
# It reports accuracy, positive-class precision, recall, and F1 every ten optimizer updates.
# It saves the final checkpoint, per-task predictions, metric history, and W&B artifacts.

from __future__ import annotations

import argparse
import json
import random
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
def predict_rows(
    encoder: Any,
    head: torch.nn.Module,
    dropout: torch.nn.Module,
    encoded: dict[str, torch.Tensor],
    labels: list[int],
    device: torch.device,
    batch_size: int,
) -> tuple[dict[str, Any], list[int], list[float]]:
    # Run batched inference, then calculate the four retrieval metrics from argmax labels.
    encoder.eval()
    head.eval()
    dropout.eval()
    predictions: list[int] = []
    probabilities: list[float] = []
    with torch.no_grad():
        for start in range(0, len(labels), batch_size):
            batch = {key: value[start:start + batch_size].to(device) for key, value in encoded.items()}
            logits = head(dropout(encoder(**batch).last_hidden_state[:, 0]))
            positive_probability = logits.softmax(dim=-1)[:, 1]
            probabilities.extend(float(value) for value in positive_probability.cpu())
            predictions.extend(int(value) for value in logits.argmax(dim=-1).cpu())
    return binary_metrics(labels, predictions), predictions, probabilities


# Train all MiniLM parameters on all training labels and evaluate both splits every ten steps.
def main() -> None:
    # Parse paths, training settings, and the W&B project for this full-data router run.
    parser = argparse.ArgumentParser()
    parser.add_argument("--train-data", type=Path, default=Path("outputs/router-mbpp-easy-one-shot-20261013/router_dataset.jsonl"))
    parser.add_argument("--eval-data", type=Path, default=Path("outputs/router-evalplus-greedy-dual-label-20261013/router_evalplus_labels.jsonl"))
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/router-minilm-easy-dual-eval-20261013"))
    parser.add_argument("--model", default="microsoft/MiniLM-L12-H384-uncased")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--epochs", type=int, default=5)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--eval-batch-size", type=int, default=32)
    parser.add_argument("--eval-every-steps", type=int, default=10)
    parser.add_argument("--max-length", type=int, default=512)
    parser.add_argument("--learning-rate", type=float, default=5e-5)
    parser.add_argument("--wandb-project", default="grpo-mbpp")
    parser.add_argument("--wandb-entity", default="kunal-personal")
    args = parser.parse_args()

    # Set all random seeds before shuffling training examples and initializing the classifier head.
    random.seed(args.seed)
    torch.manual_seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)

    # Load all training and canonical EvalPlus label rows and validate their binary targets.
    train_rows = [json.loads(line) for line in args.train_data.read_text(encoding="utf-8").splitlines() if line.strip()]
    eval_rows = [json.loads(line) for line in args.eval_data.read_text(encoding="utf-8").splitlines() if line.strip()]
    train_labels = [int(row["label_mbpp"]) for row in train_rows]
    eval_mbpp_labels = [int(row["label_mbpp"]) for row in eval_rows]
    eval_mbpp_plus_labels = [int(row["label_mbpp_plus"]) for row in eval_rows]
    if any(label not in (0, 1) for label in train_labels + eval_mbpp_labels + eval_mbpp_plus_labels):
        raise ValueError("Every MBPP and MBPP+ router label must be zero or one.")

    # Load MiniLM, initialize the CLS classification head, and tokenize both full datasets.
    tokenizer = AutoTokenizer.from_pretrained(args.model)
    encoder = AutoModel.from_pretrained(args.model)
    train_encoded, train_labels = encode_rows(tokenizer, train_rows, args.max_length, "label_mbpp")
    eval_encoded, _ = encode_rows(tokenizer, eval_rows, args.max_length, "label_mbpp")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    encoder.to(device)
    dropout = torch.nn.Dropout(0.1).to(device)
    head = torch.nn.Linear(int(encoder.config.hidden_size), 2).to(device)
    optimizer = torch.optim.AdamW(list(encoder.parameters()) + list(head.parameters()), lr=args.learning_rate)
    loss_function = torch.nn.CrossEntropyLoss()

    # Create the W&B run before training and track all configuration and source artifacts.
    import wandb

    train_summary = json.loads((args.train_data.parent / "summary.json").read_text(encoding="utf-8"))
    eval_summary = json.loads((args.eval_data.parent / "summary.json").read_text(encoding="utf-8"))
    run = wandb.init(
        entity=args.wandb_entity,
        project=args.wandb_project,
        name="router-minilm-original-easy-dual-eval-20261013",
        job_type="router-full-training",
        config={
            "train_data": str(args.train_data),
            "eval_data": str(args.eval_data),
            "output_dir": str(args.output_dir),
            "seed": args.seed,
            "epochs": args.epochs,
            "batch_size": args.batch_size,
            "eval_batch_size": args.eval_batch_size,
            "eval_every_steps": args.eval_every_steps,
            "max_length": args.max_length,
            "learning_rate": args.learning_rate,
            "wandb_project": args.wandb_project,
            "wandb_entity": args.wandb_entity,
            "model": args.model,
            "encoder_trainable_parameters": sum(parameter.numel() for parameter in encoder.parameters()),
            "head_trainable_parameters": sum(parameter.numel() for parameter in head.parameters()),
            "head_architecture": f"Dropout(0.1) then Linear({encoder.config.hidden_size}, 2)",
            "positive_class": 1,
            "metric_prediction_rule": "argmax over two logits",
            "train_target": "passes every available MBPP-style task assertion on one greedy completion",
            "eval_targets": ["passes all MBPP base tests", "passes all MBPP+ base and extra tests"],
            "train_task_count": len(train_rows),
            "train_label_counts": train_summary["class_counts"],
            "eval_task_count": len(eval_rows),
            "eval_label_counts": {"solved": eval_summary["plus_solved"], "unsolved": eval_summary["plus_unsolved"]},
            "eval_base_label_counts": {"solved": eval_summary["base_solved"], "unsolved": eval_summary["base_unsolved"]},
            "evaluation_cadence": args.eval_every_steps,
            "logging_mode": "live during training",
        },
    )
    run.define_metric("optimizer_step")
    run.define_metric("train/*", step_metric="optimizer_step")
    run.define_metric("evalplus_mbpp/*", step_metric="optimizer_step")
    run.define_metric("evalplus_mbpp_plus/*", step_metric="optimizer_step")
    train_artifact = wandb.Artifact("router-mbpp-easy-one-shot-labels-20261013", type="dataset")
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

    # Measure train and held-out metrics and save every task prediction at one optimizer step.
    def evaluate_and_log(step: int) -> None:
        # Compute metrics on both complete datasets and publish the same values to W&B.
        train_metrics, train_predictions, train_probabilities = predict_rows(
            encoder, head, dropout, train_encoded, train_labels, device, args.eval_batch_size
        )
        eval_mbpp_metrics, eval_predictions, eval_probabilities = predict_rows(
            encoder, head, dropout, eval_encoded, eval_mbpp_labels, device, args.eval_batch_size
        )
        eval_mbpp_plus_metrics = binary_metrics(eval_mbpp_plus_labels, eval_predictions)
        record = {
            "optimizer_step": step,
            "training": train_metrics,
            "evalplus_mbpp": eval_mbpp_metrics,
            "evalplus_mbpp_plus": eval_mbpp_plus_metrics,
        }
        history.append(record)
        with metrics_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record) + "\n")
        with predictions_path.open("a", encoding="utf-8") as handle:
            for split, rows, labels, predictions, probabilities in (
                ("training", train_rows, train_labels, train_predictions, train_probabilities),
                ("evalplus", eval_rows, eval_mbpp_labels, eval_predictions, eval_probabilities),
            ):
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
        payload.update({f"evalplus_mbpp/{key}": value for key, value in eval_mbpp_metrics.items()})
        payload.update({f"evalplus_mbpp_plus/{key}": value for key, value in eval_mbpp_plus_metrics.items()})
        run.log(payload, step=step)
        print(json.dumps(record), flush=True)

    # Report the untrained baseline before the first optimizer update.
    evaluate_and_log(0)

    # Shuffle and train across every labeled training example for the configured number of epochs.
    global_step = 0
    started = time.time()
    labels_tensor = torch.tensor(train_labels, dtype=torch.long)
    loss_history_path = args.output_dir / "training_loss.jsonl"
    loss_history_path.unlink(missing_ok=True)
    for epoch in range(args.epochs):
        order = torch.randperm(len(train_rows))
        for start in range(0, len(train_rows), args.batch_size):
            indexes = order[start:start + args.batch_size]
            batch = {key: value[indexes].to(device) for key, value in train_encoded.items()}
            batch_labels = labels_tensor[indexes].to(device)
            encoder.train()
            head.train()
            dropout.train()
            optimizer.zero_grad(set_to_none=True)
            logits = head(dropout(encoder(**batch).last_hidden_state[:, 0]))
            loss = loss_function(logits, batch_labels)
            loss.backward()
            optimizer.step()
            global_step += 1
            loss_value = float(loss.detach().cpu())
            with loss_history_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps({"optimizer_step": global_step, "loss": loss_value}) + "\n")
            run.log({"train/loss": loss_value}, step=global_step)
            if global_step % args.eval_every_steps == 0:
                evaluate_and_log(global_step)
    if history[-1]["optimizer_step"] != global_step:
        evaluate_and_log(global_step)

    # Save the final encoder, classification head, metrics, and complete run configuration.
    encoder.eval()
    head.eval()
    encoder_dir = args.output_dir / "encoder"
    encoder.save_pretrained(encoder_dir, safe_serialization=True)
    tokenizer.save_pretrained(encoder_dir)
    torch.save(head.state_dict(), args.output_dir / "classification_head.pt")
    metadata = {
        "experiment": "MiniLM full-data router training with separate MBPP and MBPP+ retrieval evaluation",
        "model": args.model,
        "architecture": {
            "encoder": "fully fine-tuned MiniLM",
            "pooling": "last hidden state at CLS position",
            "head": f"Dropout(0.1) then Linear({encoder.config.hidden_size}, 2)",
            "encoder_parameters": sum(parameter.numel() for parameter in encoder.parameters()),
            "head_parameters": sum(parameter.numel() for parameter in head.parameters()),
        },
        "train_data": str(args.train_data),
        "eval_data": str(args.eval_data),
        "train_task_count": len(train_rows),
        "eval_task_count": len(eval_rows),
        "configuration": {
            "seed": args.seed,
            "epochs": args.epochs,
            "batch_size": args.batch_size,
            "eval_batch_size": args.eval_batch_size,
            "eval_every_steps": args.eval_every_steps,
            "max_length": args.max_length,
            "learning_rate": args.learning_rate,
            "optimizer": "AdamW",
            "loss": "cross entropy",
            "device": str(device),
        },
        "optimizer_steps": global_step,
        "elapsed_seconds": time.time() - started,
        "final_metrics": history[-1],
        "evaluation_history": str(metrics_path),
        "predictions": str(predictions_path),
        "training_loss": str(loss_history_path),
    }
    metadata_path = args.output_dir / "experiment.json"
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    model_artifact = wandb.Artifact("minilm-router-original-easy-20261013", type="model")
    model_artifact.add_dir(str(args.output_dir))
    run.log_artifact(model_artifact)
    run.summary["optimizer_steps"] = global_step
    run.summary["final_train_metrics"] = history[-1]["training"]
    run.summary["final_evalplus_mbpp_metrics"] = history[-1]["evalplus_mbpp"]
    run.summary["final_evalplus_mbpp_plus_metrics"] = history[-1]["evalplus_mbpp_plus"]
    run.summary["elapsed_seconds"] = metadata["elapsed_seconds"]
    run_url = run.url
    run.finish()
    print(json.dumps({"wandb_url": run_url, "output_dir": str(args.output_dir), "final_metrics": history[-1]}, indent=2), flush=True)


if __name__ == "__main__":
    # Start full-data router training with live W&B metrics.
    main()
