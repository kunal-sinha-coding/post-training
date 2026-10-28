"""Fit scalar probability temperatures for the frozen full-pool Qwen and encoder pair.

The flow draws at most 500 clean SFT-source examples, splits them into disjoint fit and
validation partitions, scores frozen members, fits one temperature per member, compares fixed
calibrated candidates, and saves aggregate metrics. It never loads the official test split.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import time
from pathlib import Path

import torch

from experiments.clean_validation_baseline import load_sft_training_rows
from experiments.existing_when2call_hybrid import ENCODERS, QWEN_BASE, encoder_logits, hybrid_probabilities
from experiments.heterogeneous_when2call import artifact_digest
from experiments.train_fullpool_when2call_stacker import metric_summary, partition_indices, sample_indices
from experiments.train_qwen_when2call import ClassificationRow, label_token_ids, load_model, make_prompt, score_rows, write_heartbeat
from experiments.train_when2call_jina import LABELS, prepare_train_examples
import experiments.train_when2call_jina as jina_training


QWEN_CHECKPOINT = "outputs/qwen-when2call-fullpool-base-seed20261055/epoch-02"


def fit_temperature(probabilities: torch.Tensor, labels: torch.Tensor) -> float:
    """Fit one positive scalar temperature by minimizing fit-partition cross entropy."""
    # Optimize a log temperature so the fitted scale remains positive.
    logits = probabilities.clamp_min(1e-8).log().double()
    log_temperature = torch.zeros((), dtype=torch.float64, requires_grad=True)
    optimizer = torch.optim.LBFGS([log_temperature], max_iter=80, line_search_fn="strong_wolfe")
    def closure() -> torch.Tensor:
        # Keep fitting labels inside the disjoint meta-training partition.
        optimizer.zero_grad()
        temperature = log_temperature.exp().clamp(0.05, 20.0)
        loss = torch.nn.functional.cross_entropy(logits / temperature, labels)
        loss.backward()
        return loss
    optimizer.step(closure)
    return float(log_temperature.detach().exp().clamp(0.05, 20.0).item())


def main() -> int:
    """Fit calibration scales on clean data and compare them on a disjoint clean holdout."""
    # Freeze the source sample and calibration settings before model inference.
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--qwen-checkpoint", type=Path, default=Path(QWEN_CHECKPOINT))
    parser.add_argument("--encoder-checkpoint", type=Path, default=Path(ENCODERS[2]))
    parser.add_argument("--split-seed", type=int, default=20261078)
    parser.add_argument("--sample-seed", type=int, default=20261079)
    parser.add_argument("--meta-split-seed", type=int, default=20261080)
    parser.add_argument("--max-examples", type=int, default=500)
    parser.add_argument("--batch-size", type=int, default=1)
    args = parser.parse_args()
    # Enforce the clean data cap before loading the SFT source.
    if args.max_examples < 2 or args.max_examples > 500:
        raise ValueError("The combined clean SFT sample must contain between 2 and 500 examples.")
    import wandb
    if not os.getenv("WANDB_API_KEY"):
        raise RuntimeError("WANDB_API_KEY is required for this validation experiment.")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    run = wandb.init(
        project=os.getenv("WANDB_PROJECT", "when2call-research"),
        entity=os.getenv("WANDB_ENTITY"),
        name="fullpool-qwen-encoder-temperature-validation",
        job_type="clean-validation",
        config={"encoder": str(args.encoder_checkpoint), "qwen_checkpoint": str(args.qwen_checkpoint), "source": "nvidia/When2Call train_sft", "split_seed": args.split_seed, "sample_seed": args.sample_seed, "meta_split_seed": args.meta_split_seed, "max_examples": args.max_examples, "official_test_loaded": False},
    )
    started = time.time()
    try:
        # Create a stratified sample with disjoint fit and validation rows.
        sft_rows = list(load_sft_training_rows())
        examples = prepare_train_examples(sft_rows)
        sampled = sample_indices(examples, args.split_seed, args.sample_seed, args.max_examples)
        fitting, validation = partition_indices(sampled, examples, args.meta_split_seed)
        all_indices = fitting + validation
        qwen_rows = [ClassificationRow(make_prompt(sft_rows[index]), examples[index].label, None) for index in all_indices]
        labels = torch.tensor([examples[index].label for index in all_indices], dtype=torch.long)
        fit_positions = torch.arange(len(fitting))
        validation_positions = torch.arange(len(fitting), len(all_indices))
        # Score both frozen model families once on the clean sample.
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        jina_training.MAX_LENGTH = 4096
        write_heartbeat(args.output_dir / "heartbeat.json", "encoder-scoring")
        encoder = encoder_logits(str(args.encoder_checkpoint), [examples[index] for index in all_indices], args, device).softmax(-1)
        model, tokenizer = load_model(QWEN_BASE, device, 16)
        model.load_adapter(str(args.qwen_checkpoint), adapter_name="frozen")
        model.set_adapter("frozen")
        model.eval()
        qwen_scores = []
        with torch.inference_mode():
            for start in range(0, len(qwen_rows), args.batch_size):
                write_heartbeat(args.output_dir / "heartbeat.json", "qwen-scoring", start)
                qwen_scores.append(score_rows(model, tokenizer, qwen_rows[start:start + args.batch_size], label_token_ids(tokenizer), device, 4096).exp().cpu())
        qwen = torch.cat(qwen_scores)
        del model, tokenizer, qwen_scores
        # Fit separate scalar temperatures without using held-out validation labels.
        qwen_temperature = fit_temperature(qwen[fit_positions], labels[fit_positions])
        encoder_temperature = fit_temperature(encoder[fit_positions], labels[fit_positions])
        qwen_calibrated = (qwen.clamp_min(1e-8).log() / qwen_temperature).softmax(-1)
        encoder_calibrated = (encoder.clamp_min(1e-8).log() / encoder_temperature).softmax(-1)
        candidates = {
            "qwen_sft": qwen,
            "encoder_single": encoder,
            "single_average": (encoder + qwen) / 2,
            "single_entropy_weighted": hybrid_probabilities(encoder, qwen, "entropy_weighted"),
            "single_margin_weighted": hybrid_probabilities(encoder, qwen, "margin_weighted"),
            "single_gate": hybrid_probabilities(encoder, qwen, "gate"),
            "single_encoder_confident": hybrid_probabilities(encoder, qwen, "encoder_confident"),
            "single_qwen_weighted": hybrid_probabilities(encoder, qwen, "qwen_weighted"),
            "single_geometric": hybrid_probabilities(encoder, qwen, "geometric"),
            "single_request_conf_60": hybrid_probabilities(encoder, qwen, "request_conf_60"),
            "qwen_temperature": qwen_calibrated,
            "encoder_temperature": encoder_calibrated,
            "temperature_average": (encoder_calibrated + qwen_calibrated) / 2,
            "temperature_request_conf_60": hybrid_probabilities(encoder_calibrated, qwen_calibrated, "request_conf_60"),
        }
        fit_metrics = {name: metric_summary(labels[fit_positions], probability[fit_positions]) for name, probability in candidates.items()}
        validation_metrics = {name: metric_summary(labels[validation_positions], probability[validation_positions]) for name, probability in candidates.items()}
        for name, values in validation_metrics.items():
            run.log({f"validation/{name}/accuracy": values["accuracy"], f"validation/{name}/macro_f1": values["macro_f1"]})
        # Select only supported fusion methods with clean held-out accuracy and macro F1.
        selection_methods = ["single_average", "single_gate", "single_entropy_weighted", "single_margin_weighted", "single_encoder_confident", "single_request_conf_60"]
        selected_method = max(selection_methods, key=lambda name: (validation_metrics[name]["accuracy"], validation_metrics[name]["macro_f1"], name == "single_entropy_weighted"))
        # Save disjoint clean metrics, source fingerprints, and exact checkpoint provenance.
        result = {
            "status": "completed",
            "official_test_loaded": False,
            "training_examples": len(fitting),
            "validation_examples": len(validation),
            "sampled_examples": len(sampled),
            "fit_indices_sha256": hashlib.sha256(",".join(map(str, fitting)).encode()).hexdigest(),
            "validation_indices_sha256": hashlib.sha256(",".join(map(str, validation)).encode()).hexdigest(),
            "temperatures": {"qwen": qwen_temperature, "encoder": encoder_temperature},
            "training_metrics": fit_metrics,
            "heldout_validation_metrics": validation_metrics,
            "selection_methods": selection_methods,
            "selected_method": selected_method,
            "selection_metric": "clean held-out validation accuracy, with macro F1 as tie-breaker",
            "qwen_checkpoint": str(args.qwen_checkpoint),
            "encoder_checkpoint": str(args.encoder_checkpoint),
            "artifacts": {str(path): artifact_digest(path) for path in (args.encoder_checkpoint / "model_state.pt", args.qwen_checkpoint / "adapter_model.safetensors")},
            "runtime_seconds": time.time() - started,
            "git_commit": subprocess.check_output(["git", "-c", "safe.directory=/workspace/post-training", "rev-parse", "HEAD"], text=True).strip(),
            "wandb_run_id": run.id,
            "wandb_run_url": run.url,
        }
        (args.output_dir / "metrics.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        run.summary.update({"status": "completed", "qwen_temperature": qwen_temperature, "encoder_temperature": encoder_temperature, "selected_method": selected_method, "output_dir": str(args.output_dir)})
        write_heartbeat(args.output_dir / "heartbeat.json", "completed")
        print(json.dumps({"temperatures": result["temperatures"], "validation": validation_metrics}, indent=2))
    except BaseException as error:
        run.summary.update({"status": "failed", "error": repr(error)})
        write_heartbeat(args.output_dir / "heartbeat.json", "failed")
        raise
    finally:
        run.finish()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
