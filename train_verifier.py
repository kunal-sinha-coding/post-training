"""Train a task-conditioned CodeBERT verifier from sandbox-labeled MBPP candidates.

The flow loads official MBPP records, splits tasks before generating candidates, labels
reference implementations as correct, labels generated candidates from the sandbox,
trains a CodeBERT encoder with a binary classification head, logs quarter-epoch metrics to
Weights & Biases, and saves the verifier plus its reproducible JSONL dataset. The same
file can reload the saved labeled evaluation data and report thresholded predictions.
"""

from __future__ import annotations

import argparse
import json
import random
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import torch
from torch import Tensor, nn
from torch.utils.data import DataLoader, Dataset

from data import load_mbpp, split_dataset
from sandbox import score_completion


@dataclass
class VerifierExample:
    """Store one task-conditioned candidate and its sandbox correctness label."""

    task_id: str
    task: str
    code: str
    label: float
    source: str


class VerifierDataset(Dataset[VerifierExample]):
    """Expose verifier examples to a PyTorch data loader."""

    def __init__(self, examples: list[VerifierExample]) -> None:
        # Keep examples in memory because the generated verifier dataset is intentionally small.
        self.examples = examples

    def __len__(self) -> int:
        # Return the number of labeled candidates.
        return len(self.examples)

    def __getitem__(self, index: int) -> VerifierExample:
        # Return one labeled candidate by position.
        return self.examples[index]


def seed_everything(seed: int) -> None:
    """Make candidate generation and verifier training as reproducible as practical."""
    # Seed Python and PyTorch random number generators.
    random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def candidate_text(task: str, code: str) -> str:
    """Build the task-conditioned text consumed by CodeBERT."""
    # Separate the natural-language task from the candidate implementation.
    return f"Task:\n{task.strip()}\n\nCandidate code:\n{code.strip()}"


def record_task(record: dict[str, Any]) -> str:
    """Extract the natural-language task from a normalized MBPP record."""
    # Remove the visible test protocol so the verifier focuses on task and implementation semantics.
    prompt = str(record.get("prompt", ""))
    marker = "Task:\n"
    if marker in prompt:
        prompt = prompt.split(marker, 1)[1].split("\n\nTests:", 1)[0]
    return prompt.strip()


def label_generated_candidate(item: tuple[str, str, str, str]) -> VerifierExample:
    """Sandbox one generated candidate and return its binary verifier label."""
    # Run one isolated candidate evaluation so thread workers can execute independently.
    task_id, task, code, tests = item
    _, detail = score_completion(code, tests)
    return VerifierExample(task_id, task, code.strip(), float(detail["status"] == "passed"), "generated")


def generate_candidates(
    records: list[dict[str, Any]],
    generator_name: str,
    candidates_per_task: int,
    temperature: float,
    top_p: float,
    max_new_tokens: int,
    batch_size: int,
    label_workers: int,
) -> list[VerifierExample]:
    """Create positive references and sandbox-labeled model candidates for each task."""
    # Import Transformers lazily so dataset-only utilities remain lightweight.
    from transformers import AutoModelForCausalLM, AutoTokenizer

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    tokenizer = AutoTokenizer.from_pretrained(generator_name, trust_remote_code=False)
    if tokenizer.pad_token is None:
        # Reuse the EOS token when the causal tokenizer lacks a padding token.
        tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(generator_name, trust_remote_code=False)
    model.to(device)
    model.eval()
    examples: list[VerifierExample] = []
    pending_labels: list[tuple[str, str, str, str]] = []

    # Generate candidates task by task while keeping labels pending for parallel sandbox execution.
    for record_index, record in enumerate(records, start=1):
        task_id = str(record["task_id"])
        task = record_task(record)
        reference = str(record["reference_code"]).strip()
        examples.append(VerifierExample(task_id, task, reference, 1.0, "reference"))
        prompt = str(record["prompt"])
        encoded = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=512).to(device)
        generated: list[str] = []
        remaining = candidates_per_task

        # Generate in bounded microbatches to control GPU memory.
        while remaining > 0:
            current_batch = min(batch_size, remaining)
            with torch.inference_mode():
                outputs = model.generate(
                    **encoded,
                    do_sample=True,
                    temperature=temperature,
                    top_p=top_p,
                    num_return_sequences=current_batch,
                    max_new_tokens=max_new_tokens,
                    pad_token_id=tokenizer.pad_token_id,
                )
            generated.extend(tokenizer.batch_decode(outputs[:, encoded["input_ids"].shape[1] :], skip_special_tokens=True))
            remaining -= current_batch
        pending_labels.extend((task_id, task, code, str(record["test_code"])) for code in generated)
        if record_index % 25 == 0 or record_index == len(records):
            print(f"Generated candidates for {record_index}/{len(records)} tasks.", flush=True)

    # Label all generated candidates concurrently because sandbox work is subprocess and I/O bound.
    with ThreadPoolExecutor(max_workers=max(1, label_workers)) as executor:
        labeled = list(executor.map(label_generated_candidate, pending_labels))
    examples.extend(labeled)
    print(f"Labeled {len(labeled)} generated candidates with {max(1, label_workers)} workers.", flush=True)

    # Release the generator before loading CodeBERT to avoid unnecessary GPU residency.
    del model
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    return examples


def save_examples(examples: list[VerifierExample], path: Path) -> None:
    """Save verifier examples as a reproducible JSONL artifact."""
    # Write one complete labeled example per line for later audit and reuse.
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for example in examples:
            handle.write(json.dumps(asdict(example), ensure_ascii=False) + "\n")


def collate_examples(batch: list[VerifierExample], tokenizer: Any, max_length: int) -> dict[str, Any]:
    """Tokenize a verifier batch and preserve labels and metadata."""
    # Encode task and candidate together with CodeBERT's standard special tokens.
    encoded = tokenizer([candidate_text(item.task, item.code) for item in batch], padding=True, truncation=True, max_length=max_length, return_tensors="pt")
    encoded["labels"] = torch.tensor([item.label for item in batch], dtype=torch.float32)
    encoded["task_ids"] = [item.task_id for item in batch]
    return encoded


def auc_metric(probabilities: Tensor, labels: Tensor) -> float:
    """Estimate pairwise ROC AUC for one collection of labeled candidates."""
    # Compare every positive score with every negative score and award half credit for ties.
    positives = labels == 1
    negatives = labels == 0
    if not positives.any() or not negatives.any():
        return 0.5
    pairwise = (probabilities[positives].unsqueeze(1) > probabilities[negatives].unsqueeze(0)).float()
    ties = (probabilities[positives].unsqueeze(1) == probabilities[negatives].unsqueeze(0)).float()
    return (pairwise.sum() + 0.5 * ties.sum()).div(positives.sum() * negatives.sum()).item()


def threshold_metrics(probabilities: Tensor, labels: Tensor, threshold: float) -> dict[str, float]:
    """Compute binary metrics at one probability threshold."""
    # Convert probabilities into yes or no predictions at the requested threshold.
    predictions = probabilities >= threshold
    accuracy = (predictions == labels.bool()).float().mean().item()
    true_positive = ((predictions == 1) & (labels == 1)).sum().item()
    false_positive = ((predictions == 1) & (labels == 0)).sum().item()
    false_negative = ((predictions == 0) & (labels == 1)).sum().item()
    precision = true_positive / (true_positive + false_positive) if true_positive + false_positive else 0.0
    recall = true_positive / (true_positive + false_negative) if true_positive + false_negative else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"accuracy": accuracy, "precision": precision, "recall": recall, "f1": f1}


def binary_metrics(logits: Tensor, labels: Tensor, task_ids: list[str] | None = None) -> dict[str, float]:
    """Compute global metrics and macro averages over task-local metrics."""
    # Convert logits to probabilities once so global and local metrics use identical scores.
    probabilities = torch.sigmoid(logits)
    metrics = {"auc": auc_metric(probabilities, labels), "positive_rate": labels.mean().item()}
    task_groups: dict[str, list[int]] = {}
    if task_ids is not None:
        # Group candidate positions by task so every task receives equal macro weight.
        for index, task_id in enumerate(task_ids):
            task_groups.setdefault(task_id, []).append(index)
    for threshold_index in range(1, 11):
        # Log global metrics at every requested tenth so candidate-level behavior remains visible.
        threshold = threshold_index / 10
        global_values = threshold_metrics(probabilities, labels, threshold)
        for name, value in global_values.items():
            metrics[f"threshold_{threshold:.1f}/{name}"] = value
        if task_groups:
            # Average each metric across tasks after computing it independently within each task.
            local_values = [threshold_metrics(probabilities[indexes], labels[indexes], threshold) for indexes in task_groups.values()]
            for name in global_values:
                metrics[f"local_threshold_{threshold:.1f}/{name}"] = sum(values[name] for values in local_values) / len(local_values)
    if task_groups:
        # Average task-local AUC values to expose within-task ranking quality.
        metrics["local_auc"] = sum(auc_metric(probabilities[indexes], labels[indexes]) for indexes in task_groups.values()) / len(task_groups)
        metrics["local_positive_rate"] = sum(labels[indexes].mean().item() for indexes in task_groups.values()) / len(task_groups)
    return metrics


def generated_only(examples: list[VerifierExample]) -> list[VerifierExample]:
    """Remove reference implementations from verifier training and evaluation."""
    # Keep only candidates whose labels came from sandbox execution.
    return [example for example in examples if example.source == "generated"]


def prediction_rows(model: nn.Module, examples: list[VerifierExample], loader: DataLoader, device: torch.device) -> list[dict[str, Any]]:
    """Return one probability and thresholded prediction for every labeled example."""
    # Preserve loader order so predictions can be joined directly to saved examples.
    model.eval()
    probabilities: list[float] = []
    with torch.inference_mode():
        for batch in loader:
            batch = {key: value.to(device) if isinstance(value, Tensor) else value for key, value in batch.items()}
            output = model(**{key: value for key, value in batch.items() if key not in {"labels", "task_ids"}})
            probabilities.extend(torch.sigmoid(output.logits.squeeze(-1)).cpu().tolist())
    return [
        {**asdict(example), "probability": probability, "prediction": int(probability >= 0.5)}
        for example, probability in zip(examples, probabilities)
    ]


def save_prediction_rows(rows: list[dict[str, Any]], path: Path) -> None:
    """Save verifier probabilities and yes or no decisions as JSONL."""
    # Persist every evaluation prediction so ranking and threshold decisions are auditable.
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def load_examples(path: Path) -> list[VerifierExample]:
    """Load the labeled JSONL dataset produced during verifier training."""
    # Reconstruct the same examples without regenerating candidates or rerunning the sandbox.
    with path.open(encoding="utf-8") as handle:
        return [VerifierExample(**json.loads(line)) for line in handle if line.strip()]


def evaluate_verifier(model: nn.Module, loader: DataLoader, criterion: nn.Module, device: torch.device) -> dict[str, float]:
    """Evaluate verifier loss and classification metrics without updating weights."""
    # Accumulate predictions and labels across the complete evaluation split.
    model.eval()
    losses: list[float] = []
    logits: list[Tensor] = []
    labels: list[Tensor] = []
    task_ids: list[str] = []
    with torch.inference_mode():
        for batch in loader:
            batch = {key: value.to(device) if isinstance(value, Tensor) else value for key, value in batch.items()}
            output = model(**{key: value for key, value in batch.items() if key not in {"labels", "task_ids"}})
            losses.append(criterion(output.logits.squeeze(-1), batch["labels"]).item())
            logits.append(output.logits.squeeze(-1).cpu())
            labels.append(batch["labels"].cpu())
            task_ids.extend(batch["task_ids"])
    all_logits = torch.cat(logits)
    all_labels = torch.cat(labels)
    metrics = binary_metrics(all_logits, all_labels, task_ids)
    metrics["loss"] = sum(losses) / len(losses)
    return metrics


def prepare_verifier_data(config: dict[str, Any], force: bool = False) -> tuple[list[VerifierExample], list[VerifierExample]]:
    """Generate, sandbox-label, and immediately save task-disjoint train and evaluation data."""
    # Load and split MBPP before generation so no task appears in both labeled datasets.
    output_dir = Path(config["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)
    dataset = load_mbpp(config["dataset_name"], config.get("dataset_config"), config["split"])
    if config.get("max_examples"):
        dataset = dataset.select(range(min(int(config["max_examples"]), len(dataset))))
    train_records, validation_records = split_dataset(dataset, float(config["train_fraction"]), int(config["seed"]))
    prepared: list[list[VerifierExample]] = []
    for name, records in (("train", list(train_records)), ("validation", list(validation_records))):
        path = output_dir / f"{name}.jsonl"
        if path.exists() and not force:
            # Reuse the completed labels so later training retries never regenerate candidates.
            examples = load_examples(path)
            print(f"Reusing {len(examples)} labeled {name} examples from {path}.", flush=True)
        else:
            # Finish and persist one split before beginning the next split.
            examples = generate_candidates(records, config["generator_model"], int(config["candidates_per_task"]), float(config["temperature"]), float(config["top_p"]), int(config["max_new_tokens"]), int(config["generation_batch_size"]), int(config["label_workers"]))
            save_examples(examples, path)
            print(f"Saved {len(examples)} labeled {name} examples to {path}.", flush=True)
        prepared.append(examples)
    return prepared[0], prepared[1]


def train_verifier(config: dict[str, Any]) -> dict[str, float]:
    """Build data, train CodeBERT, log W&B metrics, and save the final verifier."""
    # Initialize deterministic behavior before loading any model or data.
    seed_everything(int(config["seed"]))
    output_dir = Path(config["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)
    # Reuse durable labels whenever available so training retries are cheap and reproducible.
    train_examples, validation_examples = prepare_verifier_data(config, force=bool(config.get("regenerate_data", False)))
    train_examples = generated_only(train_examples)
    validation_examples = generated_only(validation_examples)
    print(f"Using generated-only verifier data: {len(train_examples)} train and {len(validation_examples)} validation examples.", flush=True)

    # Load CodeBERT as an encoder with a single scalar classification head.
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(config["verifier_model"])
    model = AutoModelForSequenceClassification.from_pretrained(config["verifier_model"], num_labels=1, problem_type="single_label_classification")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    if not bool(config.get("unfreeze_encoder", False)):
        # Freeze CodeBERT so the small labeled set trains only a stable classification head.
        for parameter in model.base_model.parameters():
            parameter.requires_grad = False
    # Initialize the classification bias at the observed positive prior for better 0.5 threshold calibration.
    positive_prior = sum(example.label for example in train_examples) / len(train_examples)
    prior_bias = torch.logit(torch.tensor(positive_prior, device=device))
    if hasattr(model, "classifier") and hasattr(model.classifier, "out_proj"):
        with torch.no_grad():
            model.classifier.out_proj.bias.copy_(prior_bias.expand_as(model.classifier.out_proj.bias))
    train_loader = DataLoader(VerifierDataset(train_examples), batch_size=int(config["batch_size"]), shuffle=True, collate_fn=lambda batch: collate_examples(batch, tokenizer, int(config["max_length"])))
    validation_loader = DataLoader(VerifierDataset(validation_examples), batch_size=int(config["batch_size"]), shuffle=False, collate_fn=lambda batch: collate_examples(batch, tokenizer, int(config["max_length"])))
    # Weight positive examples so missed correct programs are penalized at the fixed 0.5 threshold.
    criterion = nn.BCEWithLogitsLoss(pos_weight=torch.tensor(float(config["positive_class_weight"]), device=device))
    optimizer = torch.optim.AdamW([parameter for parameter in model.parameters() if parameter.requires_grad], lr=float(config["learning_rate"]), weight_decay=float(config["weight_decay"]))

    # Start the W&B run before training so dataset and optimizer settings are attached to the experiment.
    import wandb

    wandb.init(project=config["wandb_project"], name=config.get("wandb_run_name"), config=config)
    final_metrics: dict[str, float] = {}
    quarter_steps = max(1, (len(train_loader) + 3) // 4)
    for epoch in range(1, int(config["epochs"]) + 1):
        # Optimize BCE over every labeled training candidate for one epoch.
        model.train()
        epoch_losses: list[float] = []
        for batch_index, batch in enumerate(train_loader, start=1):
            batch = {key: value.to(device) if isinstance(value, Tensor) else value for key, value in batch.items()}
            optimizer.zero_grad(set_to_none=True)
            output = model(**{key: value for key, value in batch.items() if key not in {"labels", "task_ids"}})
            loss = criterion(output.logits.squeeze(-1), batch["labels"])
            loss.backward()
            optimizer.step()
            epoch_losses.append(loss.item())
            is_quarter = batch_index % quarter_steps == 0 or batch_index == len(train_loader)
            if not is_quarter:
                continue
            # Evaluate both splits at each quarter of the current epoch across every configured threshold.
            train_metrics = evaluate_verifier(model, train_loader, criterion, device)
            validation_metrics = evaluate_verifier(model, validation_loader, criterion, device)
            global_step = (epoch - 1) * len(train_loader) + batch_index
            final_metrics = {f"train/{key}": value for key, value in train_metrics.items()}
            final_metrics.update({f"validation/{key}": value for key, value in validation_metrics.items()})
            final_metrics.update({f"eval/{key}": value for key, value in validation_metrics.items()})
            final_metrics["epoch"] = float(epoch)
            final_metrics["epoch_fraction"] = batch_index / len(train_loader)
            final_metrics["global_step"] = float(global_step)
            final_metrics["train/optimization_loss"] = sum(epoch_losses) / len(epoch_losses)
            wandb.log(final_metrics, step=global_step)
            print(json.dumps(final_metrics, sort_keys=True), flush=True)
            model.train()

    # Save the final continuously trained classifier and metric summary for downstream experiments.
    model.save_pretrained(output_dir / "model")
    tokenizer.save_pretrained(output_dir / "model")
    save_prediction_rows(prediction_rows(model, validation_examples, validation_loader, device), output_dir / "validation_predictions.jsonl")
    (output_dir / "metrics.json").write_text(json.dumps(final_metrics, indent=2) + "\n", encoding="utf-8")
    wandb.finish()
    return final_metrics


def evaluate_saved_verifier(config: dict[str, Any]) -> dict[str, float]:
    """Evaluate a saved CodeBERT verifier on previously sandbox-labeled examples."""
    # Load the exact labeled evaluation artifact produced alongside the checkpoint.
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    checkpoint = Path(config["checkpoint_dir"])
    examples = generated_only(load_examples(Path(config["evaluation_data"])))
    tokenizer = AutoTokenizer.from_pretrained(checkpoint)
    model = AutoModelForSequenceClassification.from_pretrained(checkpoint)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    loader = DataLoader(VerifierDataset(examples), batch_size=int(config["batch_size"]), shuffle=False, collate_fn=lambda batch: collate_examples(batch, tokenizer, int(config["max_length"])))
    metrics = evaluate_verifier(model, loader, nn.BCEWithLogitsLoss(), device)
    rows = prediction_rows(model, examples, loader, device)
    save_prediction_rows(rows, Path(config["output_dir"]) / "evaluation_predictions.jsonl")
    import wandb

    wandb.init(project=config["wandb_project"], name=config.get("wandb_run_name"), config=config)
    logged = {f"evaluation/{key}": value for key, value in metrics.items()}
    wandb.log(logged, step=0)
    print(json.dumps(logged, sort_keys=True), flush=True)
    wandb.finish()
    return metrics


def parse_args() -> dict[str, Any]:
    """Parse the command-line configuration for verifier training."""
    # Keep the first experiment small enough to iterate on a single GPU.
    parser = argparse.ArgumentParser(description="Train a CodeBERT MBPP correctness verifier.")
    parser.add_argument("--generator-model", default="Qwen/Qwen2.5-Coder-0.5B-Instruct")
    parser.add_argument("--verifier-model", default="microsoft/codebert-base")
    parser.add_argument("--dataset-name", default="google-research-datasets/mbpp")
    parser.add_argument("--dataset-config", default=None)
    parser.add_argument("--split", default="train")
    parser.add_argument("--output-dir", default="outputs/verifier-codebert")
    parser.add_argument("--candidates-per-task", type=int, default=4)
    parser.add_argument("--generation-batch-size", type=int, default=4)
    parser.add_argument("--label-workers", type=int, default=16)
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--top-p", type=float, default=0.95)
    parser.add_argument("--max-new-tokens", type=int, default=512)
    parser.add_argument("--train-fraction", type=float, default=0.8)
    parser.add_argument("--max-examples", type=int, default=None)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--max-length", type=int, default=512)
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--learning-rate", type=float, default=5e-6)
    parser.add_argument("--weight-decay", type=float, default=0.01)
    parser.add_argument("--positive-class-weight", type=float, default=1.5)
    parser.add_argument("--unfreeze-encoder", action="store_true", help="Fine-tune CodeBERT instead of using a frozen linear probe.")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--wandb-project", default="mbpp-verifier")
    parser.add_argument("--wandb-run-name", default=None)
    parser.add_argument("--eval-only", action="store_true", help="Evaluate a saved verifier without regenerating labels.")
    parser.add_argument("--checkpoint-dir", default=None, help="Saved verifier directory for --eval-only.")
    parser.add_argument("--evaluation-data", default=None, help="Labeled JSONL data for --eval-only.")
    parser.add_argument("--prepare-data", action="store_true", help="Generate and save labels, then exit before model training.")
    parser.add_argument("--regenerate-data", action="store_true", help="Regenerate labeled data instead of reusing saved JSONL.")
    return vars(parser.parse_args())


# Launch the verifier data construction and training flow when invoked as a script.
if __name__ == "__main__":
    # Select training or saved-checkpoint evaluation from the command line.
    arguments = parse_args()
    if arguments["prepare_data"]:
        prepare_verifier_data(arguments, force=arguments["regenerate_data"])
    elif arguments["eval_only"]:
        arguments["checkpoint_dir"] = arguments["checkpoint_dir"] or str(Path(arguments["output_dir"]) / "model")
        arguments["evaluation_data"] = arguments["evaluation_data"] or str(Path(arguments["output_dir"]) / "validation.jsonl")
        evaluate_saved_verifier(arguments)
    else:
        train_verifier(arguments)
