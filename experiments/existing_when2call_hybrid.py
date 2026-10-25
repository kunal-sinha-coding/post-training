"""Measure fixed hybrids of existing When2Call encoders and the trained Qwen SFT model.

Preparation freezes existing checkpoint hashes and four predeclared hybrid rules without
training or development selection. One aggregate measurement scores each model once,
restores source row order after encoder batching, and compares fixed hybrids and baselines.
Official predictions, labels, probabilities, and per-class statistics remain in memory only.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time

import torch

from experiments.calibrate_clean_validation import collect_logits, load_checkpoint
from experiments.heterogeneous_when2call import artifact_digest, assert_size, free_gpu, metrics, save_json
from experiments.train_qwen_when2call import load_model, label_token_ids, score_rows, write_heartbeat
from experiments.train_when2call_jina import LABELS, Example
import experiments.train_when2call_jina as jina_training


ENCODERS = [
    "outputs/clean-validation-when2call-pref6000-bfcl-simple-multiple-1000-seed20261065",
    "outputs/clean-validation-when2call-pref6000-bfcl-simple-multiple-1000-seed20261061",
    "outputs/clean-validation-when2call-pref6000-bfcl1500-callonly-seed20261048",
]
WEIGHTS = [0.35625, 0.1375, 0.50625]
QWEN = "outputs/qwen-when2call-sft-15b-seed20261022"
QWEN_BASE = "Qwen/Qwen2.5-1.5B-Instruct"
METHODS = ("single_average", "single_gate", "ensemble_average", "ensemble_gate")


def encoder_families(logits: torch.Tensor, weights: list[float]) -> tuple[torch.Tensor, torch.Tensor]:
    # Preserve the standalone encoder and historical weighted raw-logit ensemble definitions.
    weight = torch.tensor(weights, dtype=logits.dtype).view(-1, 1, 1)
    return logits[2].softmax(-1), (logits * weight).sum(0).softmax(-1)


def hybrid_probabilities(encoder: torch.Tensor, qwen: torch.Tensor, rule: str) -> torch.Tensor:
    # Apply a fixed equal probability average or choose the lower-entropy family per row.
    if rule == "average":
        return (encoder + qwen) / 2
    if rule != "gate":
        raise ValueError("Unknown frozen hybrid rule: " + rule)
    probabilities = torch.stack((encoder, qwen), dim=1)
    entropy = -(probabilities.clamp_min(1e-8).log() * probabilities).sum(-1)
    return probabilities[torch.arange(len(probabilities)), entropy.argmin(1)]


def prepare(args: object, run: object) -> dict:
    # Freeze existing artifact identities and all four methods before opening official examples.
    artifacts = []
    for checkpoint in ENCODERS:
        artifacts.extend(Path(checkpoint) / name for name in ("model_state.pt", "encoder_config.json"))
    artifacts.extend(Path(QWEN) / name for name in ("adapter_model.safetensors", "adapter_config.json"))
    artifacts.append(Path("outputs/when2call-jina-v2-small/latest/tokenizer.json"))
    config = {"selection_complete": True, "training_performed": False, "development_selection_performed": False, "encoders": ENCODERS, "encoder_logit_weights": WEIGHTS, "single_encoder_index": 2, "qwen_checkpoint": QWEN, "qwen_base": QWEN_BASE, "qwen_output_permutation": [0, 1, 2, 3], "label_order": LABELS, "max_length": 4096, "methods": list(METHODS), "primary_method": "ensemble_average", "family_probability_weights": [0.5, 0.5], "artifact_sha256": {str(path): artifact_digest(path) for path in artifacts}, "validation_limitation": "Existing encoder warm starts saw all train_pref rows. No clean preference validation is claimed or used for selection.", "historical_selection_limitation": "Existing encoder approaches were identified in prior research with repeated official benchmark inspection. This fixed comparison is a benchmark measurement, not a new independent generalization estimate.", "metric_definition": "Primary macro F1 includes all four declared classes. The present-class macro F1 diagnostic permits comparison with historical encoder reports.", "qwen_mapping": "Historical adapter training used LABEL_TO_ID directly despite reversed ABCD descriptions in its prompt. Preserve learned identity indices.", "test_status": "queued"}
    save_json(args.work_dir / "frozen-config.json", config)
    run.summary.update({"selection_complete": True, "training_performed": False, "test_status": "queued"})
    return {"status": "completed", "test_status": "queued", "frozen_configuration": config}


def verify_frozen(config: dict) -> None:
    # Reject changed artifacts or method definitions before the official loader is imported or called.
    if not config["selection_complete"] or config["encoders"] != ENCODERS or config["qwen_checkpoint"] != QWEN or config["methods"] != list(METHODS) or config["encoder_logit_weights"] != WEIGHTS or config["primary_method"] != "ensemble_average":
        raise ValueError("Frozen existing-model comparison configuration changed.")
    for path, expected in config["artifact_sha256"].items():
        if artifact_digest(Path(path)) != expected:
            raise ValueError("Frozen comparison artifact changed: " + path)


def encoder_logits(checkpoint: str, examples: list, args: object, device: torch.device) -> torch.Tensor:
    # Score bounded encoder inputs and restore source order after length-sorted inference.
    model, tokenizer = load_checkpoint(Path(checkpoint), device, 4096)
    assert_size(model)
    for example in examples:
        example.token_ids = tokenizer(example.text, add_special_tokens=True, truncation=True, max_length=4096, verbose=False)["input_ids"]
    order = sorted(range(len(examples)), key=lambda index: len(examples[index].token_ids))
    values = []
    for start in range(0, len(order), args.batch_size):
        write_heartbeat(args.output_dir / "heartbeat.json", "encoder-evaluation", start)
        batch = [examples[index] for index in order[start:start + args.batch_size]]
        logits, _ = collect_logits(model, tokenizer, batch, device, batch_size=args.batch_size)
        values.append(logits)
    sorted_logits = torch.cat(values)
    restored = torch.empty_like(sorted_logits)
    restored[torch.tensor(order)] = sorted_logits
    del model, tokenizer, values
    free_gpu()
    return restored


def test(args: object, run: object) -> dict:
    # Measure every frozen hybrid and baseline from one sequential pass through the four models.
    config_path = args.work_dir / "frozen-config.json"
    config = json.loads(config_path.read_text())
    verify_frozen(config)
    from experiments.evaluate_qwen_when2call_test import load_official_rows, prepare_test_rows
    rows = list(load_official_rows())
    qwen_rows = prepare_test_rows(rows)
    examples = [Example("Question: " + row["question"] + "\nAvailable tools:\n" + ("\n".join(row["tools"]) if row["tools"] else "No tools are available."), 0, str(index)) for index, row in enumerate(rows)]
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    jina_training.MAX_LENGTH = 4096
    encoder_scores = []
    for checkpoint in config["encoders"]:
        write_heartbeat(args.output_dir / "heartbeat.json", "loading-encoder")
        encoder_scores.append(encoder_logits(checkpoint, examples, args, device))
    single, ensemble = encoder_families(torch.stack(encoder_scores), config["encoder_logit_weights"])
    del encoder_scores
    # Evaluate only the existing SFT adapter with its historical input and learned output order.
    write_heartbeat(args.output_dir / "heartbeat.json", "loading-qwen-sft")
    model, tokenizer = load_model(config["qwen_base"], device, 16)
    model.load_adapter(config["qwen_checkpoint"], adapter_name="frozen")
    model.set_adapter("frozen")
    assert_size(model)
    model.eval()
    qwen_scores = []
    with torch.inference_mode():
        for start in range(0, len(qwen_rows), args.batch_size):
            write_heartbeat(args.output_dir / "heartbeat.json", "qwen-sft-evaluation", start)
            qwen_scores.append(score_rows(model, tokenizer, qwen_rows[start:start + args.batch_size], label_token_ids(tokenizer), device, 4096).exp().cpu())
    qwen = torch.cat(qwen_scores)
    del model, tokenizer, qwen_scores
    free_gpu()
    # Reduce hidden labels to aggregate metrics without saving probabilities or per-class outcomes.
    probabilities = {"encoder_single": single, "encoder_ensemble": ensemble, "qwen_sft": qwen}
    for family_name, family in (("single", single), ("ensemble", ensemble)):
        for rule in ("average", "gate"):
            probabilities[family_name + "_" + rule] = hybrid_probabilities(family, qwen, rule)
    labels = torch.tensor([row.label for row in qwen_rows])
    aggregate = {}
    for name, probability in probabilities.items():
        complete = metrics(labels, probability)
        aggregate[name] = {key: complete[key] for key in ("accuracy", "macro_f1", "macro_f1_present_classes")}
        run.log({name + "/test_accuracy": aggregate[name]["accuracy"], name + "/test_macro_f1_all_four_classes": aggregate[name]["macro_f1"], name + "/test_macro_f1_present_classes_diagnostic": aggregate[name]["macro_f1_present_classes"]})
    result = {"status": "completed", "test_status": "measured", "test_measurement_only": True, "black_box": True, "selection_complete": True, "official_test_loaded": True, "examples": len(rows), "dataset": "nvidia/When2Call", "dataset_revision": "0582f7749df63a96fdc3070932e83e72396ace53", "split": "test/mcq", "primary_method": config["primary_method"], "official_test_metrics": aggregate[config["primary_method"]], "all_methods": aggregate, "frozen_config_sha256": artifact_digest(config_path), "frozen_configuration": config, "test_selection_performed": False}
    save_json(args.output_dir / "aggregate-comparison.json", result)
    return result


def main() -> int:
    # Initialize tracking before data access and preserve phase results and failure evidence.
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("prepare", "test"))
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--batch-size", type=int, default=1)
    args = parser.parse_args()
    import wandb
    if not os.getenv("WANDB_API_KEY"):
        raise RuntimeError("WANDB_API_KEY is required.")
    args.work_dir.mkdir(parents=True, exist_ok=True)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    metadata = {"command": [sys.executable, *sys.argv], "git_commit": subprocess.check_output(["git", "-c", "safe.directory=/workspace/post-training", "rev-parse", "HEAD"], text=True).strip(), "configuration": {key: str(value) if isinstance(value, Path) else value for key, value in vars(args).items()}, "encoders": ENCODERS, "encoder_logit_weights": WEIGHTS, "qwen_checkpoint": QWEN, "max_length": 4096, "primary_method": "ensemble_average"}
    run = wandb.init(project=os.getenv("WANDB_PROJECT", "when2call-research"), entity=os.getenv("WANDB_ENTITY"), name="existing-when2call-hybrid-" + args.mode, job_type="existing-hybrid-" + args.mode, config=metadata)
    started = time.time()
    stop = threading.Event()
    def keep_alive() -> None:
        # Refresh liveness during model loading without suppressing per-batch progress updates.
        while not stop.wait(30):
            heartbeat = args.output_dir / "heartbeat.json"
            if not heartbeat.exists() or time.time() - heartbeat.stat().st_mtime > 45:
                write_heartbeat(heartbeat, "worker-alive")
    threading.Thread(target=keep_alive, daemon=True).start()
    try:
        write_heartbeat(args.output_dir / "heartbeat.json", "loading")
        result = {"prepare": prepare, "test": test}[args.mode](args, run)
        metadata.update({"status": "completed", "runtime_seconds": time.time() - started, "wandb_run_id": run.id, "wandb_run_url": run.url})
        save_json(args.output_dir / "metrics.json", {**metadata, **result})
        run.summary.update({"status": "completed", "runtime_seconds": metadata["runtime_seconds"], "primary_method": "ensemble_average"})
        write_heartbeat(args.output_dir / "heartbeat.json", "completed")
    except BaseException as error:
        metadata.update({"status": "failed", "error": repr(error), "runtime_seconds": time.time() - started, "wandb_run_id": run.id, "wandb_run_url": run.url})
        save_json(args.output_dir / "metrics.json", metadata)
        run.summary.update({"status": "failed", "error": repr(error)})
        write_heartbeat(args.output_dir / "heartbeat.json", "failed")
        raise
    finally:
        stop.set()
        run.finish()
    return 0


if __name__ == "__main__":
    # Return the worker outcome to the persistent research supervisor.
    raise SystemExit(main())
