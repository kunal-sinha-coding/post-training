"""Train a small Qwen model to classify When2Call actions with clean validation.

The flow initializes W&B, loads only the cached When2Call training split, formats each row as a
four-way action prompt, trains either supervised, preference, or policy-gradient objectives, evaluates
the frozen model on a deterministic development split, and saves reproducible adapter artifacts.
"""
from __future__ import annotations

import argparse
import atexit
import json
import os
import random
import time
from dataclasses import dataclass
from pathlib import Path

import torch
from datasets import load_dataset
from peft import LoraConfig, PeftModel, get_peft_model
from transformers import AutoModelForCausalLM, AutoTokenizer

from experiments.train_when2call_jina import LABELS, LABEL_TO_ID, response_label, tools_text


DATASET_NAME = "nvidia/When2Call"
CACHE_PATH = Path("/workspace/.cache/huggingface/datasets/nvidia___when2_call/train_pref/0.0.0/0582f7749df63a96fdc3070932e83e72396ace53/when2_call-train.arrow")


@dataclass
class ClassificationRow:
    """Store one formatted classification prompt and its chosen and rejected labels."""

    prompt: str
    label: int
    rejected_label: int | None


def load_rows() -> object:
    """Load only the cached train preference split."""
    # Keep the official test split out of every Qwen training and validation run.
    if CACHE_PATH.exists():
        from datasets import Dataset
        return Dataset.from_file(str(CACHE_PATH))
    return load_dataset(DATASET_NAME, "train_pref", split="train")


def make_prompt(row: object) -> str:
    """Format one When2Call row as a stable four-way action prompt."""
    # Preserve the full question and tool schemas so Qwen can use the same evidence as the benchmark.
    user_text = "\n".join(message["content"] for message in row["messages"] if message["role"] == "user")
    return (
        "Classify the required assistant action. Return exactly one label: A, B, C, or D.\n"
        "A = direct answer.\n"
        "B = tool call.\n"
        "C = request for more information.\n"
        "D = cannot answer.\n\n"
        f"Question: {user_text}\nAvailable tools:\n{tools_text(row['tools'])}\nAction label:"
    )


def prepare_rows(rows: object) -> list[ClassificationRow]:
    """Convert chosen and rejected response text into action labels."""
    # Infer labels from training responses and retain rejected labels only for preference objectives.
    prepared = []
    for row in rows:
        chosen = LABEL_TO_ID[response_label(row["chosen_response"]["content"])]
        rejected = LABEL_TO_ID[response_label(row["rejected_response"]["content"])]
        prepared.append(ClassificationRow(make_prompt(row), chosen, rejected))
    return prepared


def split_rows(rows: list[ClassificationRow], seed: int) -> tuple[list[ClassificationRow], list[ClassificationRow]]:
    """Create a deterministic stratified training and development split."""
    # Stratify by inferred chosen label so macro F1 remains measurable on the development set.
    grouped = {label: [] for label in range(len(LABELS))}
    for row in rows:
        grouped[row.label].append(row)
    rng = random.Random(seed)
    train, development = [], []
    for label, items in grouped.items():
        rng.shuffle(items)
        count = max(1, round(len(items) * 0.2)) if items else 0
        development.extend(items[:count])
        train.extend(items[count:])
    rng.shuffle(train)
    rng.shuffle(development)
    return train, development


def load_model(model_name: str, device: torch.device, lora_rank: int, adapter_checkpoint: str | None = None) -> tuple[object, object]:
    """Load a Qwen causal model and attach or continue a LoRA adapter."""
    # Use bfloat16 and gradient checkpointing so the two-billion-parameter limit is also memory safe.
    dtype = torch.bfloat16 if device.type == "cuda" else torch.float32
    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=False)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(model_name, torch_dtype=dtype, trust_remote_code=False).to(device)
    model.config.use_cache = False
    model.gradient_checkpointing_enable()
    if adapter_checkpoint:
        # Continue training the saved preference adapter without replaying its training data.
        model = PeftModel.from_pretrained(model, adapter_checkpoint, is_trainable=True)
    elif lora_rank > 0:
        # Adapt attention and feed-forward projections while keeping the base model frozen.
        config = LoraConfig(r=lora_rank, lora_alpha=2 * lora_rank, lora_dropout=0.05, target_modules="all-linear", task_type="CAUSAL_LM")
        model = get_peft_model(model, config)
    return model, tokenizer


def label_token_ids(tokenizer: object) -> list[int]:
    """Return one tokenizer ID for each action label."""
    # Require single-token labels so the classification objective has one unambiguous action position.
    encoded = [tokenizer.encode(f" {letter}", add_special_tokens=False) for letter in "ABCD"]
    if any(len(tokens) != 1 for tokens in encoded):
        raise ValueError(f"Action labels are not single tokens: {encoded}")
    return [tokens[0] for tokens in encoded]


def score_rows(model: object, tokenizer: object, rows: list[ClassificationRow], label_ids: list[int], device: torch.device, max_length: int) -> torch.Tensor:
    """Return log probabilities for the four action labels."""
    # Read the next-token distribution at the end of each prompt and restrict it to the four actions.
    inputs = tokenizer([row.prompt for row in rows], return_tensors="pt", padding=True, truncation=True, max_length=max_length)
    inputs = {key: value.to(device) for key, value in inputs.items()}
    with torch.autocast(device_type="cuda", dtype=torch.bfloat16, enabled=device.type == "cuda"):
        logits = model(**inputs).logits
    positions = inputs["attention_mask"].sum(dim=1) - 1
    next_logits = logits[torch.arange(len(rows), device=device), positions][:, label_ids]
    return torch.log_softmax(next_logits.float(), dim=-1)


def reference_scores(model: object, tokenizer: object, rows: list[ClassificationRow], label_ids: list[int], device: torch.device, max_length: int) -> torch.Tensor:
    """Return frozen-base log probabilities for one batch."""
    # Disable only the trainable LoRA adapter so the base Qwen model remains the reference policy.
    if hasattr(model, "disable_adapter"):
        with model.disable_adapter():
            with torch.no_grad():
                return score_rows(model, tokenizer, rows, label_ids, device, max_length)
    with torch.no_grad():
        return score_rows(model, tokenizer, rows, label_ids, device, max_length)


def metrics(rows: list[ClassificationRow], predictions: list[int]) -> dict:
    """Compute accuracy, macro F1, and the four-class confusion matrix."""
    # Calculate all metrics locally without loading any official test labels.
    matrix = [[0 for _ in LABELS] for _ in LABELS]
    for row, prediction in zip(rows, predictions):
        matrix[row.label][prediction] += 1
    f1_values = []
    for label in range(len(LABELS)):
        tp = matrix[label][label]
        fp = sum(matrix[source][label] for source in range(len(LABELS)) if source != label)
        fn = sum(matrix[label][target] for target in range(len(LABELS)) if target != label)
        precision = tp / max(1, tp + fp)
        recall = tp / max(1, tp + fn)
        f1_values.append(2 * precision * recall / max(1e-12, precision + recall))
    return {"accuracy": sum(row.label == prediction for row, prediction in zip(rows, predictions)) / max(1, len(rows)), "macro_f1": sum(f1_values) / len(f1_values), "confusion_matrix": matrix, "examples": len(rows)}


def write_heartbeat(path: Path, phase: str, step: int = 0) -> None:
    """Write the current worker phase and progress."""
    # Use an atomic replacement so the watchdog never reads a partial heartbeat.
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps({"timestamp": time.time(), "phase": phase, "step": step}) + "\n", encoding="utf-8")
    temporary.replace(path)


def train_epoch(model: object, tokenizer: object, rows: list[ClassificationRow], label_ids: list[int], objective: str, device: torch.device, optimizer: object, max_length: int, batch_size: int, beta: float, seed: int, heartbeat_path: Path, step_callback: object | None = None, step_offset: int = 0) -> float:
    """Run one objective-specific training epoch and return mean loss."""
    # Shuffle only training rows and optimize the selected action objective in small memory-safe batches.
    model.train()
    order = list(rows)
    random.Random(seed).shuffle(order)
    losses = []
    for batch_index, start in enumerate(range(0, len(order), batch_size), start=1):
        write_heartbeat(heartbeat_path, "training", start)
        batch = order[start:start + batch_size]
        optimizer.zero_grad(set_to_none=True)
        log_probs = score_rows(model, tokenizer, batch, label_ids, device, max_length)
        chosen = torch.tensor([row.label for row in batch], device=device)
        if objective == "sft":
            loss = torch.nn.functional.nll_loss(log_probs, chosen)
        elif objective == "rpo":
            rejected = torch.tensor([row.rejected_label if row.rejected_label is not None else row.label for row in batch], device=device)
            valid = rejected != chosen
            if not valid.any():
                continue
            ref_probs = reference_scores(model, tokenizer, batch, label_ids, device, max_length)
            policy_margin = log_probs[valid, chosen[valid]] - log_probs[valid, rejected[valid]]
            reference_margin = ref_probs[valid, chosen[valid]] - ref_probs[valid, rejected[valid]]
            loss = -torch.nn.functional.logsigmoid(beta * (policy_margin - reference_margin)).mean()
        else:
            ref_probs = reference_scores(model, tokenizer, batch, label_ids, device, max_length)
            distribution = log_probs.exp()
            sampled = torch.multinomial(distribution, 1).squeeze(1)
            reward = (sampled == chosen).float() * 2.0 - 1.0
            reward = reward - beta * (log_probs[torch.arange(len(batch), device=device), sampled] - ref_probs[torch.arange(len(batch), device=device), sampled]).detach()
            loss = -(reward.detach() * log_probs[torch.arange(len(batch), device=device), sampled]).mean()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
        losses.append(float(loss.detach().cpu()))
        # Run the optional checkpoint callback after each completed optimizer update.
        if step_callback is not None:
            # Pass the optimizer loss so callers can record a live training curve.
            should_stop = step_callback(step_offset + batch_index, float(loss.detach().cpu()))
            model.train()
            if should_stop:
                break
    return sum(losses) / max(1, len(losses))


def evaluate(model: object, tokenizer: object, rows: list[ClassificationRow], label_ids: list[int], device: torch.device, max_length: int, batch_size: int, heartbeat_path: Path | None = None) -> dict:
    """Evaluate action predictions on one clean partition."""
    # Disable gradients and aggregate predictions across fixed batches.
    model.eval()
    predictions = []
    with torch.no_grad():
        for start in range(0, len(rows), batch_size):
            if heartbeat_path is not None:
                write_heartbeat(heartbeat_path, "evaluation", start)
            scores = score_rows(model, tokenizer, rows[start:start + batch_size], label_ids, device, max_length)
            predictions.extend(scores.argmax(dim=-1).cpu().tolist())
    return metrics(rows, predictions)


def main() -> int:
    """Run one W&B-logged Qwen clean-validation experiment."""
    # Parse the model, objective, and reproducibility controls before initializing W&B.
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="Qwen/Qwen2.5-0.5B-Instruct")
    parser.add_argument("--objective", choices=("sft", "rpo", "rl"), default="sft")
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/qwen-when2call-sft-05b"))
    parser.add_argument("--seed", type=int, default=20261022)
    parser.add_argument("--split-seed", type=int, default=20261022)
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--max-length", type=int, default=4096)
    parser.add_argument("--learning-rate", type=float, default=2e-5)
    parser.add_argument("--weight-decay", type=float, default=0.01)
    parser.add_argument("--beta", type=float, default=0.1)
    parser.add_argument("--lora-rank", type=int, default=16)
    args = parser.parse_args()
    # Require online W&B before any data or model operation as required by the research protocol.
    import wandb
    if not os.getenv("WANDB_API_KEY"):
        raise RuntimeError("WANDB_API_KEY is required for Qwen experiments.")
    # Include the unique output directory so separate launches never share a misleading W&B display name.
    run_name = f"qwen-when2call-{args.objective}-{Path(args.model).name}-{Path(args.output_dir).name}"
    run = wandb.init(project=os.getenv("WANDB_PROJECT", "when2call-research"), entity=os.getenv("WANDB_ENTITY"), name=run_name, job_type="qwen-when2call-clean-validation", config=vars(args))
    atexit.register(run.finish)
    # Fix all random sources before model construction and training.
    random.seed(args.seed)
    torch.manual_seed(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    heartbeat_path = args.output_dir / "heartbeat.json"
    write_heartbeat(heartbeat_path, "loading")
    # Load and split only inferred-label training rows after W&B initialization.
    train_rows, development_rows = split_rows(prepare_rows(load_rows()), args.split_seed)
    model, tokenizer = load_model(args.model, device, args.lora_rank)
    label_ids = label_token_ids(tokenizer)
    optimizer = torch.optim.AdamW((parameter for parameter in model.parameters() if parameter.requires_grad), lr=args.learning_rate, weight_decay=args.weight_decay)
    losses = []
    for epoch in range(args.epochs):
        losses.append(train_epoch(model, tokenizer, train_rows, label_ids, args.objective, device, optimizer, args.max_length, args.batch_size, args.beta, args.seed + epoch, heartbeat_path))
        train_metrics = evaluate(model, tokenizer, train_rows, label_ids, device, args.max_length, args.batch_size, heartbeat_path)
        development_metrics = evaluate(model, tokenizer, development_rows, label_ids, device, args.max_length, args.batch_size, heartbeat_path)
        run.log({"epoch": epoch + 1, "training/loss": losses[-1], "train/accuracy": train_metrics["accuracy"], "train/macro_f1": train_metrics["macro_f1"], "development/accuracy": development_metrics["accuracy"], "development/macro_f1": development_metrics["macro_f1"], "development/confusion_matrix": development_metrics["confusion_matrix"]})
    # Save the adapter and complete experiment metadata without touching official test data.
    args.output_dir.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(args.output_dir)
    tokenizer.save_pretrained(args.output_dir)
    # Convert path-valued arguments before writing JSON so a completed run cannot fail during bookkeeping.
    serializable_config = {key: str(value) if isinstance(value, Path) else value for key, value in vars(args).items()}
    metadata = {"model": args.model, "objective": args.objective, "dataset": DATASET_NAME, "official_test_loaded": False, "label_source": "inferred from chosen response content", "train_examples": len(train_rows), "development_examples": len(development_rows), "label_tokens": label_ids, "losses": losses, "train_metrics": train_metrics, "development_metrics": development_metrics, "config": serializable_config, "device": str(device), "wandb_run_id": run.id, "wandb_run_url": run.url}
    (args.output_dir / "metrics.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    write_heartbeat(heartbeat_path, "completed")
    run.summary.update({"development_accuracy": development_metrics["accuracy"], "development_macro_f1": development_metrics["macro_f1"], "output_dir": str(args.output_dir), "label_ids": label_ids})
    print(json.dumps(metadata, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
