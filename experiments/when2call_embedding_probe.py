"""Run a frozen Jina embedding probe for When2Call action classification.

The flow loads heuristic labels from train_pref or train_sft, loads the pretrained
Jina encoder, embeds complete question and tool contexts with masked mean pooling,
trains a small weighted linear classifier, and evaluates the classifier on MCQ.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import torch
from datasets import load_dataset
from transformers import AutoModel, AutoTokenizer

from experiments.train_when2call_jina import (
    DATASET_NAME,
    LABELS,
    JinaSequenceClassifier,
    LABEL_TO_ID,
    autocast_context,
    collate,
    infer_action_label,
    length_aware_batches,
    load_train_examples,
    prepare_test_examples,
    tokenize_examples,
    tools_text,
)


def build_test_texts(rows):
    """Build test examples from question and available-tool text."""
    # Keep the probe input identical to the classifier input while preserving official labels.
    return prepare_test_examples(rows)


def embed_examples(encoder, tokenizer, examples, device):
    """Embed complete examples with masked mean pooling."""
    # Run the frozen encoder in length-aware batches and return CPU feature tensors.
    tokenize_examples(examples, tokenizer)
    features = []
    encoder.eval()
    with torch.inference_mode():
        for items in length_aware_batches(examples, max_examples=4):
            batch = collate(items, tokenizer)
            batch.pop("labels")
            batch.pop("rejected_labels")
            batch.pop("source_ids")
            inputs = {key: value.to(device) for key, value in batch.items()}
            with autocast_context(device):
                hidden = encoder(**inputs).last_hidden_state
            mask = inputs["attention_mask"].unsqueeze(-1).to(hidden.dtype)
            pooled = (hidden * mask).sum(dim=1) / mask.sum(dim=1).clamp_min(1)
            features.append(pooled.float().cpu())
    return torch.cat(features)


def metric_dict(targets, predictions):
    """Compute accuracy and macro metrics over the three active test classes."""
    # Calculate explicit confusion counts so the output is independent of sklearn.
    active = list(range(3))
    matrix = [[0] * len(LABELS) for _ in LABELS]
    for target, prediction in zip(targets, predictions, strict=True):
        matrix[target][prediction] += 1
    scores = []
    for index in active:
        tp = matrix[index][index]
        predicted = sum(row[index] for row in matrix)
        support = sum(matrix[index])
        precision = tp / predicted if predicted else 0.0
        recall = tp / support if support else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        scores.append((precision, recall, f1))
    return {"accuracy": sum(a == b for a, b in zip(targets, predictions)) / len(targets), "macro_precision": sum(x[0] for x in scores) / 3, "macro_recall": sum(x[1] for x in scores) / 3, "macro_f1": sum(x[2] for x in scores) / 3}


def main():
    """Train the probe head and save its test metrics."""
    # Parse the experiment controls and establish a writable model cache.
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--dataset", choices=("train_pref", "train_sft", "combined"), default="train_pref")
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--lr", type=float, default=1e-2)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--pretrained", action="store_true")
    args = parser.parse_args()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    tokenizer = AutoTokenizer.from_pretrained(args.checkpoint, trust_remote_code=True)
    tokenizer.model_max_length = 8192
    encoder = AutoModel.from_pretrained("jinaai/jina-embeddings-v2-small-en", trust_remote_code=True)
    if not args.pretrained:
        state = torch.load(args.checkpoint / "model_state.pt", map_location="cpu")
        model = JinaSequenceClassifier(encoder, len(LABELS))
        model.load_state_dict(state)
        encoder = model.encoder
    encoder = encoder.to(device)
    train_examples = load_train_examples(args.dataset)
    test_examples = build_test_texts(load_dataset(DATASET_NAME, "test", split="mcq"))
    train_features = embed_examples(encoder, tokenizer, train_examples, device)
    test_features = embed_examples(encoder, tokenizer, test_examples, device)
    train_targets = torch.tensor([item.label for item in train_examples])
    test_targets = [item.label for item in test_examples]
    head = torch.nn.Linear(train_features.shape[1], len(LABELS))
    weights = torch.bincount(train_targets, minlength=len(LABELS)).float().reciprocal()
    weights = weights / weights.sum() * len(LABELS)
    optimizer = torch.optim.AdamW(head.parameters(), lr=args.lr)
    for _ in range(args.epochs):
        permutation = torch.randperm(len(train_features))
        for start in range(0, len(permutation), 256):
            indices = permutation[start:start + 256]
            loss = torch.nn.functional.cross_entropy(head(train_features[indices]), train_targets[indices], weight=weights)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
    predictions = head(test_features).argmax(dim=-1).tolist()
    result = {"dataset": args.dataset, "epochs": args.epochs, "lr": args.lr, "pretrained": args.pretrained, "metrics": metric_dict(test_targets, predictions)}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
