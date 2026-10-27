"""Evaluate nearest-neighbor and retrieved-example prompting on clean When2Call validation.

The flow loads only train_sft, makes a stratified train and validation split, builds
TF-IDF indexes from training rows, retrieves examples for each validation row, evaluates
label voting and Qwen few-shot prompts, and saves aggregate validation metrics only.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random
import re
import subprocess
import time
from collections import Counter, defaultdict
from pathlib import Path

import torch

from experiments.clean_validation_baseline import load_sft_training_rows, split_examples
from experiments.heterogeneous_when2call import artifact_digest
from experiments.train_qwen_when2call import (
    ClassificationRow,
    label_token_ids,
    load_model,
    score_rows,
    write_heartbeat,
)
from experiments.train_when2call_jina import LABELS, metric_values, prepare_train_examples


QWEN_BASE = "Qwen/Qwen2.5-1.5B-Instruct"
QWEN_CHECKPOINT = "outputs/qwen-when2call-fullpool-base-seed20261055/epoch-02"
LABEL_TO_LETTER = {0: "D", 1: "C", 2: "B", 3: "A"}
INSTRUCTION = (
    "Classify the required assistant action. Return exactly one label: A, B, C, or D.\n"
    "A = direct answer. B = tool call. C = request for more information. D = cannot answer.\n\n"
)


def question_text(example: object) -> str:
    # Extract only the user question so one retrieval mode ignores tool schemas.
    return example.text.split("\nAvailable tools:\n", 1)[0]


def build_sampled_split(args: argparse.Namespace) -> tuple[list, list]:
    # Create one clean split and cap its validation side with a fixed stratified sample.
    examples = prepare_train_examples(load_sft_training_rows())
    train, validation = split_examples(examples, 0.2, args.split_seed)
    grouped = {label: [] for label in range(len(LABELS))}
    # Group held-out rows by inferred label before applying the fixed sample cap.
    for example in validation:
        grouped[example.label].append(example)
    # Shuffle each class with one explicit seed so the capped validation sample is repeatable.
    rng = random.Random(args.sample_seed)
    # Randomize within each class before computing proportional sample quotas.
    for items in grouped.values():
        rng.shuffle(items)
    total = len(validation)
    quotas = {label: len(items) * args.max_validation_examples / total for label, items in grouped.items()}
    counts = {label: min(len(grouped[label]), int(quotas[label])) for label in grouped}
    # Distribute leftover slots by the largest fractional quota.
    for label in sorted(grouped, key=lambda value: quotas[value] - counts[value], reverse=True):
        # Stop once the configured validation cap is full.
        if sum(counts.values()) >= args.max_validation_examples:
            break
        # Add one row to a class while it still has unused examples.
        if counts[label] < len(grouped[label]):
            counts[label] += 1
    # Restore a seeded mixed order after class-wise sampling.
    validation = [example for label in grouped for example in grouped[label][:counts[label]]]
    rng.shuffle(validation)
    # Remove exact normalized question matches so retrieval cannot copy a duplicate validation row.
    held_questions = {" ".join(question_text(item).casefold().split()) for item in validation}
    train = [item for item in train if " ".join(question_text(item).casefold().split()) not in held_questions]
    return train, validation


def retrieval_tokens(text: str) -> list[str]:
    # Return lower-case word unigrams and adjacent-word bigrams for sparse retrieval.
    words = re.findall(r"[a-z0-9_]+", text.casefold())
    return words + [f"{left} {right}" for left, right in zip(words, words[1:])]


def retrieval_text(example: object, mode: str) -> str:
    # Build either a question-only document or a compact question and tool-feature document.
    question = question_text(example)
    if mode == "question_only":
        return question
    tool_lines = example.text.partition("\nAvailable tools:\n")[2].splitlines()
    tool_features = []
    for line in tool_lines:
        try:
            schema = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(schema, dict):
            function = schema.get("function", schema)
            if not isinstance(function, dict):
                continue
            tool_features.extend([str(function.get("name", "")), str(function.get("description", ""))])
            parameters = function.get("parameters", {})
            properties = parameters.get("properties", {}) if isinstance(parameters, dict) else {}
            if isinstance(properties, dict):
                tool_features.extend(map(str, properties.keys()))
    return question + "\n" + " ".join(tool_features)


def retrieve(train: list, validation: list, mode: str) -> list[list[int]]:
    # Rank training examples by sparse TF-IDF cosine similarity without external packages.
    documents = [Counter(retrieval_tokens(retrieval_text(item, mode))) for item in train]
    document_frequency = Counter()
    for counts in documents:
        document_frequency.update(counts.keys())
    inverse_frequency = {token: math.log((1 + len(documents)) / (1 + count)) + 1.0 for token, count in document_frequency.items()}
    postings = defaultdict(list)
    norms = [0.0] * len(documents)
    for document_index, counts in enumerate(documents):
        weighted = {token: (1 + math.log(frequency)) * inverse_frequency[token] for token, frequency in counts.items() if token in inverse_frequency}
        norms[document_index] = math.sqrt(sum(value * value for value in weighted.values()))
        for token, value in weighted.items():
            postings[token].append((document_index, value))
    ranked_rows = []
    # Rank each validation row against the training-only sparse index.
    for example in validation:
        query_counts = Counter(retrieval_tokens(retrieval_text(example, mode)))
        query = {token: (1 + math.log(frequency)) * inverse_frequency[token] for token, frequency in query_counts.items() if token in inverse_frequency}
        query_norm = math.sqrt(sum(value * value for value in query.values())) or 1.0
        dot_products = defaultdict(float)
        for token, query_weight in query.items():
            for document_index, document_weight in postings[token]:
                dot_products[document_index] += query_weight * document_weight
        ranked = sorted(dot_products.items(), key=lambda item: (-item[1] / (query_norm * norms[item[0]]) if norms[item[0]] else 0.0, item[0]))[:8]
        selected = [index for index, _ in ranked]
        # Fill empty-similarity slots with stable training indices for complete vote lists.
        if len(selected) < 8:
            selected_set = set(selected)
            selected.extend(index for index in range(len(train)) if index not in selected_set and len(selected) < 8)
        ranked_rows.append(selected)
    return ranked_rows


def knn_predictions(train: list, neighbors: list[list[int]], k: int) -> list[int]:
    # Vote among the top k retrieved labels and break ties by the nearest example.
    predictions = []
    # Use label counts first and the nearest neighbor to resolve tied vote totals.
    for indices in neighbors:
        selected = indices[:k]
        counts = Counter(train[index].label for index in selected)
        predictions.append(max(range(len(LABELS)), key=lambda label: (counts[label], -next((rank for rank, index in enumerate(selected) if train[index].label == label), k))))
    return predictions


def prompt_with_demos(tokenizer: object, target: object, demos: list, max_length: int, per_demo_tokens: int) -> str:
    # Fit retrieved examples before the target while reserving the context budget for the target.
    target_prompt = INSTRUCTION + target.text + "\nAction label:"
    target_count = len(tokenizer.encode(target_prompt, add_special_tokens=False))
    available = max(0, max_length - target_count - 8)
    if not demos or available < 64 * len(demos):
        return target_prompt
    each_limit = min(per_demo_tokens, (available - 48 * len(demos)) // len(demos))
    rendered = []
    # Keep each demonstration short so the validation target remains inside the model context.
    for index, demo in enumerate(demos, 1):
        tokens = tokenizer.encode(demo.text, add_special_tokens=False)[:each_limit]
        excerpt = tokenizer.decode(tokens, skip_special_tokens=True)
        rendered.append(f"Example {index}:\n{excerpt}\nAction label: {LABEL_TO_LETTER[demo.label]}\n")
    prefix = "Use these labeled examples as guidance.\n\n" + "\n".join(rendered) + "\nNow classify this example.\n"
    return prefix + target_prompt


def main() -> int:
    # Run the declared clean retrieval comparison and save model and data provenance.
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--split-seed", type=int, default=20270327)
    parser.add_argument("--sample-seed", type=int, default=20270328)
    parser.add_argument("--max-validation-examples", type=int, default=500)
    parser.add_argument("--qwen-checkpoint", default=QWEN_CHECKPOINT)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--max-length", type=int, default=4096)
    parser.add_argument("--per-demo-tokens", type=int, default=160)
    args = parser.parse_args()
    # Enforce the project sample cap before loading validation data.
    if not 1 <= args.max_validation_examples <= 500:
        raise ValueError("Clean validation must use between 1 and 500 examples.")
    # Require W&B so every experiment has a durable metric trace.
    if not os.getenv("WANDB_API_KEY"):
        raise RuntimeError("WANDB_API_KEY is required for validation experiments.")
    import wandb
    run = wandb.init(
        project=os.getenv("WANDB_PROJECT", "when2call-research"),
        entity=os.getenv("WANDB_ENTITY"),
        name="when2call-dynamic-retrieval-clean-validation",
        job_type="clean-validation",
        config={"split_seed": args.split_seed, "sample_seed": args.sample_seed, "max_validation_examples": args.max_validation_examples, "qwen_checkpoint": args.qwen_checkpoint, "retrieval_pool": "train_sft split training partition", "retrieval_methods": ["question_only_tfidf", "question_and_tools_tfidf"], "official_test_loaded": False},
    )
    started = time.time()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_heartbeat(args.output_dir / "heartbeat.json", "retrieval-validation")
    try:
        train, validation = build_sampled_split(args)
        labels = [item.label for item in validation]
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model, tokenizer = load_model(QWEN_BASE, device, 16)
        if not hasattr(model, "load_adapter"):
            raise TypeError("The Qwen model did not load as a PEFT model.")
        model.load_adapter(args.qwen_checkpoint, adapter_name="frozen")
        model.set_adapter("frozen")
        model.eval()
        results = {}
        neighbor_sets = {}
        # Compare retrieval features with and without the available tool schemas.
        # Compare retrieval features with and without the available tool schemas.
        for mode in ("question_only", "question_and_tools"):
            indices = retrieve(train, validation, mode)
            neighbor_sets[mode] = indices
            # Measure majority-label voting at three neighborhood sizes.
            # Measure majority-label voting at three neighborhood sizes.
            for k in (1, 3, 5):
                predictions = knn_predictions(train, indices, k)
                metrics = metric_values(labels, predictions, list(range(len(LABELS))))
                results[f"{mode}_knn_{k}"] = {key: metrics[key] for key in ("accuracy", "macro_f1")}
                run.log({f"validation/{mode}_knn_{k}/accuracy": metrics["accuracy"], f"validation/{mode}_knn_{k}/macro_f1": metrics["macro_f1"]})
        # Compare one-shot and three-shot prompting for both retrieval representations.
        for mode in ("question_only", "question_and_tools"):
            # Build each prompt with neighbors selected only from the training partition.
            for shots in (1, 3):
                prompts = []
                for target, indices in zip(validation, neighbor_sets[mode]):
                    demos = [train[index] for index in indices[:shots]]
                    prompt = prompt_with_demos(tokenizer, target, demos, args.max_length, args.per_demo_tokens)
                    prompts.append(ClassificationRow(prompt, target.label, None))
                predictions = []
                # Score one batch at a time to keep inference memory bounded.
                with torch.inference_mode():
                    for start in range(0, len(prompts), args.batch_size):
                        write_heartbeat(args.output_dir / "heartbeat.json", f"qwen-{mode}-{shots}shot", start)
                        logits = score_rows(model, tokenizer, prompts[start:start + args.batch_size], label_token_ids(tokenizer), device, args.max_length)
                        predictions.extend(logits.argmax(-1).tolist())
                metrics = metric_values(labels, predictions, list(range(len(LABELS))))
                results[f"{mode}_qwen_{shots}shot"] = {key: metrics[key] for key in ("accuracy", "macro_f1")}
                run.log({f"validation/{mode}_{shots}shot/accuracy": metrics["accuracy"], f"validation/{mode}_{shots}shot/macro_f1": metrics["macro_f1"]})
        # Measure zero-shot Qwen once so retrieval prompts have a same-run reference.
        zero_shot = [ClassificationRow(INSTRUCTION + item.text + "\nAction label:", item.label, None) for item in validation]
        predictions = []
        with torch.inference_mode():
            for start in range(0, len(zero_shot), args.batch_size):
                write_heartbeat(args.output_dir / "heartbeat.json", "qwen-zero-shot", start)
                logits = score_rows(model, tokenizer, zero_shot[start:start + args.batch_size], label_token_ids(tokenizer), device, args.max_length)
                predictions.extend(logits.argmax(-1).tolist())
        metrics = metric_values(labels, predictions, list(range(len(LABELS))))
        results["qwen_zero_shot"] = {key: metrics[key] for key in ("accuracy", "macro_f1")}
        run.log({"validation/qwen_zero_shot/accuracy": metrics["accuracy"], "validation/qwen_zero_shot/macro_f1": metrics["macro_f1"]})
        record = {
            "status": "completed", "training_performed": False, "official_test_loaded": False,
            "validation_source": "nvidia/When2Call train_sft", "validation_examples": len(validation),
            "retrieval_training_examples": len(train), "exact_question_duplicates_excluded": True,
            "split_seed": args.split_seed, "sample_seed": args.sample_seed,
            "retrieval_features": ["question only", "question and tool schemas"],
            "retrieval_algorithm": "word unigram and bigram TF-IDF cosine similarity",
            "few_shot_settings": [1, 3], "per_demo_token_cap": args.per_demo_tokens,
            "qwen_checkpoint": args.qwen_checkpoint,
            "qwen_adapter_sha256": artifact_digest(Path(args.qwen_checkpoint) / "adapter_model.safetensors"),
            "validation_metrics": results,
            "git_commit": subprocess.check_output(["git", "-c", "safe.directory=/workspace/post-training", "rev-parse", "HEAD"], text=True).strip(),
            "wandb_run_id": run.id, "wandb_run_url": run.url, "runtime_seconds": time.time() - started,
        }
        (args.output_dir / "metrics.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        run.summary.update({"status": "completed", "validation_examples": len(validation), "output_dir": str(args.output_dir)})
        write_heartbeat(args.output_dir / "heartbeat.json", "completed")
        print(json.dumps({"validation_examples": len(validation), "metrics": results}, indent=2))
    except BaseException as error:
        run.summary.update({"status": "failed", "error": repr(error)})
        write_heartbeat(args.output_dir / "heartbeat.json", "failed")
        raise
    finally:
        run.finish()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
