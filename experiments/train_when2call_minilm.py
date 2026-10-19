"""Run a two-stage When2Call action classifier experiment with MiniLM.

The script loads the official train_pref and test/mcq splits, infers action labels from
chosen responses, overfits one stratified batch without saving it, then trains for 1,000
optimizer steps if the batch reaches macro F1 1.0. It evaluates full train and test
splits at step 1,000, saves that checkpoint, and logs configuration and metrics to W&B.
"""

from __future__ import annotations

import json
import random
import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import torch
from datasets import load_dataset
from dotenv import load_dotenv
from torch.utils.data import DataLoader, Dataset
from transformers import AutoModelForSequenceClassification, AutoTokenizer

MODEL_NAME = "nreimers/MiniLM-L6-H384-uncased"
DATASET_NAME = "nvidia/When2Call"
LABELS = ("cannot_answer", "request_for_info", "tool_call", "direct")
LABEL_TO_ID = {label: index for index, label in enumerate(LABELS)}
BATCH_SIZE = 16
MAX_LENGTH = 512
OVERFIT_EVAL_INTERVAL = 10
OVERFIT_MAX_STEPS = 2000
FULL_TRAIN_STEPS = 1000
LEARNING_RATE = 5e-5
SEED = 20261019
OUTPUT_DIR = Path("outputs/when2call-minilm")
LOG_PATH = Path("logs/when2call-minilm.log")


@dataclass
class Example:
    """Store one model input and its inferred action label."""

    text: str
    label: int
    source_id: str


class ExampleDataset(Dataset[Example]):
    """Expose prepared examples to the PyTorch data loader."""

    def __init__(self, examples: list[Example]) -> None:
        # Keep the small text records in memory for deterministic data access.
        self.examples = examples

    def __len__(self) -> int:
        # Return the number of records in this split.
        return len(self.examples)

    def __getitem__(self, index: int) -> Example:
        # Return one text and label pair.
        return self.examples[index]


def infer_action_label(response: str) -> str:
    """Map a preferred response to its action class for the benchmark classifier."""
    # Recognize the dataset's tagged tool-call format before checking natural-language answers.
    match = re.fullmatch(r"\s*<TOOLCALL>\s*(.*?)\s*</TOOLCALL>\s*", response, re.IGNORECASE | re.DOTALL)
    if match:
        try:
            calls = json.loads(match.group(1))
            if isinstance(calls, list) and calls and all(isinstance(call, dict) and "name" in call for call in calls):
                return "tool_call"
        except json.JSONDecodeError:
            return "tool_call"
    # Treat explicit questions and requests for missing information as clarification targets.
    if "?" in response or re.search(r"(?i)\b(i'll need|i need|please provide|please specify|could you|would you|let me know)\b", response):
        return "request_for_info"
    # Separate explicit refusals from the few preferred responses that answer directly.
    if re.search(r"(?i)\b(unable|cannot|can't|can not|don't have|do not have|no access|not able|apolog|beyond my|lack|not within my capabilities|designed to .* not)\b", response):
        return "cannot_answer"
    return "direct"


def tools_text(tools: list[str]) -> str:
    """Format the available tool descriptions as stable input text."""
    # Keep tool JSON readable and deterministic for the encoder tokenizer.
    return "\n".join(tools) if tools else "No tools are available."


def prepare_train_examples(rows: Any) -> list[Example]:
    """Build inputs and inferred action labels from the train_pref chosen responses."""
    # Convert each user query, tool list, and preferred response into one classification record.
    examples = []
    for index, row in enumerate(rows):
        messages = row["messages"]
        user_text = "\n".join(message["content"] for message in messages if message["role"] == "user")
        response = row["chosen_response"]["content"]
        action = infer_action_label(response)
        examples.append(Example(f"Question: {user_text}\nAvailable tools:\n{tools_text(row['tools'])}", LABEL_TO_ID[action], str(index)))
    return examples


def prepare_test_examples(rows: Any) -> list[Example]:
    """Build inputs and official labels from the benchmark MCQ split."""
    # Preserve the MCQ ground-truth action labels for evaluation only.
    examples = []
    for row in rows:
        label = str(row["correct_answer"])
        if label not in LABEL_TO_ID:
            raise ValueError(f"Unsupported test label: {label}")
        text = f"Question: {row['question']}\nAvailable tools:\n{tools_text(row['tools'])}"
        examples.append(Example(text, LABEL_TO_ID[label], str(row["uuid"])))
    return examples


def stratified_batch(examples: list[Example], batch_size: int, seed: int) -> list[Example]:
    """Select a reproducible batch with broad representation of every observed class."""
    # Shuffle examples within each class so selection does not depend on dataset row order.
    rng = random.Random(seed)
    by_label: dict[int, list[Example]] = {}
    for example in examples:
        by_label.setdefault(example.label, []).append(example)
    for label_examples in by_label.values():
        rng.shuffle(label_examples)
    # Allocate evenly first, then use remaining slots where enough class examples exist.
    labels = sorted(by_label)
    if len(labels) < 2 or batch_size < len(labels):
        raise ValueError("The stratified batch requires at least two observed classes.")
    selected_counts = {label: min(batch_size // len(labels), len(by_label[label])) for label in labels}
    remaining = batch_size - sum(selected_counts.values())
    while remaining:
        available = [label for label in labels if selected_counts[label] < len(by_label[label])]
        if not available:
            raise ValueError("The observed classes do not have enough examples for the batch size.")
        for label in available:
            if remaining == 0:
                break
            selected_counts[label] += 1
            remaining -= 1
    # Shuffle the selected rows so the model sees a mixed class order in the fixed batch.
    selected = [example for label in labels for example in by_label[label][:selected_counts[label]]]
    rng.shuffle(selected)
    return selected


def collate(batch: list[Example], tokenizer: Any) -> dict[str, Any]:
    """Tokenize one batch and attach class labels and stable source identifiers."""
    # Pad each batch dynamically and truncate long tool schemas at the model limit.
    encoded = tokenizer([item.text for item in batch], padding=True, truncation=True, max_length=MAX_LENGTH, return_tensors="pt")
    encoded["labels"] = torch.tensor([item.label for item in batch], dtype=torch.long)
    encoded["source_ids"] = [item.source_id for item in batch]
    return encoded


def metric_values(targets: list[int], predictions: list[int], labels: list[int]) -> dict[str, Any]:
    """Compute accuracy and macro precision, recall, and F1 for explicit labels."""
    # Build the confusion counts so absent test classes remain visible as zero-score classes.
    matrix = [[0 for _ in labels] for _ in labels]
    label_index = {label: index for index, label in enumerate(labels)}
    for target, prediction in zip(targets, predictions, strict=True):
        matrix[label_index[target]][label_index[prediction]] += 1
    # Calculate per-class scores with zero for undefined precision or recall.
    per_class = {}
    for label in labels:
        index = label_index[label]
        tp = matrix[index][index]
        predicted_count = sum(matrix[row][index] for row in range(len(labels)))
        support = sum(matrix[index])
        precision = tp / predicted_count if predicted_count else 0.0
        recall = tp / support if support else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        per_class[LABELS[label]] = {"precision": precision, "recall": recall, "f1": f1, "support": support}
    # Average only labels present in the target set unless the caller explicitly includes absent labels.
    active_labels = [label for label in labels if sum(matrix[label_index[label]]) > 0]
    macro = {metric: sum(per_class[LABELS[label]][metric] for label in active_labels) / len(active_labels) for metric in ("precision", "recall", "f1")}
    accuracy = sum(matrix[index][index] for index in range(len(labels))) / len(targets) if targets else 0.0
    return {"accuracy": accuracy, "macro_precision": macro["precision"], "macro_recall": macro["recall"], "macro_f1": macro["f1"], "per_class": per_class, "confusion_matrix": matrix, "labels": [LABELS[label] for label in labels], "examples": len(targets)}


def batch_metrics(model: Any, tokenizer: Any, examples: list[Example], device: torch.device, metric_labels: list[int]) -> dict[str, Any]:
    """Evaluate the model on a supplied fixed batch or dataset."""
    # Run inference without gradients while keeping predictions in input order.
    loader = DataLoader(ExampleDataset(examples), batch_size=64, shuffle=False, collate_fn=lambda items: collate(items, tokenizer))
    targets: list[int] = []
    predictions: list[int] = []
    model.eval()
    with torch.inference_mode():
        for batch in loader:
            labels = batch.pop("labels").tolist()
            batch.pop("source_ids")
            inputs = {key: value.to(device) for key, value in batch.items()}
            predictions.extend(model(**inputs).logits.argmax(dim=-1).cpu().tolist())
            targets.extend(labels)
    return metric_values(targets, predictions, metric_labels)


def log_metrics(run: Any, prefix: str, metrics: dict[str, Any], step: int, loss: float | None = None) -> None:
    """Write aggregate and class-level metrics to W&B and the console."""
    # Flatten class metrics so W&B can chart each class beside aggregate scores.
    record: dict[str, Any] = {f"{prefix}/{key}": value for key, value in metrics.items() if isinstance(value, (int, float))}
    for label, values in metrics["per_class"].items():
        for metric, value in values.items():
            record[f"{prefix}/{label}/{metric}"] = value
    # Preserve the exact confusion matrix as a W&B table and JSON log field.
    record[f"{prefix}/confusion_matrix"] = json.dumps({"labels": metrics["labels"], "matrix": metrics["confusion_matrix"]})
    record[f"{prefix}/optimizer_step"] = step
    if loss is not None:
        record[f"{prefix}/loss"] = loss
    run.log(record)
    print(json.dumps({"stage": prefix, "step": step, **metrics, "loss": loss}, sort_keys=True), flush=True)


def move_batch(batch: dict[str, Any], device: torch.device) -> dict[str, Any]:
    """Move tensor fields to the selected training device."""
    # Leave source identifiers out of model inputs and preserve labels for the loss.
    return {key: value.to(device) for key, value in batch.items() if key != "source_ids"}


def main() -> int:
    """Run the batch overfit stage and then the full-data classifier stage."""
    # Load local secrets and make all random choices repeatable.
    load_dotenv(".env")
    random.seed(SEED)
    torch.manual_seed(SEED)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(SEED)
    # Load the chosen-response preference split and the requested MCQ test split.
    train_rows = load_dataset(DATASET_NAME, "train_pref", split="train")
    test_rows = load_dataset(DATASET_NAME, "test", split="mcq")
    train_examples = prepare_train_examples(train_rows)
    test_examples = prepare_test_examples(test_rows)
    train_counts = Counter(LABELS[item.label] for item in train_examples)
    test_counts = Counter(LABELS[item.label] for item in test_examples)
    # Select a batch that includes every observed chosen-response action type.
    overfit_examples = stratified_batch(train_examples, BATCH_SIZE, SEED)
        # Require W&B because the user asked to log the complete experiment.
    import wandb
    api_key = __import__("os").environ.get("WANDB_API_KEY")
    if not api_key:
        raise RuntimeError("WANDB_API_KEY is missing from .env or the environment.")
    wandb.login(key=api_key, relogin=False)
    run = wandb.init(project="post-training", name=f"when2call-minilm-pref-{datetime.now(timezone.utc):%Y%m%d-%H%M%S}", config={"model": MODEL_NAME, "dataset": DATASET_NAME, "train_config": "train_pref/train", "eval_config": "test/mcq", "train_rows": len(train_examples), "test_rows": len(test_examples), "train_label_counts_inferred_from_chosen_response": dict(train_counts), "test_label_counts_official": dict(test_counts), "train_labels_inferred_from_response": True, "rejected_response_used_for_training": False, "batch_size": BATCH_SIZE, "overfit_eval_interval_steps": OVERFIT_EVAL_INTERVAL, "overfit_max_steps": OVERFIT_MAX_STEPS, "full_train_steps": FULL_TRAIN_STEPS, "full_eval_interval_steps": 1000, "learning_rate": LEARNING_RATE, "max_length": MAX_LENGTH, "seed": SEED, "overfit_batch_label_counts": dict(Counter(LABELS[item.label] for item in overfit_examples)), "checkpoint_policy": "No overfit checkpoint. Save after step 1000 full train and test evaluation."})
    # Initialize the encoder classifier with the inferred action labels and the direct-response outlier class.
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME, num_labels=len(LABELS), id2label=dict(enumerate(LABELS)), label2id=LABEL_TO_ID)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=LEARNING_RATE)
    single_batch = collate(overfit_examples, tokenizer)
    train_loader = DataLoader(ExampleDataset(train_examples), batch_size=BATCH_SIZE, shuffle=True, collate_fn=lambda items: collate(items, tokenizer), generator=torch.Generator().manual_seed(SEED))
    # Reuse one fixed training batch until its macro F1 reaches the requested value.
    hit_target = False
    for step in range(1, OVERFIT_MAX_STEPS + 1):
        model.train()
        batch = move_batch(single_batch, device)
        optimizer.zero_grad(set_to_none=True)
        output = model(**batch)
        output.loss.backward()
        optimizer.step()
        wandb.log({"overfit/train_loss": float(output.loss.detach().cpu()), "overfit/optimizer_step": step})
        if step % OVERFIT_EVAL_INTERVAL == 0:
            metrics = batch_metrics(model, tokenizer, overfit_examples, device, list(range(len(LABELS))))
            log_metrics(wandb, "overfit", metrics, step, float(output.loss.detach().cpu()))
            if metrics["macro_f1"] >= 1.0:
                hit_target = True
                break
    # Do not begin full-dataset training unless the single-batch target was achieved.
    if not hit_target:
        print(json.dumps({"stage": "overfit", "result": "target_not_reached", "max_steps": OVERFIT_MAX_STEPS}), flush=True)
        wandb.summary["overfit/target_reached"] = False
        wandb.finish(exit_code=2)
        return 2
    wandb.summary["overfit/target_reached"] = True
    wandb.summary["overfit/target_step"] = step
    wandb.summary["overfit/target_macro_f1"] = 1.0
    # Continue from the in-memory overfit weights and train over the complete requested split.
    iterator = iter(train_loader)
    full_eval_labels = list(range(len(LABELS)))
    for full_step in range(1, FULL_TRAIN_STEPS + 1):
        try:
            batch = next(iterator)
        except StopIteration:
            train_loader.generator.manual_seed(SEED + full_step)
            iterator = iter(train_loader)
            batch = next(iterator)
        model.train()
        batch = move_batch(batch, device)
        optimizer.zero_grad(set_to_none=True)
        output = model(**batch)
        output.loss.backward()
        optimizer.step()
        global_step = step + full_step
        wandb.log({"full_train/loss": float(output.loss.detach().cpu()), "full_train/optimizer_step": full_step, "optimizer_step": global_step})
        # Evaluate both complete splits after every 1,000 full-data optimizer steps.
        if full_step % 1000 == 0:
            train_metrics = batch_metrics(model, tokenizer, train_examples, device, full_eval_labels)
            test_metrics = batch_metrics(model, tokenizer, test_examples, device, list(range(len(LABELS))))
            log_metrics(wandb, "full_train_eval", train_metrics, full_step)
            log_metrics(wandb, "test_eval", test_metrics, full_step)
            # Save the checkpoint only after both requested full-split evaluations finish.
            checkpoint = OUTPUT_DIR / f"checkpoint-{full_step}"
            checkpoint.mkdir(parents=True, exist_ok=True)
            model.save_pretrained(checkpoint)
            tokenizer.save_pretrained(checkpoint)
            artifact = wandb.Artifact(f"when2call-minilm-checkpoint-{full_step}", type="model")
            artifact.add_dir(str(checkpoint))
            run.log_artifact(artifact)
            wandb.summary["checkpoint/path"] = str(checkpoint)
            wandb.summary["checkpoint/optimizer_step"] = global_step
            wandb.summary["test_eval/macro_f1"] = test_metrics["macro_f1"]
    # Close the single W&B run after all requested training and checkpoint work finishes.
    wandb.finish()
    return 0


if __name__ == "__main__":
    # Exit with the training result so orchestration can detect a missed overfit target.
    raise SystemExit(main())
