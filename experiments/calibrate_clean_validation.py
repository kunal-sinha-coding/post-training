"""Calibrate the current When2Call validation leader without using development labels for fitting.

The flow rebuilds the deterministic training and development split, reserves part of training as
a calibration set, loads the saved argument cue checkpoint, fits class logit biases on calibration
examples, and measures the frozen rule on development examples only.
"""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

import torch
from transformers import AutoConfig, AutoModel, AutoTokenizer

from experiments.clean_validation_baseline import add_argument_cues, load_training_rows, split_examples
from experiments.train_when2call_jina import LABELS, JinaSequenceClassifier, autocast_context, collate, metric_values


def load_checkpoint(checkpoint: Path, device: torch.device) -> tuple[torch.nn.Module, object]:
    """Load the saved argument cue classifier and its local tokenizer."""
    # Rebuild the encoder from local configuration so calibration does not require a network call.
    tokenizer = AutoTokenizer.from_pretrained("outputs/when2call-jina-v2-small/latest", trust_remote_code=True)
    tokenizer.model_max_length = 8192
    config = AutoConfig.from_pretrained(checkpoint / "encoder_config.json", trust_remote_code=True)
    config._name_or_path = str(Path("outputs/when2call-jina-v2-small/latest").resolve())
    config.attn_implementation = "torch"
    encoder = AutoModel.from_config(config, trust_remote_code=True)
    model = JinaSequenceClassifier(encoder, len(LABELS))
    model.load_state_dict(torch.load(checkpoint / "model_state.pt", map_location="cpu"))
    return model.to(device), tokenizer


def collect_logits(model: torch.nn.Module, tokenizer: object, examples: list, device: torch.device) -> tuple[torch.Tensor, torch.Tensor]:
    """Collect logits and labels for one supplied split without changing model weights."""
    # Evaluate in length ordered batches to match the existing memory safe inference path.
    model.eval()
    logits, labels = [], []
    ordered = sorted(examples, key=lambda item: len(item.token_ids or []))
    with torch.inference_mode():
        for start in range(0, len(ordered), 16):
            batch = collate(ordered[start:start + 16], tokenizer)
            labels.append(batch.pop("labels"))
            batch.pop("rejected_labels")
            batch.pop("source_ids")
            inputs = {key: value.to(device) for key, value in batch.items()}
            with autocast_context(device):
                logits.append(model(**inputs).logits.float().cpu())
    return torch.cat(logits), torch.cat(labels)


def fit_bias(logits: torch.Tensor, labels: torch.Tensor) -> torch.Tensor:
    """Fit bounded coordinate class biases on the calibration partition."""
    # Search a small deterministic grid because calibration must remain cheap and reproducible.
    bias = torch.zeros(len(LABELS))
    grid = [-0.30, -0.20, -0.10, 0.0, 0.10, 0.20, 0.30]
    best = (float((logits + bias).argmax(dim=1).eq(labels).float().mean()), bias.clone())
    for _ in range(2):
        for class_id in range(len(LABELS)):
            for value in grid:
                candidate = bias.clone()
                candidate[class_id] = value
                score = float((logits + candidate).argmax(dim=1).eq(labels).float().mean())
                if score > best[0]:
                    best = (score, candidate)
                    bias = candidate
    return best[1]


def main() -> int:
    """Fit calibration on training data and evaluate it on the held out development split."""
    # Keep the split and checkpoint fixed to the current validation leader.
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", type=Path, default=Path("outputs/clean-validation-argument-cues-seed21"))
    parser.add_argument("--output", type=Path, default=Path("outputs/clean-validation-calibration.json"))
    args = parser.parse_args()
    seed = 20261021
    random.seed(seed)
    torch.manual_seed(seed)
    rows = load_training_rows()
    examples = split_examples(__import__("experiments.train_when2call_jina", fromlist=["prepare_train_examples"]).prepare_train_examples(rows), 0.2, seed)
    train, development = examples
    add_argument_cues(train)
    add_argument_cues(development)
    calibration = train[: len(train) // 10]
    remaining_train = train[len(train) // 10 :]
    tokenizer_model, tokenizer = load_checkpoint(args.checkpoint, torch.device("cuda" if torch.cuda.is_available() else "cpu"))
    for item in calibration + remaining_train + development:
        item.token_ids = tokenizer(item.text, add_special_tokens=True, truncation=False, verbose=False)["input_ids"]
    device = next(tokenizer_model.parameters()).device
    calibration_logits, calibration_labels = collect_logits(tokenizer_model, tokenizer, calibration, device)
    development_logits, development_labels = collect_logits(tokenizer_model, tokenizer, development, device)
    bias = fit_bias(calibration_logits, calibration_labels)
    predictions = (development_logits + bias).argmax(dim=1).tolist()
    metrics = metric_values(development_labels.tolist(), predictions, list(range(len(LABELS))))
    result = {"seed": seed, "calibration_examples": len(calibration), "development_examples": len(development), "bias": bias.tolist(), "calibration_accuracy": float((calibration_logits + bias).argmax(dim=1).eq(calibration_labels).float().mean()), "development_metrics": metrics, "test_loaded": False, "checkpoint": str(args.checkpoint)}
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
