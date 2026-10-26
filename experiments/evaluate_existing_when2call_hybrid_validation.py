"""Evaluate frozen encoder and Qwen hybrids on a held-out SFT-source partition.

The flow loads the SFT training source, creates a fixed stratified development split,
freezes candidate rules before scoring, measures the encoder and Qwen once, and saves
only aggregate metrics. It never loads the official test split or writes row outcomes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
from pathlib import Path
import subprocess
import time

import torch

from experiments.clean_validation_baseline import load_sft_training_rows, split_examples
from experiments.heterogeneous_when2call import artifact_digest
from experiments.existing_when2call_hybrid import (
    DISAGREE_METHODS,
    POOL_GRID_METHODS,
    REQUEST_CONFIDENCE_METHODS,
    RULE_METHODS,
    RULES,
    input_route_mask,
    encoder_logits,
    hybrid_probabilities,
)
from experiments.train_qwen_when2call import (
    ClassificationRow,
    label_token_ids,
    load_model,
    make_prompt,
    score_rows,
    write_heartbeat,
)
from experiments.train_when2call_jina import LABELS, metric_values, prepare_train_examples


ENCODER = "outputs/clean-validation-when2call-pref6000-bfcl1500-callonly-seed20261048"
QWEN = "outputs/qwen-when2call-sft-15b-seed20261022"
QWEN_BASE = "Qwen/Qwen2.5-1.5B-Instruct"


def evaluate(args: argparse.Namespace, run: object) -> dict:
    # Score the declared frozen candidates on the SFT source partition unseen by both members.
    rows = list(load_sft_training_rows())
    examples = prepare_train_examples(rows)
    _, development = split_examples(examples, 0.2, args.split_seed)
    # Keep the clean validation measurement within the project evaluation sample cap.
    if len(development) > args.max_validation_examples:
        grouped = {label: [] for label in range(len(LABELS))}
        for item in development:
            grouped[item.label].append(item)
        rng = random.Random(args.sample_seed)
        for items in grouped.values():
            rng.shuffle(items)
        total = len(development)
        quotas = {label: len(items) * args.max_validation_examples / total for label, items in grouped.items()}
        counts = {label: min(len(grouped[label]), int(quotas[label])) for label in grouped}
        for label in sorted(grouped, key=lambda key: quotas[key] - counts[key], reverse=True):
            if sum(counts.values()) >= args.max_validation_examples:
                break
            if counts[label] < len(grouped[label]):
                counts[label] += 1
        development = [item for label in grouped for item in grouped[label][:counts[label]]]
        rng.shuffle(development)
    source_indices = [int(item.source_id) for item in development]
    validation_examples = [examples[index] for index in source_indices]
    # Build routing features from the same visible question and tool text scored by both models.
    validation_source_rows = []
    for item in validation_examples:
        question, _, tool_text = item.text.partition("\nAvailable tools:\n")
        tools = [] if tool_text.strip() == "No tools are available." else tool_text.splitlines()
        validation_source_rows.append({"question": question, "tools": tools})
    validation_rows = [ClassificationRow(make_prompt(rows[index]), examples[index].label, None) for index in source_indices]
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_heartbeat(args.output_dir / "heartbeat.json", "encoder-validation")
    encoder = encoder_logits(ENCODER, validation_examples, args, device).softmax(-1)
    model, tokenizer = load_model(QWEN_BASE, device, 16)
    if not hasattr(model, "load_adapter"):
        raise TypeError("The Qwen base did not produce a PEFT model.")
    model.load_adapter(args.qwen_checkpoint, adapter_name="frozen")
    model.set_adapter("frozen")
    model.eval()
    scores = []
    with torch.inference_mode():
        for start in range(0, len(validation_rows), args.batch_size):
            write_heartbeat(args.output_dir / "heartbeat.json", "qwen-validation", start)
            scores.append(score_rows(model, tokenizer, validation_rows[start:start + args.batch_size], label_token_ids(tokenizer), device, 4096).exp().cpu())
    qwen = torch.cat(scores)
    labels = torch.tensor([item.label for item in validation_examples])
    candidates = {"encoder_single": encoder, "qwen_sft": qwen, "single_average": (encoder + qwen) / 2, "single_gate": hybrid_probabilities(encoder, qwen, "gate")}
    methods = tuple(dict.fromkeys((*POOL_GRID_METHODS, *DISAGREE_METHODS, *REQUEST_CONFIDENCE_METHODS, *RULE_METHODS)))
    for method in methods:
        if method in candidates or method in ("single_average", "single_gate"):
            continue
        rule = method.removeprefix("single_")
        if rule.removeprefix("encoder_") in RULES:
            mask = input_route_mask(validation_source_rows, rule.removeprefix("encoder_"), encoder.device)
            candidates[method] = torch.where(mask.unsqueeze(-1), encoder, qwen)
        else:
            candidates[method] = hybrid_probabilities(encoder, qwen, rule)
    aggregate = {}
    for name, probabilities in candidates.items():
        result = metric_values(labels.tolist(), probabilities.argmax(-1).tolist(), list(range(len(LABELS))))
        aggregate[name] = {key: result[key] for key in ("accuracy", "macro_f1")}
        run.log({f"validation/{name}/accuracy": result["accuracy"], f"validation/{name}/macro_f1": result["macro_f1"]})
    # Save only source-level counts, frozen identifiers, and aggregate metrics.
    return {
        "status": "completed",
        "official_test_loaded": False,
        "training_performed": False,
        "validation_source": "nvidia/When2Call train_sft",
        "validation_source_independent_of_training": True,
        "validation_examples": len(validation_examples),
        "split_seed": args.split_seed,
        "sample_seed": args.sample_seed,
        "validation_sample_cap": args.max_validation_examples,
        "validation_indices_sha256": hashlib.sha256(",".join(map(str, source_indices)).encode()).hexdigest(),
        "encoder_checkpoint": ENCODER,
        "qwen_checkpoint": args.qwen_checkpoint,
        "artifact_sha256": {
            str(path): artifact_digest(path)
            for path in (
                Path(ENCODER) / "model_state.pt",
                Path(ENCODER) / "encoder_config.json",
                Path(args.qwen_checkpoint) / "adapter_model.safetensors",
                Path(args.qwen_checkpoint) / "adapter_config.json",
            )
        },
        "qwen_base": QWEN_BASE,
        "candidate_methods": list(aggregate),
        "aggregate_validation_metrics": aggregate,
        "git_commit": subprocess.check_output(["git", "-c", "safe.directory=/workspace/post-training", "rev-parse", "HEAD"], text=True).strip(),
        "wandb_run_id": run.id,
        "wandb_run_url": run.url,
    }


def main() -> int:
    # Register one validation run before loading the development partition or model artifacts.
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--split-seed", type=int, default=20261026)
    parser.add_argument("--sample-seed", type=int, default=20261068)
    parser.add_argument("--max-validation-examples", type=int, default=500)
    parser.add_argument("--qwen-checkpoint", default=QWEN)
    parser.add_argument("--batch-size", type=int, default=1)
    args = parser.parse_args()
    # Enforce the research policy before loading any validation rows.
    if args.max_validation_examples < 1 or args.max_validation_examples > 500:
        raise ValueError("Clean validation evaluation must use between 1 and 500 examples.")
    import wandb
    if not os.getenv("WANDB_API_KEY"):
        raise RuntimeError("WANDB_API_KEY is required for validation experiments.")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    run = wandb.init(
        project=os.getenv("WANDB_PROJECT", "when2call-research"),
        entity=os.getenv("WANDB_ENTITY"),
        name="existing-when2call-hybrid-sft-source-validation",
        job_type="clean-validation",
        config={"encoder": ENCODER, "qwen": args.qwen_checkpoint, "qwen_base": QWEN_BASE, "split_seed": args.split_seed, "sample_seed": args.sample_seed, "max_validation_examples": args.max_validation_examples, "source": "nvidia/When2Call train_sft", "official_test_loaded": False},
    )
    started = time.time()
    try:
        result = evaluate(args, run)
        result["runtime_seconds"] = time.time() - started
        (args.output_dir / "metrics.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        run.summary.update({"status": "completed", "validation_examples": result["validation_examples"], "output_dir": str(args.output_dir)})
        write_heartbeat(args.output_dir / "heartbeat.json", "completed")
        print(json.dumps({"validation_examples": result["validation_examples"], "metrics": result["aggregate_validation_metrics"]}, indent=2))
    except BaseException as error:
        run.summary.update({"status": "failed", "error": repr(error)})
        write_heartbeat(args.output_dir / "heartbeat.json", "failed")
        raise
    finally:
        run.finish()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
