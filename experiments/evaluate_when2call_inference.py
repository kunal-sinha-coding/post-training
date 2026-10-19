"""Evaluate a saved Jina classifier with stochastic votes and Jev comparisons.

The script loads the best local checkpoint, samples classifier predictions with
dropout enabled, computes majority and coverage metrics for several vote counts,
and asks Jev for one four-way action choice per test example.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any

import torch
from datasets import load_dataset
from dotenv import load_dotenv

from experiments.train_when2call_jina import (
    DATASET_NAME,
    LABELS,
    LABEL_TO_ID,
    JinaSequenceClassifier,
    autocast_context,
    collate,
    length_aware_batches,
    metric_values,
    prepare_test_examples,
    tokenize_examples,
)
from transformers import AutoConfig, AutoModel, AutoTokenizer


def load_classifier(checkpoint: Path) -> tuple[Any, Any, torch.device]:
    """Load the encoder, classifier head, and tokenizer from one checkpoint."""
    # Recreate the same long-context model architecture used during training.
    tokenizer = AutoTokenizer.from_pretrained(checkpoint, trust_remote_code=True)
    tokenizer.model_max_length = 8192
    config = AutoConfig.from_pretrained(checkpoint / "encoder_config.json", trust_remote_code=True)
    config.attn_implementation = "torch"
    encoder = AutoModel.from_pretrained("jinaai/jina-embeddings-v2-small-en", config=config, trust_remote_code=True)
    model = JinaSequenceClassifier(encoder, len(LABELS))
    model.load_state_dict(torch.load(checkpoint / "model_state.pt", map_location="cpu"))
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    return model, tokenizer, device


def predict_once(model: Any, tokenizer: Any, examples: list[Any], device: torch.device, stochastic: bool, seed: int) -> list[int]:
    """Predict one class per test example with optional dropout sampling."""
    # Enable dropout only for repeated-vote sampling while keeping gradients disabled.
    torch.manual_seed(seed)
    model.train(stochastic)
    predictions: list[int] = []
    with torch.inference_mode():
        for items in length_aware_batches(examples):
            batch = collate(items, tokenizer)
            batch.pop("labels")
            batch.pop("rejected_labels")
            batch.pop("source_ids")
            inputs = {key: value.to(device) for key, value in batch.items()}
            with autocast_context(device):
                predictions.extend(model(**inputs).logits.argmax(dim=-1).cpu().tolist())
    return predictions


def majority_metrics(votes: list[list[int]], targets: list[int]) -> dict[str, Any]:
    """Compute majority metrics and accuracy at least once among the votes."""
    # Use the lowest class ID as a deterministic tie break for equal vote counts.
    majority = [Counter(sample[index] for sample in votes).most_common(1)[0][0] for index in range(len(targets))]
    metrics = metric_values(targets, majority, list(range(len(LABELS))))
    coverage = sum(target in [sample[index] for sample in votes] for index, target in enumerate(targets)) / len(targets)
    metrics["accuracy_at_k"] = coverage
    return metrics


def jev_choice(state: str, api_key: str) -> str:
    """Ask Jev for one of the four When2Call action categories."""
    # Request a typed four-way choice using the same state shown to Jina.
    payload = {
        "model": "jev-latest",
        "state": state,
        "questions": {"action": {"type": "choice", "instructions": "Choose the single correct next action for this user question and available tools.", "criteria": {label: label for label in LABELS}}},
    }
    request = urllib.request.Request("https://api.typesafe.ai/v1/systemone", data=json.dumps(payload).encode(), headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(request, timeout=60) as response:
        result = json.loads(response.read())
    answer = result["answers"]["action"]
    choice = answer.get("choice", answer.get("label", answer.get("noul")))
    if isinstance(choice, dict):
        choice = choice.get("label")
    if str(choice) not in LABEL_TO_ID:
        raise ValueError(f"Jev returned unsupported choice: {choice!r}")
    return str(choice)


def main() -> int:
    """Run vote aggregation, Jev comparison, and save all inference artifacts."""
    # Parse the selected checkpoint and output location.
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=16)
    args = parser.parse_args()
    load_dotenv(".env")
    test_examples = prepare_test_examples(load_dataset(DATASET_NAME, "test", split="mcq"))
    model, tokenizer, device = load_classifier(args.checkpoint)
    tokenize_examples(test_examples, tokenizer)
    targets = [example.label for example in test_examples]
    all_votes = [predict_once(model, tokenizer, test_examples, device, True, 20261019 + index) for index in range(10)]
    result = {str(k): majority_metrics(all_votes[:k], targets) for k in (2, 3, 5, 10)}
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "majority_metrics.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    api_key = os.getenv("JEV_API_KEY")
    if not api_key:
        raise RuntimeError("JEV_API_KEY is missing from .env.")
    states = [example.text for example in test_examples]
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        jev_labels = list(executor.map(lambda state: jev_choice(state, api_key), states))
    jina_labels = all_votes[0]
    disagreements = []
    predictions = []
    for index, (jina_label, jev_label, target) in enumerate(zip(jina_labels, jev_labels, targets, strict=True)):
        row = {"row_index": index, "jina": LABELS[jina_label], "jev": jev_label, "correct": LABELS[target], "agreement": jina_label == LABEL_TO_ID[jev_label], "state": states[index]}
        predictions.append(row)
        if not row["agreement"]:
            disagreements.append(row)
    consensus = [jev_label if jina_label != LABEL_TO_ID[jev_label] else LABELS[jina_label] for jina_label, jev_label in zip(jina_labels, jev_labels, strict=True)]
    report = {"jina_jev_disagreements": len(disagreements), "jina_jev_agreements": len(targets) - len(disagreements), "jina_accuracy": sum(pred == target for pred, target in zip(jina_labels, targets, strict=True)) / len(targets), "jev_accuracy": sum(LABEL_TO_ID[pred] == target for pred, target in zip(jev_labels, targets, strict=True)) / len(targets), "consensus_accuracy": sum(LABEL_TO_ID[pred] == target for pred, target in zip(consensus, targets, strict=True)) / len(targets)}
    (args.output_dir / "jev_comparison.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    with (args.output_dir / "predictions.jsonl").open("w", encoding="utf-8") as handle:
        for row in predictions:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    with (args.output_dir / "disagreements.jsonl").open("w", encoding="utf-8") as handle:
        for row in disagreements:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
