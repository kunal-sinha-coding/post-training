"""Evaluate cached OpenAI retrieval pools and few-shot counts on clean When2Call validation.

The flow creates a clean SFT validation split, excludes its questions from SFT and preference
retrieval pools, caches OpenAI embeddings, scores Qwen with zero to three examples, and saves
validation metrics without loading official test rows.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import os
import random
import re
import subprocess
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import torch

from experiments.clean_validation_baseline import load_sft_training_rows, split_examples
from experiments.heterogeneous_when2call import artifact_digest
from experiments.train_qwen_when2call import (
    ClassificationRow,
    label_token_ids,
    load_model,
    score_rows,
    write_heartbeat,
    load_rows as load_preference_rows,
)
from experiments.train_when2call_jina import LABELS, metric_values, prepare_train_examples


QWEN_BASE = "Qwen/Qwen2.5-1.5B-Instruct"
QWEN_CHECKPOINT = "outputs/qwen-when2call-fullpool-base-seed20261055/epoch-02"
LABEL_TO_LETTER = {0: "A", 1: "B", 2: "C", 3: "D"}
INSTRUCTION = (
    "Classify the required assistant action. Return exactly one label: A, B, C, or D.\n"
    "A = cannot answer. B = request for more information. C = tool call. D = direct answer.\n\n"
)


def question_text(example: object) -> str:
    # Extract only the user question so one retrieval mode ignores tool schemas.
    return example.text.split("\nAvailable tools:\n", 1)[0]


def build_sampled_split(args: argparse.Namespace) -> tuple[list, list, set[str]]:
    # Create one clean split and cap its validation side with a fixed stratified sample.
    examples = prepare_train_examples(load_sft_training_rows())
    train, full_validation = split_examples(examples, 0.2, args.split_seed)
    full_held_questions = {" ".join(question_text(item).casefold().split()) for item in full_validation}
    grouped = {label: [] for label in range(len(LABELS))}
    # Group held-out rows by inferred label before applying the fixed sample cap.
    for example in full_validation:
        grouped[example.label].append(example)
    # Shuffle each class with one explicit seed so the capped validation sample is repeatable.
    rng = random.Random(args.sample_seed)
    # Randomize within each class before computing proportional sample quotas.
    for items in grouped.values():
        rng.shuffle(items)
    total = len(full_validation)
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
    # Remove all clean-development questions from training and every retrieval source.
    train = [item for item in train if " ".join(question_text(item).casefold().split()) not in full_held_questions]
    return train, validation, full_held_questions


def retrieval_tokens(text: str) -> list[str]:
    # Return lower-case word unigrams and adjacent-word bigrams for sparse retrieval.
    words = re.findall(r"[a-z0-9_]+", text.casefold())
    return words + [f"{left} {right}" for left, right in zip(words, words[1:])]


def retrieval_text(example: object, mode: str) -> str:
    # Build either a question-only document or a compact question and tool-feature document.
    question = question_text(example)
    if mode == "question_only":
        return question
    if mode == "tools_only":
        return example.text.partition("\nAvailable tools:\n")[2]
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


def retrieval_cache_key(train: list, mode: str) -> str:
    # Bind each retrieval cache to its mode, training texts, inferred labels, and row identifiers.
    digest = hashlib.sha256(mode.encode())
    for example in train:
        payload = f"\n{example.source_id}\t{example.label}\t{retrieval_text(example, mode)}"
        digest.update(payload.encode("utf-8"))
    return digest.hexdigest()


def load_or_build_index(train: list, mode: str, cache_path: Path) -> dict:
    # Reuse a compressed sparse TF-IDF index only when its training rows and feature mode match.
    cache_key = retrieval_cache_key(train, mode)
    if cache_path.exists():
        # Ignore a cache from any other train split or retrieval representation.
        with gzip.open(cache_path, "rt", encoding="utf-8") as stream:
            cached = json.load(stream)
        if cached.get("cache_key") == cache_key:
            return cached
    # Build document counts and inverse frequencies from the training partition only.
    documents = [Counter(retrieval_tokens(retrieval_text(item, mode))) for item in train]
    document_frequency = Counter()
    for counts in documents:
        document_frequency.update(counts.keys())
    inverse_frequency = {token: math.log((1 + len(documents)) / (1 + count)) + 1.0 for token, count in document_frequency.items()}
    postings = defaultdict(list)
    norms = [0.0] * len(documents)
    for document_index, counts in enumerate(documents):
        weighted = {token: (1 + math.log(frequency)) * inverse_frequency[token] for token, frequency in counts.items()}
        norms[document_index] = math.sqrt(sum(value * value for value in weighted.values()))
        for token, value in weighted.items():
            postings[token].append([document_index, value])
    index = {"cache_key": cache_key, "mode": mode, "inverse_frequency": inverse_frequency, "postings": dict(postings), "norms": norms}
    # Save the weighted sparse index so later runs on the same training split can reuse it.
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(cache_path, "wt", encoding="utf-8") as stream:
        json.dump(index, stream, separators=(",", ":"))
    return index


def retrieve(train: list, validation: list, mode: str, index: dict) -> list[list[int]]:
    # Rank validation rows by cosine similarity against a saved or newly built training index.
    inverse_frequency = index["inverse_frequency"]
    postings = index["postings"]
    norms = index["norms"]
    ranked_rows = []
    # Transform and rank each validation query without using its label.
    for example in validation:
        query_counts = Counter(retrieval_tokens(retrieval_text(example, mode)))
        query = {token: (1 + math.log(frequency)) * inverse_frequency[token] for token, frequency in query_counts.items() if token in inverse_frequency}
        query_norm = math.sqrt(sum(value * value for value in query.values())) or 1.0
        dot_products = defaultdict(float)
        for token, query_weight in query.items():
            for document_index, document_weight in postings.get(token, []):
                dot_products[document_index] += query_weight * document_weight
        ranked = sorted(dot_products.items(), key=lambda item: (-item[1] / (query_norm * norms[item[0]]) if norms[item[0]] else 0.0, item[0]))[:8]
        selected = [index for index, _ in ranked]
        # Fill zero-similarity slots with stable training rows for complete vote lists.
        if len(selected) < 8:
            selected_set = set(selected)
            selected.extend(index for index in range(len(train)) if index not in selected_set and len(selected) < 8)
        ranked_rows.append(selected)
    return ranked_rows


def embedding_text_digest(texts: list[str], model_name: str, mode: str, role: str) -> str:
    # Identify vectors by model, input representation, data role, and exact ordered text.
    digest = hashlib.sha256(f"{model_name}|{mode}|{role}|char-cap-24000-v1".encode())
    for text in texts:
        digest.update(len(text).to_bytes(8, "big"))
        digest.update(text.encode("utf-8"))
    return digest.hexdigest()


def load_or_create_embeddings(client: object, texts: list[str], model_name: str, dimensions: int, mode: str, role: str, cache_dir: Path) -> tuple[np.ndarray, dict, str]:
    # Reuse a cached OpenAI vector file only when its complete metadata key matches.
    bounded_texts = [text[:24000] for text in texts]
    digest = embedding_text_digest(bounded_texts, model_name, mode, role)
    cache_path = cache_dir / model_name.replace("/", "_") / f"d{dimensions}-{mode}-{role}-{digest[:24]}.npz"
    metadata = {"model": model_name, "dimensions": dimensions, "mode": mode, "role": role, "input_sha256": digest, "character_cap": 24000, "strategy_version": 1}
    if cache_path.exists():
        # Do not reuse vectors from another model or text representation.
        with np.load(cache_path, allow_pickle=False) as cached:
            saved_metadata = json.loads(str(cached["metadata"].item()))
            if saved_metadata == metadata:
                return cached["vectors"].astype(np.float32), {"cache_hit": True, "api_calls": 0, "input_tokens": 0, "embedding_count": len(texts)}, str(cache_path)
    # Request vectors in fixed-size batches and preserve the API response order.
    vectors = []
    api_calls = 0
    input_tokens = 0
    for start in range(0, len(bounded_texts), 64):
        batch = bounded_texts[start:start + 64]
        response = None
        # Retry transient errors up to two times after the initial request.
        for attempt in range(3):
            try:
                response = client.embeddings.create(model=model_name, input=batch, dimensions=dimensions)
                break
            except Exception:
                if attempt == 2:
                    raise
                time.sleep(2 ** attempt)
        api_calls += 1
        input_tokens += int(getattr(response.usage, "prompt_tokens", 0) or 0)
        vectors.extend(item.embedding for item in sorted(response.data, key=lambda item: item.index))
    array = np.asarray(vectors, dtype=np.float32)
    # Write the compressed vectors atomically with metadata for future cache validation.
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = cache_path.with_suffix(".tmp.npz")
    np.savez_compressed(temporary, vectors=array, metadata=json.dumps(metadata, sort_keys=True))
    temporary.replace(cache_path)
    return array, {"cache_hit": False, "api_calls": api_calls, "input_tokens": input_tokens, "embedding_count": len(texts)}, str(cache_path)


def dense_neighbors(train_vectors: np.ndarray, validation_vectors: np.ndarray, count: int = 8) -> list[list[int]]:
    # Rank OpenAI vectors by cosine similarity and return stable top neighbors.
    train_norms = np.linalg.norm(train_vectors, axis=1, keepdims=True).clip(min=1e-12)
    validation_norms = np.linalg.norm(validation_vectors, axis=1, keepdims=True).clip(min=1e-12)
    similarities = (validation_vectors / validation_norms) @ (train_vectors / train_norms).T
    return np.argsort(-similarities, axis=1)[:, :count].tolist()


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
    # Run the OpenAI-only retrieval screen and save clean-validation evidence.
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--split-seed", type=int, default=20270327)
    parser.add_argument("--sample-seed", type=int, default=20270332)
    parser.add_argument("--max-validation-examples", type=int, default=500)
    parser.add_argument("--qwen-checkpoint", default=QWEN_CHECKPOINT)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--max-length", type=int, default=4096)
    parser.add_argument("--per-demo-tokens", type=int, default=160)
    parser.add_argument("--cache-dir", type=Path, default=Path("outputs/when2call-openai-embedding-cache"))
    parser.add_argument("--embedding-model", default="text-embedding-3-small")
    parser.add_argument("--embedding-dimensions", type=int, default=1536)
    args = parser.parse_args()
    # Enforce the project sample cap before loading validation data.
    if not 1 <= args.max_validation_examples <= 500:
        raise ValueError("Clean validation must use between 1 and 500 examples.")
    # Load local credentials before initializing W&B or OpenAI clients.
    from dotenv import load_dotenv
    load_dotenv(".env")
    # Require both service credentials before starting an API-backed evaluation.
    if not os.getenv("WANDB_API_KEY") or not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("WANDB_API_KEY and OPENAI_API_KEY are required.")
    from openai import OpenAI
    import wandb
    run = wandb.init(
        project=os.getenv("WANDB_PROJECT", "when2call-research"),
        entity=os.getenv("WANDB_ENTITY"),
        name="when2call-openai-retrieval-clean-validation",
        job_type="clean-validation",
        config={"split_seed": args.split_seed, "sample_seed": args.sample_seed, "max_validation_examples": args.max_validation_examples, "qwen_checkpoint": args.qwen_checkpoint, "retrieval_pools": ["train_sft", "train_pref", "train_pref_plus_train_sft"], "retrieval_features": ["question_only", "tools_only", "question_and_tools"], "few_shot_k": [1, 2, 3], "embedding_model": args.embedding_model, "embedding_dimensions": args.embedding_dimensions, "official_test_loaded": False},
    )
    started = time.time()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_heartbeat(args.output_dir / "heartbeat.json", "openai-retrieval-validation")
    try:
        train_sft, validation, held_questions = build_sampled_split(args)
        # Exclude every clean-development question from each retrieval source.
        pref_rows = prepare_train_examples(load_preference_rows())
        clean = lambda rows: [row for row in rows if " ".join(question_text(row).casefold().split()) not in held_questions]
        train_sft = clean(train_sft)
        train_pref = clean(pref_rows)
        # Build a preference-first union and keep one row per normalized question.
        union = list(train_pref)
        union_questions = {" ".join(question_text(row).casefold().split()) for row in union}
        for row in train_sft:
            # Add only the first SFT row for a question that is absent from preference data.
            normalized = " ".join(question_text(row).casefold().split())
            if normalized not in union_questions:
                union.append(row)
                union_questions.add(normalized)
        pools = {"train_sft": train_sft, "train_pref": train_pref, "train_pref_plus_train_sft": union}
        labels = [row.label for row in validation]
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model, tokenizer = load_model(QWEN_BASE, device, 16)
        if not hasattr(model, "load_adapter"):
            raise TypeError("The Qwen model did not load as a PEFT model.")
        model.load_adapter(args.qwen_checkpoint, adapter_name="frozen")
        model.set_adapter("frozen")
        model.eval()
        client = OpenAI()
        results = {}
        cache_files = {}
        usage = {}
        neighbors = {}
        # Embed each training pool and input representation with a persistent, metadata-keyed cache.
        for pool_name, pool in pools.items():
            for feature in ("question_only", "tools_only", "question_and_tools"):
                mode = f"{pool_name}_{feature}"
                train_texts = [retrieval_text(row, feature) for row in pool]
                validation_texts = [retrieval_text(row, feature) for row in validation]
                train_vectors, train_usage, train_cache = load_or_create_embeddings(client, train_texts, args.embedding_model, args.embedding_dimensions, mode, "training", args.cache_dir)
                validation_vectors, validation_usage, validation_cache = load_or_create_embeddings(client, validation_texts, args.embedding_model, args.embedding_dimensions, feature, "validation", args.cache_dir)
                neighbors[mode] = dense_neighbors(train_vectors, validation_vectors, count=5)
                cache_files[mode] = {"training": train_cache, "validation": validation_cache}
                usage[mode] = {"training": train_usage, "validation": validation_usage}
                # Record direct retrieved-label votes as diagnostics separate from few-shot prompting.
                for vote_k in (1, 3, 5):
                    predictions = knn_predictions(pool, neighbors[mode], vote_k)
                    metrics = metric_values(labels, predictions, list(range(len(LABELS))))
                    results[f"{mode}_label_vote_{vote_k}"] = {key: metrics[key] for key in ("accuracy", "macro_f1")}
                    run.log({f"validation/{mode}/label_vote_{vote_k}/accuracy": metrics["accuracy"], f"validation/{mode}/label_vote_{vote_k}/macro_f1": metrics["macro_f1"]})
                # Score one, two, and three retrieved demonstrations for this source and feature mode.
                for shots in (1, 2, 3):
                    prompts = []
                    for target, indices in zip(validation, neighbors[mode]):
                        demos = [pool[index] for index in indices[:shots]]
                        prompts.append(ClassificationRow(prompt_with_demos(tokenizer, target, demos, args.max_length, args.per_demo_tokens), target.label, None))
                    predictions = []
                    with torch.inference_mode():
                        for start_index in range(0, len(prompts), args.batch_size):
                            write_heartbeat(args.output_dir / "heartbeat.json", f"qwen-{mode}-{shots}shot", start_index)
                            logits = score_rows(model, tokenizer, prompts[start_index:start_index + args.batch_size], label_token_ids(tokenizer), device, args.max_length)
                            predictions.extend(logits.argmax(-1).tolist())
                    metrics = metric_values(labels, predictions, list(range(len(LABELS))))
                    results[f"{mode}_qwen_{shots}shot"] = {key: metrics[key] for key in ("accuracy", "macro_f1")}
                    run.log({f"validation/{mode}/qwen_{shots}shot/accuracy": metrics["accuracy"], f"validation/{mode}/qwen_{shots}shot/macro_f1": metrics["macro_f1"]})
        # Measure the corrected zero-shot baseline once on the identical clean-validation rows.
        prompts = [ClassificationRow(INSTRUCTION + row.text + "\nAction label:", row.label, None) for row in validation]
        predictions = []
        with torch.inference_mode():
            for start_index in range(0, len(prompts), args.batch_size):
                logits = score_rows(model, tokenizer, prompts[start_index:start_index + args.batch_size], label_token_ids(tokenizer), device, args.max_length)
                predictions.extend(logits.argmax(-1).tolist())
        metrics = metric_values(labels, predictions, list(range(len(LABELS))))
        results["qwen_zero_shot_corrected_mapping"] = {key: metrics[key] for key in ("accuracy", "macro_f1")}
        run.log({"validation/qwen_zero_shot_corrected_mapping/accuracy": metrics["accuracy"], "validation/qwen_zero_shot_corrected_mapping/macro_f1": metrics["macro_f1"]})
        record = {"status": "completed", "training_performed": False, "official_test_loaded": False, "validation_source": "nvidia/When2Call train_sft", "validation_examples": len(validation), "retrieval_pool_sizes": {name: len(pool) for name, pool in pools.items()}, "all_clean_development_questions_excluded_from_retrieval": True, "union_policy": "train_pref precedence, then unique train_sft questions", "split_seed": args.split_seed, "sample_seed": args.sample_seed, "retrieval_features": ["question only", "tool schemas only", "question and tool schemas"], "retrieval_algorithm": "OpenAI cosine similarity", "embedding_model": args.embedding_model, "embedding_dimensions": args.embedding_dimensions, "embedding_cache": cache_files, "embedding_cache_usage": usage, "few_shot_k": [1, 2, 3], "label_vote_k": [1, 3, 5], "label_mapping": {"A": "cannot_answer", "B": "request_for_info", "C": "tool_call", "D": "direct"}, "qwen_checkpoint": args.qwen_checkpoint, "validation_metrics": results, "git_commit": subprocess.check_output(["git", "-c", "safe.directory=/workspace/post-training", "rev-parse", "HEAD"], text=True).strip(), "wandb_run_id": run.id, "wandb_run_url": run.url, "runtime_seconds": time.time() - started}
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
