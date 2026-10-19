"""Train and evaluate a Jina long-context action classifier on When2Call.

The script loads train_pref and test/mcq, prepares action labels, tokenizes complete
inputs, evaluates the pretrained encoder with a new classification head, and then
trains with memory-aware microbatches. It evaluates both splits after each epoch,
saves a rolling checkpoint, and logs metrics and timing data to W&B.
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
from types import SimpleNamespace
from typing import Any

import torch
from datasets import load_dataset
from dotenv import load_dotenv
from torch.utils.data import DataLoader, Dataset
from transformers import AutoConfig, AutoModel, AutoTokenizer

MODEL_NAME = "jinaai/jina-embeddings-v2-small-en"
DATASET_NAME = "nvidia/When2Call"
LABELS = ("cannot_answer", "request_for_info", "tool_call", "direct")
LABEL_TO_ID = {label: index for index, label in enumerate(LABELS)}
BATCH_SIZE = 16
MAX_LENGTH = 8192
ATTENTION_HEADS = 8
MAX_BATCH_ATTENTION_VALUES = 300_000_000
EPOCHS = 1_000_000
LEARNING_RATE = 5e-5
SEED = 20261019
OUTPUT_DIR = Path("outputs/when2call-jina-v2-small")
STOP_REQUESTED = False


@dataclass
class Example:
    """Store one model input and its inferred action label."""

    text: str
    label: int
    source_id: str
    token_ids: list[int] | None = None


class JinaSequenceClassifier(torch.nn.Module):
    """Add a trainable action head to the pretrained Jina encoder."""

    def __init__(self, encoder: torch.nn.Module, num_labels: int) -> None:
        # Create a fresh linear head over masked mean pooled token states.
        super().__init__()
        self.encoder = encoder
        self.classifier = torch.nn.Linear(encoder.config.hidden_size, num_labels)

    def forward(self, input_ids: torch.Tensor, attention_mask: torch.Tensor) -> Any:
        # Pool every non-padding token before producing the action logits.
        output = self.encoder(input_ids=input_ids, attention_mask=attention_mask)
        token_states = output.last_hidden_state
        mask = attention_mask.unsqueeze(-1).to(token_states.dtype)
        pooled = (token_states * mask).sum(dim=1) / mask.sum(dim=1).clamp_min(1)
        return SimpleNamespace(logits=self.classifier(pooled))

    def save_pretrained(self, path: Path) -> None:
        # Save weights and metadata without copying custom model source files.
        path.mkdir(parents=True, exist_ok=True)
        weights = {key: value.detach().cpu() for key, value in self.state_dict().items()}
        torch.save(weights, path / "model_state.pt")
        (path / "encoder_config.json").write_text(json.dumps(self.encoder.config.to_dict(), indent=2) + "\n")
        (path / "classifier_config.json").write_text(json.dumps({"base_model": MODEL_NAME, "labels": LABELS, "pooling": "attention_masked_mean"}, indent=2) + "\n")


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


def tokenize_examples(examples: list[Example], tokenizer: Any) -> None:
    """Tokenize each complete example once and check the model context limit."""
    # Store complete token sequences so batching and evaluation do not retokenize text.
    for item in examples:
        item.token_ids = tokenizer(item.text, add_special_tokens=True, truncation=False, verbose=False)["input_ids"]
        if len(item.token_ids) > MAX_LENGTH:
            raise ValueError(f"Input {item.source_id} has {len(item.token_ids)} tokens, above the {MAX_LENGTH}-token Jina limit.")


def length_aware_batches(examples: list[Example], max_examples: int = BATCH_SIZE) -> list[list[Example]]:
    """Group similar sequence lengths under a memory-aware attention budget."""
    # Sort long inputs first and limit the dense attention work in each physical batch.
    ordered = sorted(examples, key=lambda item: len(item.token_ids or []), reverse=True)
    batches: list[list[Example]] = []
    current: list[Example] = []
    current_max = 0
    for item in ordered:
        item_length = len(item.token_ids or [])
        candidate_max = max(current_max, item_length)
        exceeds_examples = len(current) >= max_examples
        exceeds_attention = bool(current) and (len(current) + 1) * ATTENTION_HEADS * candidate_max * candidate_max > MAX_BATCH_ATTENTION_VALUES
        if exceeds_examples or exceeds_attention:
            batches.append(current)
            current = []
            current_max = 0
        current.append(item)
        current_max = max(current_max, item_length)
    # Keep the final partial batch.
    if current:
        batches.append(current)
    return batches


def collate(batch: list[Example], tokenizer: Any) -> dict[str, Any]:
    """Pad complete token sequences without truncation."""
    # Pad only to the longest sequence in this memory-aware microbatch.
    features = []
    for item in batch:
        if item.token_ids is None:
            raise ValueError("Examples must be tokenized before batching.")
        features.append({"input_ids": item.token_ids, "attention_mask": [1] * len(item.token_ids)})
    encoded = tokenizer.pad(features, padding=True, return_tensors="pt")
    if encoded["input_ids"].shape[1] > MAX_LENGTH:
        raise ValueError("A padded model input exceeds Jina's context limit.")
    encoded["labels"] = torch.tensor([item.label for item in batch], dtype=torch.long)
    encoded["source_ids"] = [item.source_id for item in batch]
    return encoded


def autocast_context(device: torch.device) -> Any:
    """Use bfloat16 on CUDA to reduce the memory cost of long sequences."""
    # Keep CPU execution in its default precision.
    return torch.autocast(device_type="cuda", dtype=torch.bfloat16) if device.type == "cuda" else torch.autocast(device_type="cpu", enabled=False)


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
    """Evaluate the model on a complete supplied split."""
    # Process complete inputs in length-aware batches and collect example-level predictions.
    targets: list[int] = []
    predictions: list[int] = []
    model.eval()
    with torch.inference_mode():
        for items in length_aware_batches(examples):
            batch = collate(items, tokenizer)
            labels = batch.pop("labels").to(device)
            batch.pop("source_ids")
            inputs = {key: value.to(device) for key, value in batch.items()}
            with autocast_context(device):
                logits = model(**inputs).logits
            predictions.extend(logits.argmax(dim=-1).cpu().tolist())
            targets.extend(labels.cpu().tolist())
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
    """Move model-input tensors to the selected training device."""
    # Leave labels and source identifiers for loss and reporting handling.
    excluded = {"labels", "source_ids"}
    return {key: value.to(device) for key, value in batch.items() if key not in excluded}


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
    run = wandb.init(project="post-training", name=f"when2call-jina-v2-small-max-{EPOCHS}-epochs-{datetime.now(timezone.utc):%Y%m%d-%H%M%S}", config={"model": MODEL_NAME, "dataset": DATASET_NAME, "train_config": "train_pref/train", "eval_config": "test/mcq", "train_rows": len(train_examples), "test_rows": len(test_examples), "train_label_counts_inferred_from_chosen_response": dict(train_counts), "test_label_counts_official": dict(test_counts), "train_labels_inferred_from_response": True, "rejected_response_used_for_training": False, "effective_batch_size": BATCH_SIZE, "epochs": EPOCHS, "steps_per_epoch": steps_per_epoch, "total_optimizer_steps": EPOCHS * steps_per_epoch, "evaluation_policy": "Baseline at step 0 and full train and test evaluation after every epoch under shared metric keys.", "learning_rate": LEARNING_RATE, "max_sequence_length": MAX_LENGTH, "input_handling": "Process each complete input in one sequence; use length-aware microbatches and gradient accumulation to preserve effective batch size.", "attention_implementation": "PyTorch scaled dot-product attention with bfloat16 and gradient checkpointing.", "max_batch_attention_values": MAX_BATCH_ATTENTION_VALUES, "seed": SEED, "checkpoint_policy": "Overwrite one rolling local checkpoint after each epoch evaluation."})
    # Use one optimizer-step axis for baseline and all later evaluation metrics.
    wandb.define_metric("optimizer_step")
    wandb.define_metric("train_eval/*", step_metric="optimizer_step")
    wandb.define_metric("test_eval/*", step_metric="optimizer_step")
    wandb.define_metric("train/*", step_metric="optimizer_step")
    # Initialize the pretrained encoder with a fresh four-class classification head.
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True)
    tokenizer.model_max_length = MAX_LENGTH
    tokenize_examples(train_examples, tokenizer)
    tokenize_examples(test_examples, tokenizer)
    config = AutoConfig.from_pretrained(MODEL_NAME, trust_remote_code=True)
    config.attn_implementation = "torch"
    encoder = AutoModel.from_pretrained(MODEL_NAME, config=config, trust_remote_code=True)
    encoder.gradient_checkpointing_enable()
    model = JinaSequenceClassifier(encoder, len(LABELS))
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=LEARNING_RATE)
    train_loader = DataLoader(ExampleDataset(train_examples), batch_size=BATCH_SIZE, shuffle=True, collate_fn=lambda items: items, generator=torch.Generator().manual_seed(SEED))
    # Measure the pretrained base classifier on both complete splits before any updates.
    all_labels = list(range(len(LABELS)))
    base_train, base_train_seconds = timed_metrics(model, tokenizer, train_examples, device, all_labels)
    base_test, base_test_seconds = timed_metrics(model, tokenizer, test_examples, device, all_labels)
    log_metrics(wandb, "train_eval", base_train, 0, eval_seconds=base_train_seconds, epoch=0)
    log_metrics(wandb, "test_eval", base_test, 0, eval_seconds=base_test_seconds, epoch=0)
    # Train for the configured long run and time every optimizer update.
    global_step = 0
    for epoch in range(1, EPOCHS + 1):
        for logical_batch in train_loader:
            sync_device(device)
            step_started = time.perf_counter()
            model.train()
            optimizer.zero_grad(set_to_none=True)
            weighted_loss = 0.0
            for microbatch_examples in length_aware_batches(logical_batch):
                batch = collate(microbatch_examples, tokenizer)
                labels = batch.pop("labels").to(device)
                batch.pop("source_ids")
                inputs = move_batch(batch, device)
                with autocast_context(device):
                    logits = model(**inputs).logits
                    loss = torch.nn.functional.cross_entropy(logits, labels)
                scaled_loss = loss * (len(microbatch_examples) / len(logical_batch))
                scaled_loss.backward()
                weighted_loss += float(loss.detach().cpu()) * len(microbatch_examples) / len(logical_batch)
            optimizer.step()
            sync_device(device)
            step_seconds = time.perf_counter() - step_started
            step_loss = weighted_loss
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
