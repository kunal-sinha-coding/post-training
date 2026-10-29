"""Compare two Qwen checkpoints and repeated label samples on clean validation and the black-box test.

The flow freezes candidate aggregation rules, scores a capped SFT validation sample and the full
When2Call test split, reduces labels to aggregate metrics immediately, and saves no row predictions.
"""
from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

import torch
import wandb

from experiments.evaluate_qwen_checkpoint_sft_validation import load_validation_rows
from experiments.evaluate_qwen_when2call_test import load_official_rows, prepare_test_rows
from experiments.train_qwen_when2call import label_token_ids, load_model, score_rows
from experiments.train_when2call_jina import LABELS


QWEN_BASE = "Qwen/Qwen2.5-1.5B-Instruct"


def score_checkpoint(checkpoint: Path, rows: list, device: torch.device, batch_size: int, max_length: int, heartbeat: Path) -> torch.Tensor:
    """Return four-way probabilities from one frozen Qwen adapter."""
    # Load one adapter at a time so the two LLM experts do not share GPU memory.
    model, tokenizer = load_model(QWEN_BASE, device, 16)
    if not hasattr(model, "load_adapter"):
        raise TypeError("The Qwen model did not produce a PEFT adapter host.")
    model.load_adapter(str(checkpoint), adapter_name="frozen")
    model.set_adapter("frozen")
    model.eval()
    ids = label_token_ids(tokenizer)
    probabilities = []
    # Score each minibatch and keep only the four class probabilities in memory.
    with torch.inference_mode():
        for start in range(0, len(rows), batch_size):
            heartbeat.write_text(json.dumps({"phase": "scoring", "checkpoint": str(checkpoint), "row": start}) + "\n")
            log_probs = score_rows(model, tokenizer, rows[start:start + batch_size], ids, device, max_length)
            probabilities.append(log_probs.exp().cpu())
    # Release this checkpoint before loading the next LLM.
    result = torch.cat(probabilities)
    del model, tokenizer
    if device.type == "cuda":
        torch.cuda.empty_cache()
    return result


def sampled_majority(probabilities: torch.Tensor, votes: int, seed: int) -> list[int]:
    """Predict by repeated stochastic draws of the model's four-way label token."""
    # Draw independent one-token labels from each prompt's next-token class distribution.
    generator = torch.Generator(device="cpu").manual_seed(seed)
    draws = torch.multinomial(probabilities, votes, replacement=True, generator=generator)
    predictions = []
    # Break vote ties with the same prompt's greedy class to keep the rule deterministic.
    for row, draw in zip(probabilities, draws, strict=True):
        counts = torch.bincount(draw, minlength=len(LABELS))
        tied = torch.where(counts == counts.max())[0]
        greedy = int(row.argmax())
        predictions.append(greedy if greedy in tied.tolist() else int(tied[0]))
    return predictions


def aggregate_metrics(rows: list, predictions: list[int]) -> dict[str, float | int]:
    """Reduce labels and predictions to aggregate accuracy and four-class macro F1."""
    # Build a temporary confusion matrix and discard it after metric calculation.
    matrix = [[0 for _ in LABELS] for _ in LABELS]
    for row, prediction in zip(rows, predictions, strict=True):
        matrix[row.label][prediction] += 1
    f1_values = []
    # Score every declared class, including a class with zero support.
    for label in range(len(LABELS)):
        true_positive = matrix[label][label]
        predicted = sum(matrix[source][label] for source in range(len(LABELS)))
        support = sum(matrix[label])
        precision = true_positive / predicted if predicted else 0.0
        recall = true_positive / support if support else 0.0
        f1_values.append(2 * precision * recall / (precision + recall) if precision + recall else 0.0)
    return {
        "accuracy": sum(row.label == prediction for row, prediction in zip(rows, predictions, strict=True)) / max(1, len(rows)),
        "macro_f1": sum(f1_values) / len(f1_values),
        "examples": len(rows),
    }


def main() -> int:
    """Measure frozen LLM and vote candidates without saving example-level test outputs."""
    # Parse the two Qwen checkpoints and fixed evaluation settings before loading benchmark rows.
    parser = argparse.ArgumentParser()
    parser.add_argument("--champion-checkpoint", type=Path, required=True)
    parser.add_argument("--comparison-checkpoint", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--validation-size", type=int, default=500)
    parser.add_argument("--validation-seed", type=int, default=20261053)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--max-length", type=int, default=4096)
    args = parser.parse_args()
    # Enforce the project evaluation cap and require tracking before loading the official test split.
    if not 1 <= args.validation_size <= 500:
        parser.error("--validation-size must be between 1 and 500.")
    if not os.getenv("WANDB_API_KEY"):
        raise RuntimeError("WANDB_API_KEY is required for research measurements.")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    started = time.time()
    run = wandb.init(
        project=os.getenv("WANDB_PROJECT", "when2call-research"),
        entity=os.getenv("WANDB_ENTITY"),
        name=args.output_dir.name,
        job_type="qwen-llm-ensemble-screen",
        config={
            "champion_checkpoint": str(args.champion_checkpoint),
            "comparison_checkpoint": str(args.comparison_checkpoint),
            "validation_source": "nvidia/When2Call:train_sft",
            "validation_size": args.validation_size,
            "validation_seed": args.validation_seed,
            "test_black_box": True,
            "candidate_methods_frozen_before_test": True,
            "training_performed": False,
        },
    )
    # Prepare the same fixed clean SFT validation sample for both Qwen experts.
    validation_rows, validation_source = load_validation_rows(args.validation_size, args.validation_seed)
    # Freeze the two-model weights and same-model vote counts before reading test rows.
    method_names = ["champion_greedy", "comparison_greedy", "llm_probability_mix_25", "llm_probability_mix_50", "llm_probability_mix_75"]
    method_names += [f"champion_sample_vote_{votes}" for votes in (1, 3, 5, 9)]
    method_names += [f"comparison_sample_vote_{votes}" for votes in (1, 3, 5, 9)]
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    heartbeat = args.output_dir / "heartbeat.json"
    # Score both checkpoints sequentially on validation and retain only class probabilities.
    validation_champion = score_checkpoint(args.champion_checkpoint, validation_rows, device, args.batch_size, args.max_length, heartbeat)
    validation_comparison = score_checkpoint(args.comparison_checkpoint, validation_rows, device, args.batch_size, args.max_length, heartbeat)
    # Construct all predeclared candidate rules from the frozen checkpoint distributions.
    def candidates(first: torch.Tensor, second: torch.Tensor) -> dict[str, torch.Tensor | list[int]]:
        """Build the predeclared LLM fusion and stochastic vote candidates."""
        # Keep all weights and vote counts fixed before the official test split is loaded.
        return {
            "champion_greedy": first,
            "comparison_greedy": second,
            "llm_probability_mix_25": 0.25 * first + 0.75 * second,
            "llm_probability_mix_50": 0.50 * first + 0.50 * second,
            "llm_probability_mix_75": 0.75 * first + 0.25 * second,
            **{f"champion_sample_vote_{k}": sampled_majority(first, k, 20261070 + k) for k in (1, 3, 5, 9)},
            **{f"comparison_sample_vote_{k}": sampled_majority(second, k, 20261080 + k) for k in (1, 3, 5, 9)},
        }
    # Compute clean validation metrics before loading the official test rows.
    validation_results = {}
    for name, candidate in candidates(validation_champion, validation_comparison).items():
        predictions = candidate.argmax(-1).tolist() if isinstance(candidate, torch.Tensor) else candidate
        validation_results[name] = aggregate_metrics(validation_rows, predictions)
        run.log({f"validation/{name}/accuracy": validation_results[name]["accuracy"], f"validation/{name}/macro_f1": validation_results[name]["macro_f1"]})
    # Load the official split only after all candidate rules are frozen and clean validation is recorded.
    test_rows = prepare_test_rows(load_official_rows())
    # Score the same frozen checkpoints on the full test split and retain only four-way probabilities.
    test_champion = score_checkpoint(args.champion_checkpoint, test_rows, device, args.batch_size, args.max_length, heartbeat)
    test_comparison = score_checkpoint(args.comparison_checkpoint, test_rows, device, args.batch_size, args.max_length, heartbeat)
    # Reduce candidate outcomes to aggregate metrics without writing row-level labels or predictions.
    test_results = {}
    for name, candidate in candidates(test_champion, test_comparison).items():
        predictions = candidate.argmax(-1).tolist() if isinstance(candidate, torch.Tensor) else candidate
        test_results[name] = aggregate_metrics(test_rows, predictions)
        run.log({f"test/{name}/accuracy": test_results[name]["accuracy"], f"test/{name}/macro_f1": test_results[name]["macro_f1"]})
    # Save aggregate evidence and checkpoint provenance only.
    result = {
        "status": "completed",
        "experiment": "qwen_llm_ensemble_and_sample_vote",
        "purpose": "Compare independent Qwen probability fusion and repeated one-token label voting.",
        "training_metrics": None,
        "training_metrics_status": "not applicable because this is frozen inference only",
        "validation_source": validation_source,
        "validation_metrics": validation_results,
        "test_metrics": test_results,
        "test_examples": len(test_rows),
        "test_black_box": True,
        "test_rows_or_predictions_saved": False,
        "champion_checkpoint": str(args.champion_checkpoint),
        "comparison_checkpoint": str(args.comparison_checkpoint),
        "method_names_frozen_before_test": method_names,
        "runtime_seconds": time.time() - started,
        "wandb_run_id": run.id,
        "wandb_run_url": run.url,
    }
    (args.output_dir / "metrics.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    # Finish tracking after the aggregate-only result is durable.
    run.finish()
    print(json.dumps({"validation": validation_results, "test": test_results}, indent=2))
    return 0


if __name__ == "__main__":
    # Return a nonzero status when any required evaluation step fails.
    raise SystemExit(main())
