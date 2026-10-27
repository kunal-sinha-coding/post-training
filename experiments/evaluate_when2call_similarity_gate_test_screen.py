"""Screen a clean-selected retrieval gate on a bounded black-box test sample.

The flow selects a fixed gate from clean-validation metrics, samples test row indices without labels,
embeds test inputs, and reports aggregate metrics with an optional full-test follow-up.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import re
import time
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import torch

from experiments import evaluate_when2call_dynamic_retrieval as retrieval
from experiments.evaluate_when2call_similarity_gated_retrieval import build_retrieval_pool
from experiments.evaluate_qwen_when2call_test import aggregate_metrics, load_official_rows
from experiments.train_qwen_when2call import label_token_ids, load_model, score_rows, write_heartbeat
from experiments.train_when2call_jina import LABEL_TO_ID, tools_text


def sample_test_rows(rows: object, limit: int, seed: int) -> list[tuple[int, object]]:
    """Choose a uniform sample without reading any test labels."""
    # Sample row indices only so selection cannot depend on ground truth.
    rng = random.Random(seed)
    count = min(limit, len(rows))
    indices = sorted(rng.sample(range(len(rows)), count))
    return [(index, rows[index]) for index in indices]


def make_examples(indexed_rows: list[tuple[int, object]]) -> tuple[list, list[int]]:
    """Format model inputs and keep labels only for aggregate scoring."""
    # Store each label beside its input without writing any row-level result.
    examples = []
    labels = []
    for index, row in indexed_rows:
        text = f"Question: {row['question']}\nAvailable tools:\n{tools_text(row['tools'])}"
        label = LABEL_TO_ID[str(row["correct_answer"])]
        examples.append(SimpleNamespace(text=text, label=label, source_id=f"test-{index}"))
        labels.append(label)
    return examples, labels


def score_method(model: object, tokenizer: object, prompts: list, device: torch.device, batch_size: int, output_dir: Path, phase: str, return_probabilities: bool = False) -> list[int] | np.ndarray:
    """Score prompts and retain predictions only until aggregate reduction."""
    # Run bounded inference batches and write only a progress heartbeat.
    predictions = []
    with torch.inference_mode():
        for start in range(0, len(prompts), batch_size):
            write_heartbeat(output_dir / "heartbeat.json", phase, start)
            logits = score_rows(model, tokenizer, prompts[start:start + batch_size], label_token_ids(tokenizer), device, 4096)
            # Retain normalized class probabilities only when the fusion experiment requests them.
            batch_output = torch.softmax(logits.float(), dim=-1) if return_probabilities else logits.argmax(-1)
            predictions.extend(batch_output.cpu().tolist())
    return np.asarray(predictions) if return_probabilities else predictions


def prompts_for_gate(tokenizer: object, examples: list, train: list, vectors: np.ndarray, train_vectors: np.ndarray, zero_predictions: list[int], threshold: float, gate_score: str, k: int, label_consensus_gate: bool, label_disagreement_fallback_k1: bool, require_neighbor_match_zero_shot: bool) -> tuple[list, np.ndarray]:
    """Apply the frozen cosine threshold and construct zero-shot and gated prompts."""
    # Rank examples with the selected cached input representation and preserve top-three neighbors.
    train_norms = np.linalg.norm(train_vectors, axis=1, keepdims=True).clip(min=1e-12)
    example_norms = np.linalg.norm(vectors, axis=1, keepdims=True).clip(min=1e-12)
    similarities = (vectors / example_norms) @ (train_vectors / train_norms).T
    neighbors = np.argsort(-similarities, axis=1)[:, :3]
    ranked_similarities = np.sort(similarities, axis=1)
    nearest = ranked_similarities[:, -1]
    scores = nearest if gate_score == "absolute" else nearest - ranked_similarities[:, -2]
    # Build prompts from the same clean-selected score threshold used by validation.
    prompts = []
    for index, target in enumerate(examples):
        selected_neighbors = neighbors[index, :k]
        use_demos = scores[index] >= threshold
        # Check whether the nearest labeled demonstrations agree before applying the fallback rule.
        labels_agree = len({train[int(row_index)].label for row_index in selected_neighbors}) == 1
        if label_consensus_gate and not labels_agree:
            use_demos = False
        # Keep only the nearest demonstration when the top two labels conflict.
        if label_disagreement_fallback_k1 and not labels_agree:
            selected_neighbors = selected_neighbors[:1]
        # Fall back to zero-shot when the closest training label conflicts with the Qwen prediction.
        if require_neighbor_match_zero_shot and train[int(selected_neighbors[0])].label != zero_predictions[index]:
            use_demos = False
        demos = [train[int(row_index)] for row_index in selected_neighbors] if use_demos else []
        prompt = retrieval.prompt_with_demos(tokenizer, target, demos, 4096, 160)
        prompts.append(retrieval.ClassificationRow(prompt, target.label, None))
    return prompts, scores


def main() -> int:
    """Measure a clean-selected gate on a sample and expand to full test when it passes."""
    # Parse the immutable checkpoint, sample, and clean-validation evidence locations.
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--clean-metrics", type=Path, required=True)
    parser.add_argument("--sample-seed", type=int, default=20270350)
    parser.add_argument("--max-test-examples", type=int, default=500)
    parser.add_argument("--split-seed", type=int, default=20270327)
    parser.add_argument("--validation-sample-seed", type=int, default=20270332)
    parser.add_argument("--qwen-checkpoint", default=retrieval.QWEN_CHECKPOINT)
    parser.add_argument("--embedding-model", default="text-embedding-3-small")
    parser.add_argument("--embedding-dimensions", type=int, default=1536)
    parser.add_argument("--cache-dir", type=Path, default=Path("outputs/when2call-openai-embedding-cache"))
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--feature", choices=("question_only", "tools_only", "question_and_tools"), default="tools_only")
    parser.add_argument("--force-screen", action="store_true")
    parser.add_argument("--label-consensus-gate", action="store_true")
    parser.add_argument("--label-disagreement-fallback-k1", action="store_true")
    parser.add_argument("--require-neighbor-match-zero-shot", action="store_true")
    parser.add_argument("--probability-average", action="store_true")
    args = parser.parse_args()
    # Enforce the black-box screening cap before opening any official test rows.
    if not 1 <= args.max_test_examples <= 500:
        raise ValueError("Black-box screening must use between 1 and 500 examples.")
    # Load service credentials before creating API clients.
    from dotenv import load_dotenv
    load_dotenv(".env")
    if not os.getenv("WANDB_API_KEY") or not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("WANDB_API_KEY and OPENAI_API_KEY are required.")
    from openai import OpenAI
    import wandb
    # Select the gate by clean-validation accuracy, with macro F1 as a tie breaker.
    clean = json.loads(args.clean_metrics.read_text(encoding="utf-8"))
    validation_metrics = clean["validation_metrics"]
    gate_score = clean.get("gate_score", "absolute")
    gate_prefix = "gate_top_" if gate_score == "absolute" else "margin_gate_top_"
    gate_key = max((key for key in validation_metrics if key.startswith(gate_prefix)), key=lambda key: (validation_metrics[key]["accuracy"], validation_metrics[key]["macro_f1"]))
    quantile = gate_key.removeprefix(gate_prefix).split("_k", 1)[0]
    k = int(clean.get("k", 3))
    threshold_key = "gate_thresholds_from_unlabeled_validation_similarities" if gate_score == "absolute" else "gate_thresholds_from_unlabeled_validation_scores"
    threshold = clean[threshold_key][quantile]
    weight_match = re.search(r"_w([0-9.]+)$", gate_key)
    retrieval_weight = float(weight_match.group(1)) if weight_match else 0.5
    selected_clean = validation_metrics[gate_key]
    baseline_clean = validation_metrics["zero_shot"]
    # Register the test-only measurement before opening official test rows or model weights.
    run = wandb.init(project=os.getenv("WANDB_PROJECT", "when2call-research"), entity=os.getenv("WANDB_ENTITY"), name="when2call-similarity-gate-test-screen", job_type="black-box-test-screen", config={"qwen_checkpoint": args.qwen_checkpoint, "retrieval_pool": clean.get("retrieval_pool", "train_sft"), "clean_selected_method": gate_key, "clean_gate_threshold": threshold, "retrieval_feature": args.feature, "gate_score": gate_score, "k": k, "force_screen": args.force_screen, "label_consensus_gate": args.label_consensus_gate, "label_disagreement_fallback_k1": args.label_disagreement_fallback_k1, "require_neighbor_match_zero_shot": args.require_neighbor_match_zero_shot, "probability_average": args.probability_average, "retrieval_weight": retrieval_weight, "sample_seed": args.sample_seed, "max_test_examples": args.max_test_examples, "test_labels_used_for_selection": False, "black_box": True})
    started = time.time()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_heartbeat(args.output_dir / "heartbeat.json", "clean-candidate-check")
    try:
        # Skip test access if clean validation does not favor a gate over zero-shot accuracy.
        if selected_clean["accuracy"] <= baseline_clean["accuracy"] and not args.force_screen:
            result = {"status": "skipped", "reason": "No similarity gate improved clean-validation accuracy over zero-shot.", "official_test_loaded": False, "clean_metrics_source": str(args.clean_metrics), "selected_method": gate_key, "clean_validation_metrics": {"zero_shot": baseline_clean, gate_key: selected_clean}}
            (args.output_dir / "metrics.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
            write_heartbeat(args.output_dir / "heartbeat.json", "skipped")
            return 0
        # Recreate the clean split and retrieve only from its training partition.
        split_args = SimpleNamespace(split_seed=args.split_seed, sample_seed=args.validation_sample_seed, max_validation_examples=500)
        train, _ = build_retrieval_pool(split_args, clean.get("retrieval_pool", "train_sft"))
        client = OpenAI()
        train_text = [retrieval.retrieval_text(row, args.feature) for row in train]
        train_vectors, train_usage, train_cache = retrieval.load_or_create_embeddings(client, train_text, args.embedding_model, args.embedding_dimensions, clean.get("retrieval_pool", "train_sft") + "_" + args.feature, "training", args.cache_dir)
        # Sample the official test set uniformly by row index, without label-dependent sampling.
        write_heartbeat(args.output_dir / "heartbeat.json", "load-test-sample")
        official_rows = load_official_rows()
        sampled = sample_test_rows(official_rows, args.max_test_examples, args.sample_seed)
        sample_examples, sample_labels = make_examples(sampled)
        sample_text = [retrieval.retrieval_text(row, args.feature) for row in sample_examples]
        sample_vectors, sample_usage, sample_cache = retrieval.load_or_create_embeddings(client, sample_text, args.embedding_model, args.embedding_dimensions, args.feature, "test_sample", args.cache_dir)
        # Load the frozen Qwen adapter only after the selected method and sample are fixed.
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model, tokenizer = load_model(retrieval.QWEN_BASE, device, 16)
        model.load_adapter(args.qwen_checkpoint, adapter_name="frozen")
        model.set_adapter("frozen")
        model.eval()
        # Score zero-shot and the clean-selected gate on the same hidden-label sample.
        zero_prompts = [retrieval.ClassificationRow(retrieval.INSTRUCTION + row.text + "\nAction label:", row.label, None) for row in sample_examples]
        zero_output = score_method(model, tokenizer, zero_prompts, device, args.batch_size, args.output_dir, "sample-zero-shot", args.probability_average)
        zero_probabilities = zero_output if args.probability_average else None
        zero_predictions = zero_output.argmax(-1).tolist() if args.probability_average else zero_output
        gate_prompts, _ = prompts_for_gate(tokenizer, sample_examples, train, sample_vectors, train_vectors, zero_predictions, threshold, gate_score, k, args.label_consensus_gate, args.label_disagreement_fallback_k1, args.require_neighbor_match_zero_shot)
        # Average frozen zero-shot and retrieval probabilities when testing probability fusion.
        if args.probability_average:
            gate_probabilities = score_method(model, tokenizer, gate_prompts, device, args.batch_size, args.output_dir, "sample-gated", True)
            gate_predictions = ((1 - retrieval_weight) * zero_probabilities + retrieval_weight * gate_probabilities).argmax(-1).tolist()
        else:
            gate_predictions = score_method(model, tokenizer, gate_prompts, device, args.batch_size, args.output_dir, "sample-gated")
        sample_metrics = {"zero_shot": aggregate_metrics(sample_labels, zero_predictions), gate_key: aggregate_metrics(sample_labels, gate_predictions)}
        run.log({f"test_sample/{name}/{metric}": value for name, values in sample_metrics.items() for metric, value in values.items()})
        full_metrics = None
        full_cache = None
        full_usage = None
        full_count = 0
        # Run full evaluation only when the gate beats zero-shot accuracy on the fixed sample.
        if sample_metrics[gate_key]["accuracy"] > sample_metrics["zero_shot"]["accuracy"]:
            full_examples, full_labels = make_examples(list(enumerate(official_rows)))
            full_text = [retrieval.retrieval_text(row, args.feature) for row in full_examples]
            full_vectors, full_usage, full_cache = retrieval.load_or_create_embeddings(client, full_text, args.embedding_model, args.embedding_dimensions, args.feature, "test_full", args.cache_dir)
            full_zero_prompts = [retrieval.ClassificationRow(retrieval.INSTRUCTION + row.text + "\nAction label:", row.label, None) for row in full_examples]
            full_zero_output = score_method(model, tokenizer, full_zero_prompts, device, args.batch_size, args.output_dir, "full-zero-shot", args.probability_average)
            full_zero_probabilities = full_zero_output if args.probability_average else None
            full_zero_predictions = full_zero_output.argmax(-1).tolist() if args.probability_average else full_zero_output
            full_gate_prompts, _ = prompts_for_gate(tokenizer, full_examples, train, full_vectors, train_vectors, full_zero_predictions, threshold, gate_score, k, args.label_consensus_gate, args.label_disagreement_fallback_k1, args.require_neighbor_match_zero_shot)
            # Average frozen zero-shot and retrieval probabilities when testing probability fusion.
            if args.probability_average:
                full_gate_probabilities = score_method(model, tokenizer, full_gate_prompts, device, args.batch_size, args.output_dir, "full-gated", True)
                full_gate_predictions = ((1 - retrieval_weight) * full_zero_probabilities + retrieval_weight * full_gate_probabilities).argmax(-1).tolist()
            else:
                full_gate_predictions = score_method(model, tokenizer, full_gate_prompts, device, args.batch_size, args.output_dir, "full-gated")
            full_metrics = {"zero_shot": aggregate_metrics(full_labels, full_zero_predictions), gate_key: aggregate_metrics(full_labels, full_gate_predictions)}
            full_count = len(full_examples)
            run.log({f"full_test/{name}/{metric}": value for name, values in full_metrics.items() for metric, value in values.items()})
        # Save aggregate metrics and metadata only, with no row predictions or labels.
        run.summary.update({"black_box": True, "sample_examples": len(sampled), "sample_metrics": sample_metrics, "full_test_metrics": full_metrics, "test_labels_used_for_selection": False})
        result = {"status": "completed", "measurement_type": "aggregate_only_black_box_test_sample", "dataset": "nvidia/When2Call", "split": "test/mcq", "official_test_loaded": True, "test_labels_used_for_selection": False, "per_example_outcomes_saved": False, "sample_method": "uniform random row-index sample without label access", "sample_seed": args.sample_seed, "test_sample_examples": len(sampled), "full_test_evaluated": full_metrics is not None, "full_test_examples": full_count, "checkpoint": args.qwen_checkpoint, "retrieval_pool": clean.get("retrieval_pool", "train_sft"), "selected_method": gate_key, "retrieval_feature": args.feature, "gate_score": gate_score, "k": k, "label_consensus_gate": args.label_consensus_gate, "label_disagreement_fallback_k1": args.label_disagreement_fallback_k1, "require_neighbor_match_zero_shot": args.require_neighbor_match_zero_shot, "probability_average": args.probability_average, "retrieval_weight": retrieval_weight, "selection_source": "clean validation only", "full_test_gate": "Run full evaluation only when selected gate accuracy exceeds zero-shot accuracy on the fixed sample.", "clean_metrics_source": str(args.clean_metrics), "clean_validation_examples": clean["validation_examples"], "clean_validation_metrics": {"zero_shot": baseline_clean, gate_key: selected_clean}, "gate_threshold": threshold, "training_metrics_source": "outputs/qwen-when2call-fullpool-base-seed20261055/metrics.json", "training_metrics": {"epoch": 2, "examples": 500, "training_loss": 0.408354387068056, "accuracy": 0.96, "macro_f1": 0.7201450925439365}, "test_sample_metrics": sample_metrics, "full_test_metrics": full_metrics, "embedding_cache": {"training": train_cache, "test_sample": sample_cache, "test_full": full_cache}, "embedding_usage": {"training": train_usage, "test_sample": sample_usage, "test_full": full_usage}, "runtime_seconds": time.time() - started, "wandb_run_id": run.id, "wandb_run_url": run.url}
        (args.output_dir / "metrics.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        write_heartbeat(args.output_dir / "heartbeat.json", "completed")
    except BaseException as error:
        run.summary.update({"status": "failed", "error": repr(error)})
        write_heartbeat(args.output_dir / "heartbeat.json", "failed")
        raise
    finally:
        run.finish()
    return 0


if __name__ == "__main__":
    # Return a nonzero status when the official measurement fails.
    raise SystemExit(main())
