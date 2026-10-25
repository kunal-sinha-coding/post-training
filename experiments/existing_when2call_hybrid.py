"""Measure fixed hybrids of existing When2Call encoders and the trained Qwen SFT model.

Preparation freezes existing checkpoint hashes and four predeclared hybrid rules without
training or development selection. One aggregate measurement scores each model once,
restores source row order after encoder batching, and compares fixed hybrids and baselines.
The initial suite preserves both encoder families. The single-fusion suite compares fixed pooling rules.
The single-route suite tests a class-specialized encoder route. The single-weighted suite tests a fixed asymmetric blend. The single-adaptive suite tests confidence-weighted pooling and selective overrides. The single-rules suite routes by visible question and tool features.
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
SINGLE_METHODS = ("single_average", "single_gate", "single_geometric", "single_rank")
SINGLE_RULES = {"average": "Arithmetic mean of the two probability vectors with equal weights.", "gate": "Choose the lower-entropy probability vector with encoder first on exact ties.", "geometric": "Softmax of the equal mean of log probabilities clamped below at 1e-8.", "rank": "Sum equal Borda rank points from both experts. Average rank points for tied probabilities. Add 1e-6 times arithmetic mean probability, clamp below at 1e-12, and normalize."}
ROUTE_METHODS = ("single_average", "single_gate", "single_encoder_refusal")
ROUTE_RULES = {"encoder_refusal": "Use the encoder when its top class is cannot_answer. Use Qwen for every other encoder prediction. The class boundary is fixed from the earlier Jina plus Jev routing hypothesis and is not fitted here."}
WEIGHTED_METHODS = ("single_average", "single_gate", "single_qwen_weighted")
WEIGHTED_RULES = {"qwen_weighted": "Combine 0.25 encoder probability with 0.75 Qwen probability. These weights are fixed before test loading."}
ADAPTIVE_METHODS = ("single_average", "single_gate", "single_entropy_weighted", "single_margin_weighted", "single_encoder_confident")
ADAPTIVE_RULES = {"entropy_weighted": "Weight each expert by 1 minus its normalized predictive entropy, with equal weights if both are uniform.", "margin_weighted": "Weight each expert by its top probability minus its second highest probability, with equal weights if both margins are zero.", "encoder_confident": "Use encoder probabilities only when its top-two probability margin is at least 0.50 and exceeds the Qwen margin. Otherwise use Qwen probabilities."}
RULE_METHODS = ("single_average", "single_gate", "single_encoder_no_tools", "single_encoder_many_tools", "single_encoder_short_question", "single_encoder_long_question")
RULES = {"no_tools": "Use the encoder when no tools are available.", "many_tools": "Use the encoder when at least two tools are available.", "short_question": "Use the encoder when the question has at most 20 whitespace-delimited words.", "long_question": "Use the encoder when the question has more than 20 whitespace-delimited words."}


def suite_definition(name: str) -> dict:
    # Declare each suite independently without searching weights or fitting parameters.
    if name == "initial":
        return {"encoders": ENCODERS, "weights": WEIGHTS, "single_index": 2, "methods": list(METHODS), "primary": "ensemble_average"}
    if name == "single-fusion":
        return {"encoders": [ENCODERS[2]], "weights": [1.0], "single_index": 0, "methods": list(SINGLE_METHODS), "primary": "single_geometric"}
    if name == "single-route":
        return {"encoders": [ENCODERS[2]], "weights": [1.0], "single_index": 0, "methods": list(ROUTE_METHODS), "primary": "single_encoder_refusal"}
    if name == "single-weighted":
        return {"encoders": [ENCODERS[2]], "weights": [1.0], "single_index": 0, "methods": list(WEIGHTED_METHODS), "primary": "single_qwen_weighted"}
    if name == "single-adaptive":
        return {"encoders": [ENCODERS[2]], "weights": [1.0], "single_index": 0, "methods": list(ADAPTIVE_METHODS), "primary": "single_entropy_weighted"}
    if name == "single-rules":
        return {"encoders": [ENCODERS[2]], "weights": [1.0], "single_index": 0, "methods": list(RULE_METHODS), "primary": "single_encoder_no_tools"}
    raise ValueError("Unknown frozen suite: " + name)


def encoder_families(logits: torch.Tensor, weights: list[float]) -> tuple[torch.Tensor, torch.Tensor]:
    # Preserve the standalone encoder and historical weighted raw-logit ensemble definitions.
    weight = torch.tensor(weights, dtype=logits.dtype).view(-1, 1, 1)
    return logits[2].softmax(-1), (logits * weight).sum(0).softmax(-1)


def hybrid_probabilities(encoder: torch.Tensor, qwen: torch.Tensor, rule: str) -> torch.Tensor:
    # Apply the predeclared probability, entropy, geometric, or ordinal fusion rule.
    if rule == "average":
        return (encoder + qwen) / 2
    probabilities = torch.stack((encoder, qwen), dim=1)
    if rule == "geometric":
        return probabilities.clamp_min(1e-8).log().mean(1).softmax(-1)
    if rule == "rank":
        # Average tied ranks so uniform or identical experts do not introduce an index preference.
        lower = probabilities.unsqueeze(-1) > probabilities.unsqueeze(-2)
        equal = probabilities.unsqueeze(-1) == probabilities.unsqueeze(-2)
        points = lower.sum(-1).double() + (equal.sum(-1).double() - 1) / 2
        scores = (points.sum(1) + 1e-6 * probabilities.double().mean(1)).clamp_min(1e-12)
        return scores / scores.sum(-1, keepdim=True)
    if rule == "gate":
        entropy = -(probabilities.clamp_min(1e-8).log() * probabilities).sum(-1)
        return probabilities[torch.arange(len(probabilities)), entropy.argmin(1)]
    if rule == "encoder_refusal":
        # Keep the encoder refusal region and use Qwen for the other predicted classes.
        use_encoder = encoder.argmax(-1).eq(LABELS.index("cannot_answer")).unsqueeze(-1)
        return torch.where(use_encoder, encoder, qwen)
    if rule == "qwen_weighted":
        # Shrink the weaker standalone encoder toward the stronger Qwen baseline.
        return 0.25 * encoder + 0.75 * qwen
    if rule == "entropy_weighted":
        # Give each expert a soft share based on normalized predictive entropy.
        confidence = 1 + probabilities.clamp_min(1e-8).log().mul(probabilities).sum(-1) / torch.log(torch.tensor(float(probabilities.shape[-1]), device=probabilities.device))
        weights = confidence / confidence.sum(-1, keepdim=True).clamp_min(1e-12)
        weights = torch.where(confidence.sum(-1, keepdim=True) > 1e-12, weights, torch.full_like(weights, 0.5))
        return (weights.unsqueeze(-1) * probabilities).sum(1)
    if rule == "margin_weighted":
        # Give each expert a soft share based on its top-two probability margin.
        top = probabilities.topk(2, dim=-1).values
        confidence = (top[..., 0] - top[..., 1]).clamp_min(0)
        weights = confidence / confidence.sum(-1, keepdim=True).clamp_min(1e-12)
        weights = torch.where(confidence.sum(-1, keepdim=True) > 1e-12, weights, torch.full_like(weights, 0.5))
        return (weights.unsqueeze(-1) * probabilities).sum(1)
    if rule == "encoder_confident":
        # Override Qwen only when the encoder has a strong and larger probability margin.
        top = probabilities.topk(2, dim=-1).values
        margins = top[..., 0] - top[..., 1]
        use_encoder = (margins[:, 0] >= 0.50) & (margins[:, 0] > margins[:, 1])
        return torch.where(use_encoder.unsqueeze(-1), encoder, qwen)
    raise ValueError("Unknown frozen hybrid rule: " + rule)


def input_route_mask(rows: list, rule: str, device: torch.device) -> torch.Tensor:
    """Build an inference-only route mask from visible question and tool fields."""
    # Select the declared input feature without reading target labels or model correctness.
    if rule == "no_tools":
        values = [len(row["tools"]) == 0 for row in rows]
    elif rule == "many_tools":
        values = [len(row["tools"]) >= 2 for row in rows]
    elif rule == "short_question":
        values = [len(str(row["question"]).split()) <= 20 for row in rows]
    elif rule == "long_question":
        values = [len(str(row["question"]).split()) > 20 for row in rows]
    else:
        raise ValueError("Unknown input route rule: " + rule)
    return torch.tensor(values, dtype=torch.bool, device=device)


def prepare(args: object, run: object) -> dict:
    # Freeze only the selected suite artifacts and exact rules before opening official examples.
    suite_name = getattr(args, "suite", "initial")
    suite = suite_definition(suite_name)
    artifacts = []
    for checkpoint in suite["encoders"]:
        artifacts.extend(Path(checkpoint) / name for name in ("model_state.pt", "encoder_config.json"))
    artifacts.extend(Path(QWEN) / name for name in ("adapter_model.safetensors", "adapter_config.json"))
    artifacts.append(Path("outputs/when2call-jina-v2-small/latest/tokenizer.json"))
    config = {"selection_complete": True, "training_performed": False, "development_selection_performed": False, "suite": suite_name, "encoders": suite["encoders"], "encoder_logit_weights": suite["weights"], "single_encoder_index": suite["single_index"], "qwen_checkpoint": QWEN, "qwen_base": QWEN_BASE, "qwen_output_permutation": [0, 1, 2, 3], "label_order": LABELS, "max_length": 4096, "methods": suite["methods"], "primary_method": suite["primary"], "family_probability_weights": [0.5, 0.5], "artifact_sha256": {str(path): artifact_digest(path) for path in artifacts}, "validation_limitation": "Existing encoder warm starts saw all train_pref rows. No clean preference validation is claimed or used for selection.", "historical_selection_limitation": "Existing encoder approaches were identified in prior research with repeated official benchmark inspection. This fixed comparison is a benchmark measurement, not a new independent generalization estimate.", "metric_definition": "Primary macro F1 includes all four declared classes. The present-class macro F1 diagnostic permits comparison with historical encoder reports.", "qwen_mapping": "Historical adapter training used LABEL_TO_ID directly despite reversed ABCD descriptions in its prompt. Preserve learned identity indices.", "test_status": "queued"}
    if suite_name == "single-fusion":
        config["fusion_rules"] = SINGLE_RULES
        config["hypothesis"] = "Geometric consensus tests shared support while ordinal Borda fusion tests robustness to unequal expert confidence scales. Arithmetic averaging and entropy gating are unchanged controls."
    if suite_name == "single-route":
        config["fusion_rules"] = ROUTE_RULES
        config["hypothesis"] = "A fixed class-specialized route transfers the earlier encoder plus Jev complementarity hypothesis: keep encoder cannot_answer decisions and use Qwen for other encoder decisions. Compare with arithmetic averaging and entropy gating. Earlier class routing was selected using benchmark labels, so this is a predeclared exploratory aggregate measurement, not an unbiased estimate."
    if suite_name == "single-weighted":
        config["fusion_rules"] = WEIGHTED_RULES
        config["hypothesis"] = "The encoder improves the Qwen baseline when averaged equally, but has lower standalone accuracy. A fixed 25 percent encoder and 75 percent Qwen blend tests whether shrinkage toward the stronger Qwen baseline improves accuracy. Compare with equal averaging and minimum-entropy gating. The fixed weight is not fitted."
    if suite_name == "single-adaptive":
        config["fusion_rules"] = ADAPTIVE_RULES
        config["hypothesis"] = "Test distinct adaptive ensemble mechanisms in one frozen score pass: soft weights from predictive entropy, soft weights from top-two margins, and a fixed high-margin encoder override. Compare with equal averaging and minimum-entropy gating. No thresholds are swept."
    if suite_name == "single-rules":
        config["fusion_rules"] = RULES
        config["hypothesis"] = "Test whether visible task type should select the expert: no available tools, at least two tools, short questions, or long questions. Each fixed rule uses the encoder in only its declared region and Qwen otherwise. Compare with equal averaging and minimum-entropy gating. Rules use input fields only and are not fitted."
    save_json(args.work_dir / "frozen-config.json", config)
    run.summary.update({"selection_complete": True, "training_performed": False, "test_status": "queued"})
    return {"status": "completed", "test_status": "queued", "frozen_configuration": config}


def verify_frozen(config: dict) -> None:
    # Reject changed artifacts or method definitions before the official loader is imported or called.
    suite_name = config.get("suite", "initial")
    suite = suite_definition(suite_name)
    if not config["selection_complete"] or config["encoders"] != suite["encoders"] or config["qwen_checkpoint"] != QWEN or config["methods"] != suite["methods"] or config["encoder_logit_weights"] != suite["weights"] or config["primary_method"] != suite["primary"]:
        raise ValueError("Frozen existing-model comparison configuration changed.")
    if suite_name == "single-fusion" and (config.get("fusion_rules") != SINGLE_RULES or config.get("single_encoder_index") != 0 or config.get("qwen_base") != QWEN_BASE or config.get("max_length") != 4096 or config.get("qwen_output_permutation") != [0, 1, 2, 3] or config.get("family_probability_weights") != [0.5, 0.5]):
        raise ValueError("Frozen single-fusion rules changed.")
    if suite_name == "single-route" and (config.get("fusion_rules") != ROUTE_RULES or config.get("single_encoder_index") != 0 or config.get("qwen_base") != QWEN_BASE or config.get("max_length") != 4096 or config.get("qwen_output_permutation") != [0, 1, 2, 3] or config.get("family_probability_weights") != [0.5, 0.5]):
        raise ValueError("Frozen single-route rules changed.")
    if suite_name == "single-weighted" and (config.get("fusion_rules") != WEIGHTED_RULES or config.get("single_encoder_index") != 0 or config.get("qwen_base") != QWEN_BASE or config.get("max_length") != 4096 or config.get("qwen_output_permutation") != [0, 1, 2, 3] or config.get("family_probability_weights") != [0.5, 0.5]):
        raise ValueError("Frozen single-weighted rules changed.")
    if suite_name == "single-adaptive" and (config.get("fusion_rules") != ADAPTIVE_RULES or config.get("single_encoder_index") != 0 or config.get("qwen_base") != QWEN_BASE or config.get("max_length") != 4096 or config.get("qwen_output_permutation") != [0, 1, 2, 3] or config.get("family_probability_weights") != [0.5, 0.5]):
        raise ValueError("Frozen single-adaptive rules changed.")
    if suite_name == "single-rules" and (config.get("fusion_rules") != RULES or config.get("single_encoder_index") != 0 or config.get("qwen_base") != QWEN_BASE or config.get("max_length") != 4096 or config.get("qwen_output_permutation") != [0, 1, 2, 3] or config.get("family_probability_weights") != [0.5, 0.5]):
        raise ValueError("Frozen single-rules definitions changed.")
    for path, expected in config["artifact_sha256"].items():
        if artifact_digest(Path(path)) != expected:
            raise ValueError("Frozen comparison artifact changed: " + path)


def encoder_logits(checkpoint: str, examples: list, args: object, device: torch.device) -> torch.Tensor:
    # Score bounded encoder inputs and restore source order after length-sorted inference.
    model, tokenizer = load_checkpoint(Path(checkpoint), device, 4096)
    assert_size(model)
    for example in examples:
        example.token_ids = tokenizer(example.text, add_special_tokens=True, truncation=False, verbose=False)["input_ids"][:4096]
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
    # Measure every frozen hybrid and baseline from one sequential pass through its model members.
    config_path = args.work_dir / "frozen-config.json"
    config = json.loads(config_path.read_text())
    verify_frozen(config)
    if getattr(args, "suite", "initial") != config.get("suite", "initial"):
        raise ValueError("The requested suite does not match its frozen manifest.")
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
    if config.get("suite", "initial") == "initial":
        single, ensemble = encoder_families(torch.stack(encoder_scores), config["encoder_logit_weights"])
    else:
        single, ensemble = encoder_scores[0].softmax(-1), None
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
    probabilities = {"encoder_single": single, "qwen_sft": qwen}
    if ensemble is not None:
        probabilities["encoder_ensemble"] = ensemble
    for method in config["methods"]:
        family_name, rule = method.split("_", 1)
        family = single if family_name == "single" else ensemble
        if rule in RULES:
            mask = input_route_mask(rows, rule, single.device)
            probabilities[method] = torch.where(mask.unsqueeze(-1), single, qwen)
        else:
            probabilities[method] = hybrid_probabilities(family, qwen, rule)
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
    parser.add_argument("--suite", choices=("initial", "single-fusion", "single-route", "single-weighted", "single-adaptive", "single-rules"), default="initial")
    parser.add_argument("--batch-size", type=int, default=1)
    args = parser.parse_args()
    import wandb
    if not os.getenv("WANDB_API_KEY"):
        raise RuntimeError("WANDB_API_KEY is required.")
    args.work_dir.mkdir(parents=True, exist_ok=True)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    suite = suite_definition(args.suite)
    metadata = {"command": [sys.executable, *sys.argv], "git_commit": subprocess.check_output(["git", "-c", "safe.directory=/workspace/post-training", "rev-parse", "HEAD"], text=True).strip(), "configuration": {key: str(value) if isinstance(value, Path) else value for key, value in vars(args).items()}, "suite": args.suite, "encoders": suite["encoders"], "encoder_logit_weights": suite["weights"], "qwen_checkpoint": QWEN, "max_length": 4096, "primary_method": suite["primary"]}
    run = wandb.init(project=os.getenv("WANDB_PROJECT", "when2call-research"), entity=os.getenv("WANDB_ENTITY"), name="existing-when2call-hybrid-" + args.suite + "-" + args.mode, job_type="existing-hybrid-" + args.mode, config=metadata)
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
        run.summary.update({"status": "completed", "runtime_seconds": metadata["runtime_seconds"], "primary_method": suite["primary"]})
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
