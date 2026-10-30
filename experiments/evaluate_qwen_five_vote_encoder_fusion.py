"""Evaluate Qwen vote and raw probabilities fused with the selected three-encoder family.

The flow scores fixed clean validation first, selects only among predeclared fusion rules,
then measures the frozen candidates on the full test split and saves aggregate metrics only.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
from pathlib import Path

import torch
import wandb

from experiments.evaluate_qwen_checkpoint_sft_validation import load_validation_rows
from experiments.evaluate_qwen_llm_ensemble import QWEN_BASE, aggregate_metrics, sampled_majority, score_checkpoint
from experiments.evaluate_qwen_when2call_test import load_official_rows, prepare_test_rows
from experiments.existing_when2call_hybrid import ENCODERS, WEIGHTS, encoder_logits, free_gpu
from experiments.train_when2call_jina import Example, LABELS
import experiments.train_when2call_jina as jina_training


CHAMPION = "outputs/qwen-tool-rich-large-boundary-synthetic-only-20261028/epoch-01"
VOTE_COUNT = 5
VOTE_SEED = 20261070 + VOTE_COUNT
FUSION_ENCODER_WEIGHTS = (0.25, 0.50, 0.75)


def vote_distribution(probabilities: torch.Tensor) -> tuple[torch.Tensor, list[int]]:
    """Return five-draw label frequencies and the exact majority-vote predictions."""
    generator = torch.Generator(device="cpu").manual_seed(VOTE_SEED)
    draws = torch.multinomial(probabilities.cpu(), VOTE_COUNT, replacement=True, generator=generator)
    counts = torch.stack([torch.bincount(row, minlength=len(LABELS)) for row in draws])
    majority = sampled_majority(probabilities.cpu(), VOTE_COUNT, VOTE_SEED)
    return counts.float() / VOTE_COUNT, majority


def encoder_probabilities(rows: list, args: argparse.Namespace, device: torch.device) -> torch.Tensor:
    """Score the three frozen encoders and combine them with the selected fixed weights."""
    examples = [Example(row.prompt, row.label, str(index)) for index, row in enumerate(rows)]
    jina_training.MAX_LENGTH = 4096
    members = []
    for checkpoint in ENCODERS:
        members.append(encoder_logits(checkpoint, examples, args, device))
    weights = torch.tensor(WEIGHTS, dtype=members[0].dtype).view(-1, 1, 1)
    return (torch.stack(members) * weights).sum(0).softmax(-1)


def candidate_probabilities(qwen: torch.Tensor, encoder: torch.Tensor) -> dict[str, torch.Tensor]:
    """Build predeclared baselines and vote-to-encoder probability blends."""
    vote_probs, majority = vote_distribution(qwen)
    majority_tensor = torch.nn.functional.one_hot(torch.tensor(majority), num_classes=len(LABELS)).float()
    candidates = {"qwen_greedy": qwen, "qwen_five_vote_majority": majority_tensor, "encoder_ensemble": encoder}
    for weight in FUSION_ENCODER_WEIGHTS:
        candidates[f"vote_frequency_encoder_{int(weight * 100)}"] = (1 - weight) * vote_probs + weight * encoder
        candidates[f"vote_majority_encoder_{int(weight * 100)}"] = (1 - weight) * majority_tensor + weight * encoder
    # Preserve the model's raw class probabilities as a distinct fusion signal.
    candidates["vote_probability_encoder_50"] = 0.5 * qwen + 0.5 * encoder
    return candidates


def score_candidates(rows: list, candidates: dict[str, torch.Tensor]) -> dict[str, dict]:
    """Reduce candidate predictions to aggregate accuracy and macro F1."""
    results = {}
    for name, probabilities in candidates.items():
        results[name] = aggregate_metrics(rows, probabilities.argmax(-1).tolist())
    return results


def score_models(rows: list, args: argparse.Namespace, device: torch.device, heartbeat: Path) -> tuple[torch.Tensor, torch.Tensor]:
    """Score the champion and selected encoder family sequentially to limit GPU memory use."""
    encoder = encoder_probabilities(rows, args, device)
    qwen = score_checkpoint(Path(args.champion_checkpoint), rows, device, args.batch_size, 4096, heartbeat)
    free_gpu()
    return qwen, encoder


def main() -> int:
    """Select a fixed vote-and-encoder fusion on clean validation and report full-test aggregates."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--champion-checkpoint", type=Path, default=Path(CHAMPION))
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--validation-size", type=int, default=500)
    parser.add_argument("--validation-seed", type=int, default=20261053)
    parser.add_argument("--batch-size", type=int, default=1)
    args = parser.parse_args()
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
        job_type="qwen-five-vote-encoder-fusion",
        config={"champion_checkpoint": str(args.champion_checkpoint), "encoders": ENCODERS, "encoder_weights": WEIGHTS, "votes": VOTE_COUNT, "vote_seed": VOTE_SEED, "fusion_encoder_weights": FUSION_ENCODER_WEIGHTS, "validation_size": args.validation_size, "validation_seed": args.validation_seed, "test_selection": False},
    )
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    heartbeat = args.output_dir / "heartbeat.json"

    # Score the fixed clean validation sample before loading any official test rows.
    validation_rows, validation_source = load_validation_rows(args.validation_size, args.validation_seed)
    validation_qwen, validation_encoder = score_models(validation_rows, args, device, heartbeat)
    validation_candidates = candidate_probabilities(validation_qwen, validation_encoder)
    validation_metrics = score_candidates(validation_rows, validation_candidates)
    # Select the fusion rule using only clean validation accuracy and macro F1.
    fusion_names = [name for name in validation_metrics if name.startswith(("vote_frequency_encoder_", "vote_majority_encoder_", "vote_probability_encoder_"))]
    selected_fusion = max(fusion_names, key=lambda name: (validation_metrics[name]["accuracy"], validation_metrics[name]["macro_f1"]))

    # Freeze all candidate rules before loading the black-box test split.
    test_rows = prepare_test_rows(load_official_rows())
    test_qwen, test_encoder = score_models(test_rows, args, device, heartbeat)
    test_metrics = score_candidates(test_rows, candidate_probabilities(test_qwen, test_encoder))
    for name, metrics in validation_metrics.items():
        run.log({f"validation/{name}/accuracy": metrics["accuracy"], f"validation/{name}/macro_f1": metrics["macro_f1"]})
    for name, metrics in test_metrics.items():
        run.log({f"test/{name}/accuracy": metrics["accuracy"], f"test/{name}/macro_f1": metrics["macro_f1"]})

    # Save aggregate evidence and frozen model provenance without row-level test outputs.
    result = {
        "status": "completed",
        "experiment": "qwen_tool_rich_champion_five_vote_three_encoder_fusion",
        "purpose": "Fuse the current five-sampled-vote Qwen champion with the selected fixed three-encoder family.",
        "training_metrics": None,
        "training_metrics_status": "not applicable because this is frozen inference only",
        "validation_source": validation_source,
        "validation_metrics": validation_metrics,
        "selected_fusion_by_clean_validation": selected_fusion,
        "test_metrics": test_metrics,
        "test_examples": len(test_rows),
        "test_black_box": True,
        "test_rows_or_predictions_saved": False,
        "test_selection_performed": False,
        "champion_checkpoint": str(args.champion_checkpoint),
        "encoder_checkpoints": ENCODERS,
        "encoder_logit_weights": WEIGHTS,
        "encoder_family_rule": "Weighted encoder logits are softmaxed, then treated as one expert family.",
        "vote_count": VOTE_COUNT,
        "vote_seed": VOTE_SEED,
        "fusion_encoder_weights": FUSION_ENCODER_WEIGHTS,
        "method_selection": "Highest clean-validation accuracy among predeclared vote-frequency and vote-majority blends; macro F1 breaks ties.",
        "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "runtime_seconds": time.time() - started,
        "wandb_run_id": run.id,
        "wandb_run_url": run.url,
    }
    (args.output_dir / "metrics.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    run.finish()
    print(json.dumps({"selected_fusion": selected_fusion, "validation": validation_metrics[selected_fusion], "test": test_metrics[selected_fusion]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
