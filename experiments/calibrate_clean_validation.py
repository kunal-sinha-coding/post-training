"""Calibrate the current When2Call validation leader without using development labels for fitting.

The flow rebuilds the deterministic training and development split, reserves part of training as
a calibration set, loads the saved argument cue checkpoint, fits class logit biases on calibration
examples, and measures the frozen rule on development examples only.
"""
from __future__ import annotations

import argparse
import atexit
import json
import os
import random
from pathlib import Path

import torch
from transformers import AutoConfig, AutoModel, AutoTokenizer

from experiments.clean_validation_baseline import add_argument_cues, load_training_rows, split_examples
from experiments.train_when2call_jina import LABELS, JinaSequenceClassifier, autocast_context, collate, metric_values
import experiments.train_when2call_jina as jina_training


def load_checkpoint(checkpoint: Path, device: torch.device, max_length: int) -> tuple[torch.nn.Module, object]:
    """Load the saved argument cue classifier and its local tokenizer."""
    # Rebuild the encoder from local configuration so calibration does not require a network call.
    tokenizer = AutoTokenizer.from_pretrained("outputs/when2call-jina-v2-small/latest", trust_remote_code=True)
    tokenizer.model_max_length = max_length
    # Load the saved JSON directly because the artifact uses encoder_config.json instead of config.json.
    config = AutoConfig.from_dict(json.loads((checkpoint / "encoder_config.json").read_text(encoding="utf-8")))
    config._name_or_path = str(Path("outputs/when2call-jina-v2-small/latest").resolve())
    config.attn_implementation = "torch"
    encoder = AutoModel.from_config(config, trust_remote_code=True)
    model = JinaSequenceClassifier(encoder, len(LABELS))
    model.load_state_dict(torch.load(checkpoint / "model_state.pt", map_location="cpu"))
    return model.to(device), tokenizer


def collect_logits(model: torch.nn.Module, tokenizer: object, examples: list, device: torch.device, batch_size: int = 16) -> tuple[torch.Tensor, torch.Tensor]:
    """Collect logits and labels for one supplied split without changing model weights."""
    # Evaluate in length ordered batches to match the existing memory safe inference path.
    model.eval()
    logits, labels = [], []
    ordered = sorted(examples, key=lambda item: len(item.token_ids or []))
    with torch.inference_mode():
        for start in range(0, len(ordered), batch_size):
            batch = collate(ordered[start:start + batch_size], tokenizer)
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
    parser.add_argument("--checkpoint", type=Path, default=Path("outputs/clean-validation-fixedsplit-seed22-len4096"))
    parser.add_argument("--output", type=Path, default=Path("outputs/clean-validation-calibration.json"))
    parser.add_argument("--seed", type=int, default=20261022)
    parser.add_argument("--split-seed", type=int, default=20261021)
    parser.add_argument("--calibration-fraction", type=float, default=0.1)
    parser.add_argument("--max-length", type=int, default=4096)
    args = parser.parse_args()
    # Open a W&B run before data loading so calibration failures and metrics are tracked.
    import wandb

    if not os.getenv("WANDB_API_KEY"):
        raise RuntimeError("WANDB_API_KEY is required for clean validation calibration.")
    run = wandb.init(
        project=os.getenv("WANDB_PROJECT", "when2call-research"),
        entity=os.getenv("WANDB_ENTITY"),
        name=f"clean-calibration-seed{args.seed}-split{args.split_seed}-len{args.max_length}",
        job_type="clean-validation-calibration",
        config=vars(args),
    )
    atexit.register(run.finish)
    seed = args.seed
    random.seed(seed)
    torch.manual_seed(seed)
    rows = load_training_rows()
    examples = split_examples(__import__("experiments.train_when2call_jina", fromlist=["prepare_train_examples"]).prepare_train_examples(rows), 0.2, args.split_seed)
    train, development = examples
    add_argument_cues(train)
    add_argument_cues(development)
    calibration_count = max(1, round(len(train) * args.calibration_fraction))
    calibration = train[:calibration_count]
    remaining_train = train[calibration_count:]
    # Apply the selected context limit to the shared validation collation path.
    jina_training.MAX_LENGTH = args.max_length
    tokenizer_model, tokenizer = load_checkpoint(args.checkpoint, torch.device("cuda" if torch.cuda.is_available() else "cpu"), args.max_length)
    for item in calibration + remaining_train + development:
        item.token_ids = tokenizer(item.text, add_special_tokens=True, truncation=False, verbose=False)["input_ids"]
    device = next(tokenizer_model.parameters()).device
    calibration_logits, calibration_labels = collect_logits(tokenizer_model, tokenizer, calibration, device)
    development_logits, development_labels = collect_logits(tokenizer_model, tokenizer, development, device)
    bias = fit_bias(calibration_logits, calibration_labels)
    predictions = (development_logits + bias).argmax(dim=1).tolist()
    metrics = metric_values(development_labels.tolist(), predictions, list(range(len(LABELS))))
    result = {"seed": seed, "split_seed": args.split_seed, "max_length": args.max_length, "calibration_fraction": args.calibration_fraction, "calibration_examples": len(calibration), "development_examples": len(development), "bias": bias.tolist(), "calibration_accuracy": float((calibration_logits + bias).argmax(dim=1).eq(calibration_labels).float().mean()), "development_metrics": metrics, "test_loaded": False, "checkpoint": str(args.checkpoint), "wandb_run_id": run.id, "wandb_run_url": run.url}
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    # Log the fitted bias and the frozen development measurement to W&B.
    run.log({"calibration/accuracy": result["calibration_accuracy"], "development/accuracy": metrics["accuracy"], "development/macro_f1": metrics["macro_f1"]})
    run.summary.update({"development_accuracy": metrics["accuracy"], "development_macro_f1": metrics["macro_f1"], "bias": bias.tolist()})
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
