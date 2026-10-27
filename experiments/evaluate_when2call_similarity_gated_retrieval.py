"""Evaluate a similarity-gated retrieval fallback for the frozen When2Call Qwen model.

The flow samples clean train_sft validation data, embeds training and validation tool schemas,
uses label-free similarity quantiles to choose when to add demonstrations, scores Qwen, and
writes aggregate validation metrics without opening the official test split.
"""
from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

import numpy as np
import torch

from experiments import evaluate_when2call_dynamic_retrieval as retrieval
from experiments.train_qwen_when2call import ClassificationRow, label_token_ids, load_model, score_rows, write_heartbeat
from experiments.train_when2call_jina import LABELS, metric_values


def score_prompts(model: object, tokenizer: object, prompts: list[ClassificationRow], device: torch.device, batch_size: int, output_dir: Path, phase: str) -> list[int]:
    """Score prompts as one of the four learned action tokens."""
    # Run bounded inference batches and record the current validation position.
    predictions = []
    with torch.inference_mode():
        for start in range(0, len(prompts), batch_size):
            write_heartbeat(output_dir / "heartbeat.json", phase, start)
            logits = score_rows(model, tokenizer, prompts[start:start + batch_size], label_token_ids(tokenizer), device, 4096)
            predictions.extend(logits.argmax(-1).tolist())
    return predictions


def main() -> int:
    """Measure zero-shot, always-retrieve, and similarity-gated clean accuracy."""
    # Parse reproducibility and cache settings before loading training and validation rows.
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--split-seed", type=int, default=20270327)
    parser.add_argument("--sample-seed", type=int, default=20270332)
    parser.add_argument("--max-validation-examples", type=int, default=500)
    parser.add_argument("--qwen-checkpoint", default=retrieval.QWEN_CHECKPOINT)
    parser.add_argument("--embedding-model", default="text-embedding-3-small")
    parser.add_argument("--embedding-dimensions", type=int, default=1536)
    parser.add_argument("--cache-dir", type=Path, default=Path("outputs/when2call-openai-embedding-cache"))
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--gate-quantiles", type=float, nargs="+", default=[0.5, 0.75, 0.9])
    args = parser.parse_args()
    # Keep every clean-validation evaluation within the declared sample cap.
    if not 1 <= args.max_validation_examples <= 500:
        raise ValueError("Clean validation must use between 1 and 500 examples.")
    # Load local service credentials before creating API clients.
    from dotenv import load_dotenv
    load_dotenv(".env")
    if not os.getenv("WANDB_API_KEY") or not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("WANDB_API_KEY and OPENAI_API_KEY are required.")
    from openai import OpenAI
    import wandb
    run = wandb.init(project=os.getenv("WANDB_PROJECT", "when2call-research"), entity=os.getenv("WANDB_ENTITY"), name="when2call-similarity-gated-retrieval", job_type="clean-validation", config={"split_seed": args.split_seed, "sample_seed": args.sample_seed, "embedding_model": args.embedding_model, "embedding_dimensions": args.embedding_dimensions, "retrieval_pool": "train_sft", "retrieval_features": "tool schemas only", "k": 3, "gate_quantiles": args.gate_quantiles, "official_test_loaded": False})
    started = time.time()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_heartbeat(args.output_dir / "heartbeat.json", "load-clean-data")
    try:
        # Reuse the clean stratified split and remove all development questions from retrieval.
        train, validation, _ = retrieval.build_sampled_split(args)
        # Build cached embeddings using the same cache keys as the completed OpenAI screen.
        client = OpenAI()
        train_text = [retrieval.retrieval_text(row, "tools_only") for row in train]
        validation_text = [retrieval.retrieval_text(row, "tools_only") for row in validation]
        train_vectors, train_usage, train_cache = retrieval.load_or_create_embeddings(client, train_text, args.embedding_model, args.embedding_dimensions, "train_sft_tools_only", "training", args.cache_dir)
        validation_vectors, validation_usage, validation_cache = retrieval.load_or_create_embeddings(client, validation_text, args.embedding_model, args.embedding_dimensions, "tools_only", "validation", args.cache_dir)
        # Compute cosine scores and nearest three examples without reading validation labels.
        train_vectors = train_vectors / np.linalg.norm(train_vectors, axis=1, keepdims=True).clip(min=1e-12)
        validation_vectors = validation_vectors / np.linalg.norm(validation_vectors, axis=1, keepdims=True).clip(min=1e-12)
        similarities = validation_vectors @ train_vectors.T
        nearest = np.argsort(-similarities, axis=1)[:, :3]
        nearest_similarity = similarities.max(axis=1)
        thresholds = {str(q): float(np.quantile(nearest_similarity, q)) for q in args.gate_quantiles}
        # Load the frozen Qwen adapter after candidate retrieval rules are fixed.
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model, tokenizer = load_model(retrieval.QWEN_BASE, device, 16)
        model.load_adapter(args.qwen_checkpoint, adapter_name="frozen")
        model.set_adapter("frozen")
        model.eval()
        labels = [row.label for row in validation]
        zero_prompts = [ClassificationRow(retrieval.INSTRUCTION + row.text + "\nAction label:", row.label, None) for row in validation]
        zero_predictions = score_prompts(model, tokenizer, zero_prompts, device, args.batch_size, args.output_dir, "zero-shot")
        # Score the always-retrieve control and each label-free similarity gate.
        methods = {"zero_shot": zero_predictions}
        for key, gate in [("always_k3", None)] + [(f"gate_top_{q}", thresholds[str(q)]) for q in args.gate_quantiles]:
            prompts = []
            for index, target in enumerate(validation):
                use_demos = gate is None or nearest_similarity[index] >= gate
                demos = [train[int(row_index)] for row_index in nearest[index]] if use_demos else []
                prompt = retrieval.prompt_with_demos(tokenizer, target, demos, 4096, 160)
                prompts.append(ClassificationRow(prompt, target.label, None))
            methods[key] = score_prompts(model, tokenizer, prompts, device, args.batch_size, args.output_dir, key)
        # Save only aggregate clean metrics and the label-free gate thresholds.
        metrics = {name: {key: metric_values(labels, predictions, list(range(len(LABELS))))[key] for key in ("accuracy", "macro_f1")} for name, predictions in methods.items()}
        for name, values in metrics.items():
            run.log({f"validation/{name}/accuracy": values["accuracy"], f"validation/{name}/macro_f1": values["macro_f1"]})
        record = {"status": "completed", "training_performed": False, "official_test_loaded": False, "validation_source": "nvidia/When2Call train_sft", "validation_examples": len(validation), "qwen_checkpoint": args.qwen_checkpoint, "retrieval_pool": "train_sft", "retrieval_feature": "tool schemas only", "embedding_model": args.embedding_model, "embedding_dimensions": args.embedding_dimensions, "k": 3, "gate_quantiles": args.gate_quantiles, "gate_thresholds_from_unlabeled_validation_similarities": thresholds, "embedding_cache": {"training": train_cache, "validation": validation_cache}, "embedding_usage": {"training": train_usage, "validation": validation_usage}, "validation_metrics": metrics, "training_metrics_source": "outputs/qwen-when2call-fullpool-base-seed20261055/metrics.json", "aggregate_test_loaded": False, "git_commit": os.popen("git rev-parse HEAD").read().strip(), "wandb_run_id": run.id, "wandb_run_url": run.url, "runtime_seconds": time.time() - started}
        (args.output_dir / "metrics.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        run.summary.update({"status": "completed", "output_dir": str(args.output_dir)})
        write_heartbeat(args.output_dir / "heartbeat.json", "completed")
    except BaseException as error:
        run.summary.update({"status": "failed", "error": repr(error)})
        write_heartbeat(args.output_dir / "heartbeat.json", "failed")
        raise
    finally:
        run.finish()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
