"""Train and select a heterogeneous When2Call ensemble without test selection.

The flow reconstructs the original Qwen preference split, excludes development questions
that occur in training, trains a fresh pretrained Jina encoder, and scores three members.
A fixed development half fits a regularized stacker and the other half compares three
predeclared rules. Frozen configurations permit separate aggregate official measurements.
"""
from __future__ import annotations

import argparse
import gc
import hashlib
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import time
import threading

import torch
from transformers import AutoModel, AutoTokenizer

from experiments.train_qwen_when2call import load_rows, prepare_rows, split_rows, load_model, label_token_ids, score_rows, write_heartbeat
from experiments.train_when2call_jina import LABELS, JinaSequenceClassifier, prepare_train_examples, metric_values


BASE_ENCODER = "jinaai/jina-embeddings-v2-small-en"
MEMBERS = [
    {"name": "rpo", "model": "Qwen/Qwen2.5-0.5B-Instruct", "checkpoint": "outputs/qwen-when2call-rpo-05b-seed20261022"},
    {"name": "sft", "model": "Qwen/Qwen2.5-1.5B-Instruct", "checkpoint": "outputs/qwen-when2call-sft-15b-seed20261022"},
]
SEED = 20261022


def save_json(path: Path, value: dict) -> None:
    # Replace each result atomically so monitoring never reads a partial record.
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n")
    temporary.replace(path)


def artifact_digest(path: Path) -> str:
    # Hash model artifacts in bounded chunks to bind frozen configuration to exact weights.
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def question_key(prompt: str) -> str:
    # Normalize question whitespace and case without using labels or tool schemas.
    question = prompt.split("Question: ", 1)[1].split("\nAvailable tools:\n", 1)[0]
    return " ".join(question.casefold().split())


def partitions() -> tuple:
    # Reconstruct the exact historical Qwen split before removing shared question groups.
    raw = list(load_rows())
    prepared = prepare_rows(raw)
    positions = {id(row): index for index, row in enumerate(prepared)}
    train, original_dev = split_rows(prepared, SEED)
    seen = {question_key(row.prompt) for row in train}
    development = [row for row in original_dev if question_key(row.prompt) not in seen]
    encoder = prepare_train_examples(raw)
    train_encoder = [encoder[positions[id(row)]] for row in train]
    dev_encoder = [encoder[positions[id(row)]] for row in development]
    identifiers = [positions[id(row)] for row in development]
    provenance = {"dataset": "nvidia/When2Call", "revision": "0582f7749df63a96fdc3070932e83e72396ace53", "source": "train_pref", "split_seed": SEED, "train_examples": len(train), "original_development_examples": len(original_dev), "development_examples": len(development), "excluded_shared_questions": len(original_dev) - len(development), "development_row_indices": identifiers, "development_sha256": hashlib.sha256(json.dumps(identifiers).encode()).hexdigest(), "question_normalization": "casefold and collapsed whitespace", "test_loaded": False}
    return train_encoder, dev_encoder, development, provenance


def assert_size(model: object) -> int:
    # Enforce the per-member limit including frozen base and adapter parameters.
    count = sum(parameter.numel() for parameter in model.parameters())
    if count >= 2_000_000_000:
        raise ValueError(f"Member exceeds parameter limit: {count}")
    return count


def free_gpu() -> None:
    # Release each completed member before the next model loads.
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


def encoder_inputs(tokenizer: object, examples: list, device: torch.device, length: int) -> dict:
    # Apply one explicit bounded context policy during encoder training and inference.
    inputs = tokenizer([row.text for row in examples], padding=True, truncation=True, max_length=length, return_tensors="pt")
    return {key: value.to(device) for key, value in inputs.items() if key in ("input_ids", "attention_mask")}


def raw_encoder(device: torch.device) -> tuple:
    # Initialize from the upstream pretrained encoder without any task warm start.
    try:
        tokenizer = AutoTokenizer.from_pretrained(BASE_ENCODER, trust_remote_code=True)
        encoder = AutoModel.from_pretrained(BASE_ENCODER, trust_remote_code=True)
    except (OSError, ValueError):
        # Repair an incomplete upstream cache once without using task checkpoint weights.
        tokenizer = AutoTokenizer.from_pretrained(BASE_ENCODER, trust_remote_code=True, force_download=True)
        encoder = AutoModel.from_pretrained(BASE_ENCODER, trust_remote_code=True, force_download=True)
    model = JinaSequenceClassifier(encoder, len(LABELS)).to(device)
    return model, tokenizer


def encoder_probabilities(model: object, tokenizer: object, examples: list, args: object, device: torch.device) -> torch.Tensor:
    # Score bounded encoder batches and retain probabilities only for the caller.
    model.eval()
    probabilities = []
    with torch.inference_mode():
        for start in range(0, len(examples), args.batch_size):
            write_heartbeat(args.output_dir / "heartbeat.json", "encoder-evaluation", start)
            batch = examples[start:start + args.batch_size]
            inputs = encoder_inputs(tokenizer, batch, device, args.max_length)
            with torch.autocast("cuda", dtype=torch.bfloat16, enabled=device.type == "cuda"):
                logits = model(**inputs).logits
            probabilities.append(logits.float().softmax(-1).cpu())
    return torch.cat(probabilities)


def metrics(labels: torch.Tensor, probabilities: torch.Tensor) -> dict:
    # Include all four declared classes even when a partition has no direct examples.
    result = metric_values(labels.tolist(), probabilities.argmax(-1).tolist(), list(range(len(LABELS))))
    result["macro_f1_present_classes"] = result["macro_f1"]
    for field in ("precision", "recall", "f1"):
        result["macro_" + field] = sum(result["per_class"][label][field] for label in LABELS) / len(LABELS)
    return result


def train_encoder(args: object, run: object, device: torch.device) -> dict:
    # Train a fresh action head and upstream encoder on the historical Qwen training rows.
    training, development, _, provenance = partitions()
    torch.manual_seed(SEED)
    model, tokenizer = raw_encoder(device)
    count = assert_size(model)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate, weight_decay=0.005)
    losses = []
    for epoch in range(args.epochs):
        order = list(training)
        random.Random(SEED + epoch).shuffle(order)
        model.train()
        for start in range(0, len(order), args.batch_size):
            write_heartbeat(args.output_dir / "heartbeat.json", "encoder-training", start)
            batch = order[start:start + args.batch_size]
            optimizer.zero_grad(set_to_none=True)
            inputs = encoder_inputs(tokenizer, batch, device, args.max_length)
            targets = torch.tensor([row.label for row in batch], device=device)
            with torch.autocast("cuda", dtype=torch.bfloat16, enabled=device.type == "cuda"):
                loss = torch.nn.functional.cross_entropy(model(**inputs).logits.float(), targets)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            losses.append(float(loss.detach()))
            if start % 100 == 0:
                run.log({"training/loss": losses[-1], "training/epoch": epoch + 1, "training/examples": start})
    # Save the encoder before scoring so evaluation failures do not discard trained weights.
    checkpoint = args.work_dir / "encoder"
    model.save_pretrained(checkpoint)
    tokenizer.save_pretrained(checkpoint)
    train_probabilities = encoder_probabilities(model, tokenizer, training, args, device)
    train_metrics = metrics(torch.tensor([row.label for row in training]), train_probabilities)
    probabilities = encoder_probabilities(model, tokenizer, development, args, device)
    result = {"train_metrics": train_metrics, "provenance": provenance, "parameter_count": count, "initialization": BASE_ENCODER, "task_warmstart": False, "epochs": args.epochs, "max_length": args.max_length, "learning_rate": args.learning_rate, "development_metrics": metrics(torch.tensor([row.label for row in development]), probabilities), "mean_training_loss": sum(losses) / len(losses), "checkpoint": str(checkpoint)}
    run.log({"train/accuracy": train_metrics["accuracy"], "train/macro_f1": train_metrics["macro_f1"], "train/confusion_matrix": train_metrics["confusion_matrix"], "development/accuracy": result["development_metrics"]["accuracy"], "development/macro_f1": result["development_metrics"]["macro_f1"], "development/confusion_matrix": result["development_metrics"]["confusion_matrix"], "train/per_class": train_metrics["per_class"], "development/per_class": result["development_metrics"]["per_class"]})
    save_json(args.work_dir / "encoder-metrics.json", result)
    del model, tokenizer, optimizer
    free_gpu()
    return result


def member_probabilities(args: object, qwen_rows: list, encoder_rows: list, device: torch.device, official: bool = False) -> torch.Tensor:
    # Score members sequentially without caching official example probabilities.
    outputs = []
    for member in MEMBERS:
        write_heartbeat(args.output_dir / "heartbeat.json", "loading-" + member["name"])
        model, tokenizer = load_model(member["model"], device, 16)
        model.load_adapter(member["checkpoint"], adapter_name="frozen")
        model.set_adapter("frozen")
        assert_size(model)
        model.eval()
        scores = []
        with torch.inference_mode():
            for start in range(0, len(qwen_rows), args.batch_size):
                write_heartbeat(args.output_dir / "heartbeat.json", "scoring-" + member["name"], start)
                scores.append(score_rows(model, tokenizer, qwen_rows[start:start + args.batch_size], label_token_ids(tokenizer), device, 4096).exp().cpu())
        # Preserve the learned index order because historical training targets used LABEL_TO_ID directly.
        outputs.append(torch.cat(scores))
        del model, tokenizer, scores
        free_gpu()
    # Load only the newly trained encoder checkpoint and its recorded context limit.
    model, tokenizer = raw_encoder(device)
    checkpoint = args.work_dir / "encoder"
    model.load_state_dict(torch.load(checkpoint / "model_state.pt", map_location="cpu", weights_only=True))
    assert_size(model)
    outputs.append(encoder_probabilities(model, tokenizer, encoder_rows, args, device))
    del model, tokenizer
    free_gpu()
    return torch.stack(outputs, dim=1)


def fit_stacker(probabilities: torch.Tensor, labels: torch.Tensor) -> dict:
    # Fit a fixed regularized multinomial model only on the designated fitting half.
    features = probabilities.clamp_min(1e-8).log().flatten(1).double()
    weights = torch.zeros(features.shape[1], len(LABELS), dtype=torch.float64, requires_grad=True)
    bias = torch.zeros(len(LABELS), dtype=torch.float64, requires_grad=True)
    optimizer = torch.optim.LBFGS([weights, bias], max_iter=100, line_search_fn="strong_wolfe")
    def closure() -> torch.Tensor:
        # Optimize cross entropy with a fixed coefficient penalty and no selection labels.
        optimizer.zero_grad()
        loss = torch.nn.functional.cross_entropy(features @ weights + bias, labels) + 0.1 * weights.square().sum()
        loss.backward()
        return loss
    optimizer.step(closure)
    return {"weights": weights.detach().tolist(), "bias": bias.detach().tolist(), "l2": 0.1}


def combine(probabilities: torch.Tensor, candidate: str, stacker: dict) -> torch.Tensor:
    # Apply the frozen uniform blend, minimum-entropy gate, or fitted stacker.
    if candidate == "uniform":
        return probabilities.mean(1)
    if candidate == "gate":
        entropy = -(probabilities.clamp_min(1e-8).log() * probabilities).sum(-1)
        chosen = entropy.argmin(1)
        return probabilities[torch.arange(len(probabilities)), chosen]
    features = probabilities.clamp_min(1e-8).log().flatten(1).double()
    return (features @ torch.tensor(stacker["weights"], dtype=torch.float64) + torch.tensor(stacker["bias"], dtype=torch.float64)).softmax(-1).float()


def select(args: object, run: object, device: torch.device) -> dict:
    # Select only from shared non-test development predictions using fixed fit and selection halves.
    _, encoder_rows, qwen_rows, provenance = partitions()
    encoder_record = json.loads((args.work_dir / "encoder-metrics.json").read_text())
    if encoder_record["provenance"] != provenance:
        raise ValueError("Encoder split provenance does not match selection.")
    args.max_length = encoder_record["max_length"]
    cache = args.work_dir / "development-probabilities.pt"
    artifacts = {member["checkpoint"] + "/adapter_model.safetensors": artifact_digest(Path(member["checkpoint"]) / "adapter_model.safetensors") for member in MEMBERS}
    artifacts[str(args.work_dir / "encoder" / "model_state.pt")] = artifact_digest(args.work_dir / "encoder" / "model_state.pt")
    digest = hashlib.sha256(json.dumps({"provenance": provenance, "members": MEMBERS, "encoder": encoder_record, "artifact_sha256": artifacts}, sort_keys=True).encode()).hexdigest()
    if cache.exists():
        cached = torch.load(cache, weights_only=True)
        if cached["digest"] != digest:
            raise ValueError("Development cache provenance changed.")
        probabilities = cached["probabilities"]
    else:
        probabilities = member_probabilities(args, qwen_rows, encoder_rows, device)
        torch.save({"digest": digest, "probabilities": probabilities}, cache)
    labels = torch.tensor([row.label for row in qwen_rows])
    # Keep duplicate development questions together when assigning the two development roles.
    keys = sorted({question_key(row.prompt) for row in qwen_rows})
    random.Random(SEED).shuffle(keys)
    fit_keys = set(keys[:len(keys) // 2])
    fitting = torch.tensor([index for index, row in enumerate(qwen_rows) if question_key(row.prompt) in fit_keys])
    selection = torch.tensor([index for index, row in enumerate(qwen_rows) if question_key(row.prompt) not in fit_keys])
    if not len(fitting) or not len(selection):
        raise ValueError("Both development roles require at least one question group.")
    stacker = fit_stacker(probabilities[fitting], labels[fitting])
    candidates = {}
    for name in ("uniform", "gate", "stacker"):
        score = metrics(labels[selection], combine(probabilities[selection], name, stacker))
        viable = bool(torch.isfinite(combine(probabilities[selection], name, stacker)).all())
        candidates[name] = {"selection_metrics": score, "test_status": "pending", "rule": name, "viable": viable}
        run.log({name + "/selection_accuracy": score["accuracy"], name + "/selection_macro_f1": score["macro_f1"]})
    # Freeze all three predeclared methods before any official measurement is allowed.
    config = {"selection_complete": True, "provenance": provenance, "members": MEMBERS, "encoder": encoder_record, "label_order": LABELS, "qwen_output_permutation": [0, 1, 2, 3], "qwen_prompt_mismatch": "Prompt describes ABCD in reverse order, but training and historical evaluation use LABEL_TO_ID indices directly. Preserve learned identity order.", "metric_definition": "Macro F1 includes all four classes. Some historical encoder metrics excluded direct.", "fitting_indices": fitting.tolist(), "selection_indices": selection.tolist(), "stacker": stacker, "candidates": candidates, "selection_criterion": "Report all predeclared methods. Prefer highest selection macro F1 with accuracy as tie breaker.", "member_selection_metrics": {MEMBERS[index]["name"] if index < 2 else "encoder": metrics(labels[selection], probabilities[selection, index]) for index in range(3)}}
    best = max(candidates, key=lambda name: (candidates[name]["selection_metrics"]["macro_f1"], candidates[name]["selection_metrics"]["accuracy"]))
    config["artifact_sha256"] = artifacts
    config["best_selection_candidate"] = best
    config["development_metrics"] = candidates[best]["selection_metrics"]
    save_json(args.work_dir / "frozen-config.json", config)
    return config


def test(args: object, run: object, device: torch.device) -> dict:
    # Load official labels only inside a separate frozen aggregate measurement worker.
    config = json.loads((args.work_dir / "frozen-config.json").read_text())
    if not config["selection_complete"] or config["members"] != MEMBERS or not config["candidates"][args.candidate]["viable"]:
        raise ValueError("Frozen candidate configuration is invalid.")
    for path, expected in config["artifact_sha256"].items():
        if artifact_digest(Path(path)) != expected:
            raise ValueError("Frozen model artifact changed: " + path)
    from experiments.evaluate_qwen_when2call_test import load_official_rows, prepare_test_rows, aggregate_metrics
    from experiments.train_when2call_jina import Example
    rows = list(load_official_rows())
    qwen_rows = prepare_test_rows(rows)
    encoder_rows = [Example("Question: " + row["question"] + "\nAvailable tools:\n" + ("\n".join(row["tools"]) if row["tools"] else "No tools are available."), 0, str(index)) for index, row in enumerate(rows)]
    args.max_length = config["encoder"]["max_length"]
    probabilities = member_probabilities(args, qwen_rows, encoder_rows, device, official=True)
    predictions = combine(probabilities, args.candidate, config["stacker"]).argmax(-1).tolist()
    aggregate = aggregate_metrics([row.label for row in qwen_rows], predictions)
    result = {"candidate": args.candidate, "test_measurement_only": True, "black_box": True, "selection_complete": True, "examples": len(rows), "metrics": aggregate, "frozen_config_sha256": hashlib.sha256((args.work_dir / "frozen-config.json").read_bytes()).hexdigest()}
    save_json(args.output_dir / ("test-" + args.candidate + ".json"), result)
    run.log({"test/accuracy": aggregate["accuracy"], "test/macro_f1": aggregate["macro_f1"]})
    return result


def main() -> int:
    # Register W&B before loading data or models and persist every failure with reproducibility metadata.
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("train-encoder", "select", "test"))
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--work-dir", type=Path)
    parser.add_argument("--candidate", choices=("uniform", "gate", "stacker"), default="uniform")
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--learning-rate", type=float, default=1e-5)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--max-length", type=int, default=2048)
    args = parser.parse_args()
    args.work_dir = args.work_dir or args.output_dir
    import wandb
    if not os.getenv("WANDB_API_KEY"):
        raise RuntimeError("WANDB_API_KEY is required.")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.work_dir.mkdir(parents=True, exist_ok=True)
    command = [sys.executable, *sys.argv]
    commit = subprocess.check_output(["git", "-c", "safe.directory=/workspace/post-training", "rev-parse", "HEAD"], text=True).strip()
    metadata = {"command": command, "git_commit": commit, "configuration": {key: str(value) if isinstance(value, Path) else value for key, value in vars(args).items()}, "members": MEMBERS, "labels": LABELS}
    run = wandb.init(project=os.getenv("WANDB_PROJECT", "when2call-research"), entity=os.getenv("WANDB_ENTITY"), name="heterogeneous-" + args.mode + "-" + args.candidate, job_type="heterogeneous-" + args.mode, config=metadata)
    started = time.time()
    stop_heartbeat = threading.Event()
    def keep_alive() -> None:
        # Preserve worker liveness during upstream model loading and long device operations.
        while not stop_heartbeat.wait(30):
            heartbeat = args.output_dir / "heartbeat.json"
            if not heartbeat.exists() or time.time() - heartbeat.stat().st_mtime > 45:
                write_heartbeat(heartbeat, "worker-alive")
    threading.Thread(target=keep_alive, daemon=True).start()
    path = args.output_dir / (args.mode + ("-" + args.candidate if args.mode == "test" else "") + "-run.json")
    try:
        write_heartbeat(args.output_dir / "heartbeat.json", "loading")
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        result = {"train-encoder": train_encoder, "select": select, "test": test}[args.mode](args, run, device)
        metadata.update({"status": "completed", "runtime_seconds": time.time() - started, "wandb_run_id": run.id, "wandb_run_url": run.url, "result": result})
        save_json(path, metadata)
        save_json(args.output_dir / "metrics.json", {**metadata, **result})
        write_heartbeat(args.output_dir / "heartbeat.json", "completed")
        run.summary.update({"status": "completed", "runtime_seconds": metadata["runtime_seconds"], "result_artifact": str(path)})
    except BaseException as error:
        metadata.update({"status": "failed", "error": repr(error), "runtime_seconds": time.time() - started, "wandb_run_id": run.id, "wandb_run_url": run.url})
        save_json(path, metadata)
        save_json(args.output_dir / "metrics.json", {**metadata, **result})
        write_heartbeat(args.output_dir / "heartbeat.json", "failed")
        run.summary.update({"status": "failed", "error": repr(error)})
        raise
    finally:
        stop_heartbeat.set()
        run.finish()
    return 0


if __name__ == "__main__":
    # Return the worker status to the research supervisor.
    raise SystemExit(main())
