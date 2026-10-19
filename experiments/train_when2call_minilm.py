"""Train and evaluate a MiniLM action classifier on When2Call.

The script loads train_pref and test/mcq, infers labels for train_pref, evaluates the
pretrained encoder with a new classification head before training, then trains for
the configured epoch limit. It evaluates both splits after each epoch, overwrites a
rolling checkpoint, and logs metrics and timing data to W&B.
"""

from __future__ import annotations

import json
import re
import signal
import time
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
EPOCHS = 1_000_000
LEARNING_RATE = 5e-5
SEED = 20261019
OUTPUT_DIR = Path("outputs/when2call-minilm")
STOP_REQUESTED = False


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


def log_metrics(run: Any, prefix: str, metrics: dict[str, Any], step: int, loss: float | None = None, eval_seconds: float | None = None, epoch: int | None = None) -> None:
    """Write aggregate and class-level metrics to W&B and the console."""
    # Flatten class metrics so W&B can chart each class beside aggregate scores.
    record: dict[str, Any] = {f"{prefix}/{key}": value for key, value in metrics.items() if isinstance(value, (int, float))}
    for label, values in metrics["per_class"].items():
        for metric, value in values.items():
            record[f"{prefix}/{label}/{metric}"] = value
    # Preserve the exact confusion matrix as a W&B table and JSON log field.
    record[f"{prefix}/confusion_matrix"] = json.dumps({"labels": metrics["labels"], "matrix": metrics["confusion_matrix"]})
    record[f"{prefix}/optimizer_step"] = step
    record["optimizer_step"] = step
    if loss is not None:
        record[f"{prefix}/loss"] = loss
    if eval_seconds is not None:
        record[f"{prefix}/eval_seconds"] = eval_seconds
    if epoch is not None:
        record[f"{prefix}/epoch"] = epoch
    run.log(record)
    print(json.dumps({"stage": prefix, "step": step, "epoch": epoch, **metrics, "loss": loss, "eval_seconds": eval_seconds}, sort_keys=True), flush=True)


def timed_metrics(model: Any, tokenizer: Any, examples: list[Example], device: torch.device, metric_labels: list[int]) -> tuple[dict[str, Any], float]:
    """Measure one complete evaluation split and return its elapsed time."""
    # Synchronize around inference so asynchronous CUDA work is included in the timing.
    sync_device(device)
    started = time.perf_counter()
    metrics = batch_metrics(model, tokenizer, examples, device, metric_labels)
    sync_device(device)
    return metrics, time.perf_counter() - started


def sync_device(device: torch.device) -> None:
    """Wait for queued GPU work so elapsed timings reflect completed computation."""
    # Synchronize CUDA only because CPU operations finish synchronously.
    if device.type == "cuda":
        torch.cuda.synchronize(device)


def request_graceful_stop(signum: int, frame: Any) -> None:
    """Ask the epoch loop to stop after it saves the current epoch checkpoint."""
    # Keep training through evaluation and checkpointing before honoring a stop signal.
    global STOP_REQUESTED
    STOP_REQUESTED = True


def move_batch(batch: dict[str, Any], device: torch.device) -> dict[str, Any]:
    """Move tensor fields to the selected training device."""
    # Leave source identifiers out of model inputs and preserve labels for the loss.
    return {key: value.to(device) for key, value in batch.items() if key != "source_ids"}


def main() -> int:
    """Evaluate the base classifier, then train and evaluate each complete epoch."""
    # Load local secrets and make all random choices repeatable.
    load_dotenv(".env")
    signal.signal(signal.SIGINT, request_graceful_stop)
    signal.signal(signal.SIGTERM, request_graceful_stop)
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
    # Require W&B because the user asked to log the complete experiment.
    import wandb
    api_key = __import__("os").environ.get("WANDB_API_KEY")
    if not api_key:
        raise RuntimeError("WANDB_API_KEY is missing from .env or the environment.")
    wandb.login(key=api_key, relogin=False)
    steps_per_epoch = (len(train_examples) + BATCH_SIZE - 1) // BATCH_SIZE
    run = wandb.init(project="post-training", name=f"when2call-minilm-continuous-{datetime.now(timezone.utc):%Y%m%d-%H%M%S}", config={"model": MODEL_NAME, "dataset": DATASET_NAME, "train_config": "train_pref/train", "eval_config": "test/mcq", "train_rows": len(train_examples), "test_rows": len(test_examples), "train_label_counts_inferred_from_chosen_response": dict(train_counts), "test_label_counts_official": dict(test_counts), "train_labels_inferred_from_response": True, "rejected_response_used_for_training": False, "batch_size": BATCH_SIZE, "epochs": EPOCHS, "steps_per_epoch": steps_per_epoch, "total_optimizer_steps": EPOCHS * steps_per_epoch, "evaluation_policy": "Baseline at step 0 and full train and test evaluation after every epoch under shared metric keys.", "learning_rate": LEARNING_RATE, "max_length": MAX_LENGTH, "seed": SEED, "checkpoint_policy": "Overwrite one rolling local checkpoint after each epoch evaluation."})
    # Use one optimizer-step axis for baseline and all later evaluation metrics.
    wandb.define_metric("optimizer_step")
    wandb.define_metric("train_eval/*", step_metric="optimizer_step")
    wandb.define_metric("test_eval/*", step_metric="optimizer_step")
    wandb.define_metric("train/*", step_metric="optimizer_step")
    # Initialize the pretrained encoder with a fresh four-class classification head.
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME, num_labels=len(LABELS), id2label=dict(enumerate(LABELS)), label2id=LABEL_TO_ID)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=LEARNING_RATE)
    train_loader = DataLoader(ExampleDataset(train_examples), batch_size=BATCH_SIZE, shuffle=True, collate_fn=lambda items: collate(items, tokenizer), generator=torch.Generator().manual_seed(SEED))
    # Measure the pretrained base classifier on both complete splits before any updates.
    all_labels = list(range(len(LABELS)))
    base_train, base_train_seconds = timed_metrics(model, tokenizer, train_examples, device, all_labels)
    base_test, base_test_seconds = timed_metrics(model, tokenizer, test_examples, device, all_labels)
    log_metrics(wandb, "train_eval", base_train, 0, eval_seconds=base_train_seconds, epoch=0)
    log_metrics(wandb, "test_eval", base_test, 0, eval_seconds=base_test_seconds, epoch=0)
    # Train for the configured long run and time every optimizer update.
    global_step = 0
    for epoch in range(1, EPOCHS + 1):
        for batch in train_loader:
            sync_device(device)
            step_started = time.perf_counter()
            model.train()
            batch = move_batch(batch, device)
            optimizer.zero_grad(set_to_none=True)
            output = model(**batch)
            output.loss.backward()
            optimizer.step()
            sync_device(device)
            step_seconds = time.perf_counter() - step_started
            step_loss = float(output.loss.detach().cpu())
            global_step += 1
            wandb.log({"optimizer_step": global_step, "train/loss": step_loss, "train/optimizer_step": global_step, "train/epoch": epoch, "train/step_seconds": step_seconds})
            print(json.dumps({"stage": "train", "epoch": epoch, "step": global_step, "step_seconds": step_seconds, "loss": step_loss}, sort_keys=True), flush=True)
        # Evaluate the complete train and test splits at the end of every epoch.
        train_metrics, train_eval_seconds = timed_metrics(model, tokenizer, train_examples, device, all_labels)
        test_metrics, test_eval_seconds = timed_metrics(model, tokenizer, test_examples, device, all_labels)
        log_metrics(wandb, "train_eval", train_metrics, global_step, eval_seconds=train_eval_seconds, epoch=epoch)
        log_metrics(wandb, "test_eval", test_metrics, global_step, eval_seconds=test_eval_seconds, epoch=epoch)
        # Save each epoch checkpoint only after both full-split evaluations finish.
        checkpoint = OUTPUT_DIR / "latest"
        checkpoint.mkdir(parents=True, exist_ok=True)
        model.save_pretrained(checkpoint)
        tokenizer.save_pretrained(checkpoint)
        torch.save({"optimizer": optimizer.state_dict(), "epoch": epoch, "optimizer_step": global_step}, checkpoint / "training_state.pt")
        wandb.summary["checkpoint/path"] = str(checkpoint)
        wandb.summary["checkpoint/epoch"] = epoch
        wandb.summary["checkpoint/optimizer_step"] = global_step
        wandb.log({"checkpoint/epoch": epoch, "checkpoint/optimizer_step": global_step})
        for split, metrics in (("train", train_metrics), ("test", test_metrics)):
            for metric in ("accuracy", "macro_precision", "macro_recall", "macro_f1"):
                wandb.summary[f"latest/{split}/{metric}"] = metrics[metric]
        # Finish cleanly after the current evaluation and rolling checkpoint are saved.
        if STOP_REQUESTED:
            break
    # Close the single W&B run after all epoch evaluations and checkpoint uploads finish.
    wandb.finish()
    return 0


if __name__ == "__main__":
    # Exit with the training result so orchestration can detect a missed overfit target.
    raise SystemExit(main())
