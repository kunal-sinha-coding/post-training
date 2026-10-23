"""Train a response-aware When2Call candidate ranker and evaluate MCQ choices.

The flow turns each preference row into chosen and rejected question-response
pairs, fine-tunes a Jina encoder with a binary ranking head, scores every test
answer candidate, and reports the selected action metrics without using test
labels during selection.
"""
from __future__ import annotations

import argparse
import json
import random
from dataclasses import dataclass
from pathlib import Path

import torch
from datasets import load_dataset
from transformers import AutoModel, AutoTokenizer

from experiments.train_when2call_jina import DATASET_NAME, LABELS, LABEL_TO_ID, response_label, tools_text


@dataclass
class Pair:
    """Store one question and candidate response pair."""
    text: str
    label: int
    preference: int


def question_text(row):
    """Format a preference question with its available tools."""
    # Preserve the same user and tool context for all candidate responses.
    user = "\n".join(message["content"] for message in row["messages"] if message["role"] == "user")
    return f"Question: {user}\nAvailable tools:\n{tools_text(row['tools'])}"


def pair_text(context, response):
    """Append one candidate response to a question context."""
    # Make the response visible to the cross encoder while keeping delimiters stable.
    return f"{context}\nCandidate response:\n{response}"


def batch_encode(tokenizer, texts, device, max_length=8192):
    """Tokenize a batch with the full Jina context limit."""
    # Truncate only above the model limit so long tool schemas remain available.
    encoded = tokenizer(texts, padding=True, truncation=True, max_length=max_length, return_tensors="pt")
    return {key: value.to(device) for key, value in encoded.items()}


def metrics(targets, predictions):
    """Compute test accuracy and active-class macro metrics."""
    # Keep direct out of the macro denominator because it has no official test support.
    matrix = [[0] * 4 for _ in range(4)]
    for target, prediction in zip(targets, predictions, strict=True):
        matrix[target][prediction] += 1
    scores = []
    for index in range(3):
        tp = matrix[index][index]
        predicted = sum(row[index] for row in matrix)
        support = sum(matrix[index])
        precision = tp / predicted if predicted else 0.0
        recall = tp / support if support else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        scores.append((precision, recall, f1))
    return {"accuracy": sum(target == prediction for target, prediction in zip(targets, predictions, strict=True)) / len(targets), "macro_precision": sum(x[0] for x in scores) / 3, "macro_recall": sum(x[1] for x in scores) / 3, "macro_f1": sum(x[2] for x in scores) / 3}


def main():
    """Train the pairwise ranker and save test predictions and metrics."""
    # Parse the run controls and initialize the base Jina encoder.
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--encoder-model", default="jinaai/jina-embeddings-v2-small-en")
    parser.add_argument("--max-length", type=int, default=8192)
    parser.add_argument("--max-pairs", type=int, default=9000)
    parser.add_argument("--lr", type=float, default=2e-5)
    parser.add_argument("--weight-decay", type=float, default=0.01)
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--objective", choices=("binary", "multiclass", "joint"), default="multiclass")
    parser.add_argument("--aux-weight", type=float, default=0.5)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    random.seed(20261019)
    torch.manual_seed(20261019)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    tokenizer = AutoTokenizer.from_pretrained(args.encoder_model, trust_remote_code=True)
    tokenizer.model_max_length = 8192
    encoder = AutoModel.from_pretrained(args.encoder_model, trust_remote_code=True).to(device)
    head_size = 1 if args.objective == "binary" else len(LABELS) if args.objective == "multiclass" else len(LABELS) + 1
    head = torch.nn.Linear(encoder.config.hidden_size, head_size).to(device)
    rows = load_dataset(DATASET_NAME, "train_pref", split="train")
    pairs = []
    for row in rows:
        context = question_text(row)
        chosen = row["chosen_response"]["content"]
        rejected = row["rejected_response"]["content"]
        pairs.append(Pair(pair_text(context, chosen), 1 if args.objective == "binary" else LABEL_TO_ID[response_label(chosen)], 1))
        pairs.append(Pair(pair_text(context, rejected), 0 if args.objective == "binary" else LABEL_TO_ID[response_label(rejected)], 0))
    random.shuffle(pairs)
    pairs = pairs[: args.max_pairs * 2]
    optimizer = torch.optim.AdamW(list(encoder.parameters()) + list(head.parameters()), lr=args.lr, weight_decay=args.weight_decay)
    encoder.train()
    head.train()
    for _ in range(args.epochs):
        random.shuffle(pairs)
        for start in range(0, len(pairs), args.batch_size):
            batch = pairs[start:start + args.batch_size]
            inputs = batch_encode(tokenizer, [item.text for item in batch], device, args.max_length)
            hidden = encoder(**inputs).last_hidden_state
            mask = inputs["attention_mask"].unsqueeze(-1).to(hidden.dtype)
            pooled = (hidden * mask).sum(dim=1) / mask.sum(dim=1).clamp_min(1)
            logits = head(pooled.float())
            if args.objective == "binary":
                labels = torch.tensor([item.label for item in batch], dtype=torch.float32, device=device)
                loss = torch.nn.functional.binary_cross_entropy_with_logits(logits.squeeze(-1), labels)
            elif args.objective == "multiclass":
                labels = torch.tensor([item.label for item in batch], dtype=torch.long, device=device)
                loss = torch.nn.functional.cross_entropy(logits, labels)
            else:
                class_labels = torch.tensor([item.label for item in batch], dtype=torch.long, device=device)
                preference_labels = torch.tensor([item.preference for item in batch], dtype=torch.float32, device=device)
                loss = torch.nn.functional.cross_entropy(logits[:, :len(LABELS)], class_labels) + args.aux_weight * torch.nn.functional.binary_cross_entropy_with_logits(logits[:, -1], preference_labels)
            optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(list(encoder.parameters()) + list(head.parameters()), 1.0)
            optimizer.step()
    test_rows = load_dataset(DATASET_NAME, "test", split="mcq")
    encoder.eval()
    head.eval()
    predictions = []
    with torch.inference_mode():
        for row in test_rows:
            context = f"Question: {row['question']}\nAvailable tools:\n{tools_text(row['tools'])}"
            choices = list(row["answers"].items())
            scores = []
            for choice, response in choices:
                inputs = batch_encode(tokenizer, [pair_text(context, response)], device, args.max_length)
                hidden = encoder(**inputs).last_hidden_state
                mask = inputs["attention_mask"].unsqueeze(-1).to(hidden.dtype)
                pooled = (hidden * mask).sum(dim=1) / mask.sum(dim=1).clamp_min(1)
                logits = head(pooled.float()).squeeze(0)
                if args.objective == "binary":
                    scores.append(logits.squeeze().item())
                elif args.objective == "multiclass":
                    scores.append(logits[LABEL_TO_ID[choice]])
                else:
                    scores.append(logits[LABEL_TO_ID[choice]] + logits[-1])
            predictions.append(choices[max(range(len(scores)), key=scores.__getitem__)][0])
    targets = [row["correct_answer"] for row in test_rows]
    result = {"epochs": args.epochs, "max_pairs": args.max_pairs, "lr": args.lr, "weight_decay": args.weight_decay, "objective": args.objective, "encoder_model": args.encoder_model, "max_length": args.max_length, "metrics": metrics([LABEL_TO_ID[x] for x in targets], [LABEL_TO_ID[x] for x in predictions]), "predictions": predictions, "targets": targets}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in result.items() if key != "predictions" and key != "targets"}))


if __name__ == "__main__":
    main()
