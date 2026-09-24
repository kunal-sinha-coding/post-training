# This file runs the complete MBPP training flow from configuration loading through evaluation.
# It prepares data and models, optionally runs SFT, and then runs GRPO.
# It records metrics, selects checkpoints, and saves the final artifacts.

from __future__ import annotations

import argparse
import json
import os
import random
import re
import shutil
from collections import defaultdict, deque
from pathlib import Path
from pprint import pformat
import copy
from typing import Any

import yaml
from dotenv import load_dotenv

from data import build_sft_dataset, prepare_datasets
from evaluate import QWEN_EVALPLUS_STOP_STRINGS, append_training_step_header, append_training_step_metrics, append_training_step_samples, append_evaluation_log, code_fence_stopping_criteria, evaluate_model, evaluate_texts, forced_code_prefix_length, forced_code_prefix_processor, mask_completion_tokens_after_stop, save_evaluation, start_run_log, stop_token_id_sequences
from sandbox import reward_function, wrap_qwen_continuation


def load_config(path: str | Path) -> dict[str, Any]:
    """Load one YAML experiment configuration."""
    with Path(path).open(encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def run_qwen_evalplus(model_path: Path, output_dir: Path, name: str) -> dict[str, Any]:
    """Run the official Qwen EvalPlus MBPP and MBPP+ evaluation for one saved model."""
    # Generate the complete canonical MBPP task set directly inside the training process.
    evaluation_dir = output_dir / "evalplus" / name
    evaluation_dir.mkdir(parents=True, exist_ok=True)
    from experiments.run_qwen_official_greedy_eval import generate_evalplus_samples

    # Keep vLLM generation in the training process while using the canonical EvalPlus layout.
    samples = generate_evalplus_samples(model_path, evaluation_dir)
    samples = evaluation_dir / "mbpp" / "qwen2_chat_temp_0.0"
    # Evaluate the generated directory through EvalPlus in the training process.
    from contextlib import redirect_stdout
    from io import StringIO
    from types import SimpleNamespace
    from evalplus.evaluate import evaluate

    evaluator_args = SimpleNamespace(dataset="mbpp", samples=str(samples), base_only=False, parallel=None, i_just_wanna_run=False, test_details=True, min_time_limit=1, gt_time_limit_factor=4.0, mini=False, noextreme=False)
    evaluator_output = StringIO()
    with redirect_stdout(evaluator_output):
        evaluate(evaluator_args)
    result_text = evaluator_output.getvalue()
    result_path = evaluation_dir / "mbpp_results.txt"
    result_path.write_text(result_text, encoding="utf-8")
    print(result_text, end="", flush=True)
    # Extract both canonical pass rates so the caller can publish scalar metrics.
    base_match = re.search(r"mbpp \(base tests\).*?pass@1:\s*([0-9.]+)", result_text, re.DOTALL)
    plus_match = re.search(r"mbpp\+ \(base \+ extra tests\).*?pass@1:\s*([0-9.]+)", result_text, re.DOTALL)
    # Compute per-test pass fractions from the detailed canonical evaluator output.
    detail_metrics = canonical_test_pass_metrics(samples)
    metrics = {
        "mbpp_pass_at_1": float(base_match.group(1)) if base_match else None,
        "mbpp_plus_pass_at_1": float(plus_match.group(1)) if plus_match else None,
        **detail_metrics,
    }
    return {"evaluation_dir": str(evaluation_dir), "results": result_text, "metrics": metrics}


def canonical_test_pass_metrics(samples: Path) -> dict[str, float]:
    """Calculate overall base and MBPP+ test pass fractions from EvalPlus details."""
    # Read the canonical evaluator's per-task failure lists and compare them with official test counts.
    from evalplus.data import get_mbpp_plus

    results = json.loads((samples / "eval_results.json").read_text(encoding="utf-8"))["eval"]
    problems = get_mbpp_plus()
    base_total = plus_total = base_passed = plus_passed = 0
    base_partial = plus_partial = base_any = plus_any = 0
    for task_id, task_results in results.items():
        result = task_results[0]
        problem = problems[task_id]
        base_count = len(problem["base_input"])
        plus_count = len(problem["base_input"]) + len(problem["plus_input"])
        base_total += base_count
        plus_total += plus_count
        base_passed += base_count - len(result["base_fail_tests"])
        plus_passed += plus_count - len(result["plus_fail_tests"])
        base_completed = base_count - len(result["base_fail_tests"])
        plus_completed = plus_count - len(result["plus_fail_tests"])
        base_partial += int(0 < base_completed < base_count)
        plus_partial += int(0 < plus_completed < plus_count)
        base_any += int(base_completed > 0)
        plus_any += int(plus_completed > 0)
    return {
        "mbpp_tests_pass_fraction": base_passed / base_total if base_total else 0.0,
        "mbpp_plus_tests_pass_fraction": plus_passed / plus_total if plus_total else 0.0,
        "mbpp_partial_pass_fraction": base_partial / len(results) if results else 0.0,
        "mbpp_partial_or_full_pass_fraction": base_any / len(results) if results else 0.0,
        "mbpp_plus_partial_pass_fraction": plus_partial / len(results) if results else 0.0,
        "mbpp_plus_partial_or_full_pass_fraction": plus_any / len(results) if results else 0.0,
    }


def evaluate_training_mbpp(model_path: Path, train_dataset: Any, config: dict[str, Any], name: str) -> dict[str, Any]:
    """Evaluate all training tasks with the same batched vLLM generation path as EvalPlus."""
    # Generate one greedy completion per training task from the merged base or adapter checkpoint.
    from experiments.run_qwen_official_greedy_eval import generate_model_completions

    records = [train_dataset[index] for index in range(len(train_dataset))]
    completions = generate_model_completions(model_path, [record["prompt"] for record in records])
    # Wrap raw vLLM code bodies so the shared scorer can extract them as Python programs.
    completions = [wrap_qwen_continuation(completion) for completion in completions]
    # Score generated solutions against only the original MBPP tests used by the reward.
    metrics, details = evaluate_texts(completions, records, float(config.get("sandbox_timeout_seconds", 3)), config.get("log_path", "logs/logs.txt"), name, reward_scoring_workers=int(config.get("reward_scoring_workers", 8)))
    return {"metrics": metrics, "details": details}


def merge_training_metrics(metrics: dict[str, Any], training_metrics: dict[str, Any]) -> dict[str, Any]:
    """Add training-set MBPP pass@1 and test pass fraction with explicit metric names."""
    # Prefix only the two requested training metrics to keep W&B evaluation rows unambiguous.
    merged = dict(metrics)
    merged["training_mbpp_pass_at_1"] = float(training_metrics.get("pass_at_1", 0.0))
    merged["training_mbpp_tests_pass_fraction"] = float(training_metrics.get("tests_pass_fraction", 0.0))
    merged["training_mbpp_partial_pass_fraction"] = float(training_metrics.get("partial_pass_fraction", 0.0))
    merged["training_mbpp_partial_or_full_pass_fraction"] = float(training_metrics.get("partial_or_full_pass_fraction", 0.0))
    return merged


def build_peft_config(config: dict[str, Any]) -> Any | None:
    """Build the optional LoRA adapter configuration used to fit GRPO in GPU memory."""
    # Keep full fine tuning available while defaulting to the memory-safe adapter path for the 3B model.
    if not config.get("lora_enabled", False):
        return None
    from peft import LoraConfig

    return LoraConfig(
        task_type="CAUSAL_LM",
        r=int(config.get("lora_r", 16)),
        lora_alpha=int(config.get("lora_alpha", 32)),
        lora_dropout=float(config.get("lora_dropout", 0.05)),
        target_modules=list(config.get("lora_target_modules", ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"])),
    )


def seed_everything(seed: int) -> None:
    """Seed Python and available numerical frameworks for reproducibility."""
    # Seed Python before seeding optional numerical frameworks.
    random.seed(seed)
    # Seed NumPy when it is installed.
    try:
        import numpy as np
        np.random.seed(seed)
    except ImportError:
        pass
    # Seed PyTorch and every available CUDA device when PyTorch is installed.
    try:
        import torch
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
    except ImportError:
        pass


def configure_wandb(config: dict[str, Any]) -> Any | None:
    """Load the local W&B key and authenticate when W&B logging is enabled."""
    # Skip W&B setup when the configuration disables reporting.
    if config.get("report_to") in (None, "none", []):
        return None
    # Import W&B or report the missing logging dependency.
    try:
        import wandb
    except ImportError as exc:
        raise RuntimeError("W&B logging is enabled, but wandb is not installed.") from exc
    # Require an API key before authenticating the W&B client.
    api_key = os.getenv("WANDB_API_KEY")
    if not api_key:
        raise RuntimeError("W&B logging is enabled, but WANDB_API_KEY is missing from the environment.")
    # Authenticate and set the default project for this process.
    wandb.login(key=api_key, relogin=False)
    os.environ.setdefault("WANDB_PROJECT", str(config.get("wandb_project", "grpo-mbpp")))
    # Start one shared run before baseline evaluation and both training stages.
    if wandb.run is None:
        wandb.init(project=str(config.get("wandb_project", "grpo-mbpp")), name=config.get("wandb_run_name"))
    # Use trainer steps rather than W&B history row numbers on evaluation charts.
    if hasattr(wandb, "define_metric"):
        wandb.define_metric("evaluation/step")
        wandb.define_metric("evaluation/*", step_metric="evaluation/step")
    return wandb


def log_evaluation(wandb: Any | None, metrics: dict[str, Any], evaluation_name: str, step: int | None = None) -> None:
    """Log one evaluation event with a shared custom W&B x-axis."""
    # Skip evaluation logging when no active W&B run exists.
    if wandb is None or wandb.run is None:
        return
    # Build the common evaluation metadata payload.
    payload: dict[str, Any] = {
        "evaluation/step": float(step or 0),
        "evaluation/name": evaluation_name,
    }
    # Add scalar metrics and flattened status counts to the payload.
    for key, value in metrics.items():
        if isinstance(value, (int, float)):
            payload[f"evaluation/{key}"] = value
        elif key == "status_counts" and isinstance(value, dict):
            for status, count in value.items():
                payload[f"evaluation/status_{status}"] = count

    # Publish the requested pass@1 spelling while retaining the existing metric key.
    if isinstance(metrics.get("pass_at_1"), (int, float)):
        payload["evaluation/pass@1"] = metrics["pass_at_1"]
    wandb.log(payload)


def load_cached_evaluation(output_dir: Path, name: str) -> tuple[dict[str, Any], list[dict[str, Any]]] | None:
    """Load a complete cached evaluation when both JSON artifacts are present."""
    # Resolve the paired metrics and details artifacts.
    metrics_path = output_dir / f"{name}-metrics.json"
    details_path = output_dir / f"{name}-details.json"
    # Reject incomplete cached evaluations.
    if not metrics_path.is_file() or not details_path.is_file():
        return None
    # Load the cached metrics artifact.
    with metrics_path.open(encoding="utf-8") as handle:
        metrics = json.load(handle)
    # Load the cached details artifact.
    with details_path.open(encoding="utf-8") as handle:
        details = json.load(handle)
    return metrics, details


def _make_reward(config: dict[str, Any]):
    """Bind sandbox configuration to the TRL reward-function contract."""
    # Resolve the sandbox timeout and reward selection once for the reward closure.
    timeout = float(config.get("sandbox_timeout_seconds", 3))
    reward_function_name = str(config.get("reward_function", "test_pass"))
    reward_coefficient = float(config.get("reward_coefficient", 0.5))
    reward_scoring_workers = int(config.get("reward_scoring_workers", 8))

    def reward(completions: list[object], test_code: list[str], **kwargs: object) -> list[float]:
        """Score the current GRPO completion batch."""
        # Share reward diagnostics with the training callback for W&B and local logs.
        diagnostics: dict[str, float] = {}
        append_training_step_samples(config.get("log_path", "logs/logs.txt"), completions)
        task_ids = kwargs.get("task_id")
        task_id_values = task_ids if isinstance(task_ids, list) else None
        rewards = reward_function(completions, test_code, timeout, diagnostics=diagnostics, group_size=int(config.get("num_generations", 4)), reward_function_name=reward_function_name, reward_coefficient=reward_coefficient, trace_path=config.get("reward_trace_path"), task_ids=task_id_values, synthetic_reward_probe=bool(config.get("synthetic_reward_probe", False)), reward_scoring_workers=reward_scoring_workers, **kwargs)
        # Record the generated completion token lengths so truncation and length drift are visible in W&B.
        completion_ids = kwargs.get("completion_ids")
        if isinstance(completion_ids, list) and completion_ids:
            completion_lengths = [len(ids) for ids in completion_ids]
            diagnostics["training/completion_tokens_mean"] = sum(completion_lengths) / len(completion_lengths)
            diagnostics["training/completion_tokens_min"] = min(completion_lengths)
            diagnostics["training/completion_tokens_max"] = max(completion_lengths)
            diagnostics["training/completion_tokens_truncated_fraction"] = sum(
                length >= int(config.get("max_completion_length", 2048)) for length in completion_lengths
            ) / len(completion_lengths)
        # Record the number of hidden assertions exercised by this reward batch.
        synthetic_counts = kwargs.get("synthetic_test_count", [])
        if isinstance(synthetic_counts, list) and synthetic_counts:
            diagnostics["reward/synthetic_tests/mean"] = sum(float(count) for count in synthetic_counts) / len(synthetic_counts)
        config["_reward_diagnostics"] = diagnostics
        return rewards

    return reward

def _probe_per_token_logps(model: Any, batch: dict[str, Any], temperature: float = 1.0, chunk_size: int = 4) -> Any:
    """Compute masked-completion token log probabilities for a saved rollout batch."""
    # Reconstruct the same completion-token logits used by the installed TRL GRPO loss.
    import torch
    per_token_logps = []
    for start in range(0, batch["prompt_ids"].shape[0], chunk_size):
        # Recompute a small batched slice so the diagnostic does not change training memory requirements.
        input_ids = torch.cat([batch["prompt_ids"][start : start + chunk_size], batch["completion_ids"][start : start + chunk_size]], dim=1)
        attention_mask = torch.cat([batch["prompt_mask"][start : start + chunk_size], batch["completion_mask"][start : start + chunk_size]], dim=1)
        completion_length = batch["completion_ids"].shape[1]
        logits = model(input_ids=input_ids, attention_mask=attention_mask, use_cache=False).logits
        logits = logits[:, :-1, :]
        logits = logits[:, -completion_length:, :] / temperature
        token_ids = input_ids[:, -completion_length:]
        token_logps = torch.log_softmax(logits, dim=-1).gather(-1, token_ids.unsqueeze(-1)).squeeze(-1)
        per_token_logps.append(token_logps)
    return torch.cat(per_token_logps)


def _probe_sequence_logps(model: Any, batch: dict[str, Any], temperature: float = 1.0, chunk_size: int = 4) -> Any:
    """Compute mean masked-completion log probabilities for a saved rollout batch."""
    # Reduce the shared token likelihoods into the four existing sample-level direction metrics.
    token_logps = _probe_per_token_logps(model, batch, temperature, chunk_size)
    mask = batch["completion_mask"].float()
    return (token_logps * mask).sum(dim=1) / mask.sum(dim=1).clamp(min=1.0)


def _probe_dapo_surrogate(per_token_logps: Any, old_per_token_logps: Any, advantages: Any, completion_mask: Any) -> Any:
    """Calculate the masked DAPO surrogate used by the installed TRL trainer."""
    import torch

    # Apply the same token-level importance ratio and default two-sided clipping as TRL.
    ratio = torch.exp(per_token_logps - old_per_token_logps)
    clipped_ratio = torch.clamp(ratio, 0.8, 1.2)
    token_loss = -torch.minimum(ratio * advantages.unsqueeze(1), clipped_ratio * advantages.unsqueeze(1))
    return (token_loss * completion_mask.float()).sum() / completion_mask.sum().clamp(min=1.0)


def _probe_token_row_key(token_ids: Any) -> tuple[int, ...]:
    """Build a stable key for matching one shuffled completion to its reward."""
    # Preserve the padded row because TRL shuffles token rows without changing their contents.
    return tuple(int(token_id) for token_id in token_ids.tolist())


def _make_callback(model: Any, tokenizer: Any, train_dataset: Any, test_dataset: Any, config: dict[str, Any], wandb: Any | None, device: Any | None = None):
    """Create callbacks for step logging and checkpoint evaluation."""
    # Import the callback base class only when training starts.
    from transformers import TrainerCallback

    # Define the GRPO callback with access to the current training objects.
    class TrainingCallback(TrainerCallback):
        """Log each training step and evaluate saved checkpoints."""

        def __init__(self) -> None:
            """Track the best checkpoint selected by intermediate pass rate."""
            # Initialize checkpoint, cumulative, and rolling metric state.
            self.evaluation_model = model
            self.initial_trainable_parameters: dict[str, Any] = {}
            self.pre_optimizer_parameters: dict[str, Any] = {}
            self.best_checkpoint_path: Path | None = None
            self.best_metric = float("-inf")
            self.best_evalplus_mbpp_plus = float(config.get("_best_evalplus_mbpp_plus", float("-inf")))
            self.evaluations_without_improvement = 0
            self.reward_sum = 0.0
            self.reward_count = 0
            self.component_reward_sums: dict[str, float] = {}
            self.component_reward_counts: dict[str, int] = {}
            self.rolling_window_size = max(1, int(config.get("reward_rolling_window", 10)))
            self.rolling_reward_values: deque[float] = deque(maxlen=self.rolling_window_size)
            self.rolling_component_values: dict[str, deque[float]] = {
                component: deque(maxlen=self.rolling_window_size)
                for component in ("format", "syntax", "interface", "test_progress", "pass")
            }
            self.next_eval_step = max(1, int(config.get("evalplus_eval_steps", 10)))

        def set_evaluation_model(self, model: Any) -> None:
            """Attach the PEFT-wrapped model and record its initial trainable parameters."""
            # Store the model that the optimizer actually updates.
            self.evaluation_model = model
            # Snapshot trainable LoRA parameters before the first optimizer update.
            self.initial_trainable_parameters = {
                name: parameter.detach().float().cpu().clone()
                for name, parameter in model.named_parameters()
                if parameter.requires_grad
            }

        def on_pre_optimizer_step(self, args: Any, state: Any, control: Any, **_: Any) -> Any:
            """Snapshot trainable parameters immediately before each optimizer update."""
            # Capture CPU copies so the measured delta covers only one optimizer step.
            self.pre_optimizer_parameters = {
                name: parameter.detach().float().cpu().clone()
                for name, parameter in self.evaluation_model.named_parameters()
                if parameter.requires_grad
            }
            # Record the raw gradient norm before Adam transforms the gradients.
            gradient_sq = sum(
                float(parameter.grad.detach().float().pow(2).sum())
                for parameter in self.evaluation_model.parameters()
                if parameter.requires_grad and parameter.grad is not None
            )
            config["_update_diagnostics"] = {"training/raw_gradient_norm": gradient_sq**0.5}
            return control

        def on_optimizer_step(self, args: Any, state: Any, control: Any, **_: Any) -> Any:
            """Measure the actual LoRA parameter movement after each optimizer update."""
            # Compute update and parameter norms from the before and after snapshots.
            update_sq = 0.0
            parameter_sq = 0.0
            initial_delta_sq = 0.0
            for name, parameter in self.evaluation_model.named_parameters():
                if not parameter.requires_grad or name not in self.pre_optimizer_parameters:
                    continue
                current = parameter.detach().float().cpu()
                before = self.pre_optimizer_parameters[name]
                initial = self.initial_trainable_parameters.get(name, before)
                update_sq += float((current - before).pow(2).sum())
                parameter_sq += float(current.pow(2).sum())
                initial_delta_sq += float((current - initial).pow(2).sum())
            update_norm = update_sq**0.5
            config["_update_diagnostics"].update({
                "training/parameter_update_norm": update_norm,
                "training/relative_parameter_update": update_norm / (parameter_sq**0.5 + 1e-12),
                "training/lora_delta_from_initial_norm": initial_delta_sq**0.5,
            })
            probe_batches = config.pop("_direction_probe_batches", None)
            if probe_batches:
                # Compare the post-update likelihood of positive and negative advantage samples.
                import torch
                probe_batch = {
                    "batch": {key: torch.cat([item["batch"][key] for item in probe_batches]) for key in probe_batches[0]["batch"]},
                    "old_logps": torch.cat([item["old_logps"] for item in probe_batches]),
                    "current_pre_per_token_logps": torch.cat([item["current_pre_per_token_logps"] for item in probe_batches]),
                    "loss_old_per_token_logps": torch.cat([item["loss_old_per_token_logps"] for item in probe_batches]),
                    "advantages": torch.cat([item["advantages"] for item in probe_batches]),
                    "rewards": torch.cat([item["rewards"] for item in probe_batches]),
                    "sample_indices": torch.cat([item["sample_indices"] for item in probe_batches]),
                }
                # Require complete completion-level coverage for this singleton fixed-rollout control.
                expected_samples = int(config.get("probe_expected_samples", config.get("num_generations", 1)))
                if config.get("fixed_rollout_replay", False) and probe_batch["advantages"].numel() != expected_samples:
                    raise RuntimeError(
                        f"Fixed-rollout direction probe captured {probe_batch['advantages'].numel()} samples; expected {expected_samples}."
                    )
                target_device = next(self.evaluation_model.parameters()).device
                moved_batch = {key: value.to(target_device) for key, value in probe_batch["batch"].items()}
                was_training = self.evaluation_model.training
                self.evaluation_model.eval()
                with torch.no_grad():
                    # Compute token likelihoods once and derive all probe metrics from that result.
                    new_per_token_logps = _probe_per_token_logps(
                        self.evaluation_model,
                        moved_batch,
                        float(config.get("temperature", 1.0)),
                        chunk_size=int(config.get("probe_batch_size", 4)),
                    )
                    mask = moved_batch["completion_mask"].float()
                    new_logps = (new_per_token_logps * mask).sum(dim=1) / mask.sum(dim=1).clamp(min=1.0)
                if was_training:
                    self.evaluation_model.train()
                old_logps = probe_batch["old_logps"].to(new_logps.device)
                current_pre_per_token_logps = probe_batch["current_pre_per_token_logps"].to(new_logps.device)
                loss_old_per_token_logps = probe_batch["loss_old_per_token_logps"].to(new_logps.device)
                advantages = probe_batch["advantages"].to(new_logps.device)
                delta = new_logps - old_logps
                positive = advantages > 0
                negative = advantages < 0
                centered_advantage = advantages - advantages.mean()
                centered_delta = delta - delta.mean()
                correlation = float((centered_advantage * centered_delta).sum() / (torch.sqrt((centered_advantage**2).sum() * (centered_delta**2).sum()) + 1e-12))
                config["_update_diagnostics"].update({
                    "probe/advantage_delta_correlation": correlation,
                    "probe/positive_advantage_mean_logp_delta": float(delta[positive].mean()) if positive.any() else 0.0,
                    "probe/negative_advantage_mean_logp_delta": float(delta[negative].mean()) if negative.any() else 0.0,
                    "probe/advantage_sign_alignment": float(((advantages * delta) > 0).float().mean()),
                    "probe/rollout_sample_count": float(len(delta)),
                    "probe/dapo_surrogate_before": float(_probe_dapo_surrogate(loss_old_per_token_logps, loss_old_per_token_logps, advantages, moved_batch["completion_mask"])),
                    "probe/dapo_surrogate_after": float(_probe_dapo_surrogate(new_per_token_logps, loss_old_per_token_logps, advantages, moved_batch["completion_mask"])),
                })
                config["_update_diagnostics"]["probe/dapo_surrogate_delta"] = (
                    config["_update_diagnostics"]["probe/dapo_surrogate_after"]
                    - config["_update_diagnostics"]["probe/dapo_surrogate_before"]
                )
                # Save one auditable record for each sampled completion after its optimizer update.
                trace_path = config.get("probe_sample_trace_path")
                if trace_path:
                    trace_file = Path(trace_path)
                    trace_file.parent.mkdir(parents=True, exist_ok=True)
                    token_ids = probe_batch["batch"]["completion_ids"]
                    completion_texts = tokenizer.batch_decode(token_ids, skip_special_tokens=True)
                    sample_indices = probe_batch["sample_indices"].tolist()
                    sample_rewards = probe_batch["rewards"].tolist()
                    old_values = old_logps.detach().cpu().tolist()
                    new_values = new_logps.detach().cpu().tolist()
                    delta_values = delta.detach().cpu().tolist()
                    advantage_values = advantages.detach().cpu().tolist()
                    old_sum_values = ((current_pre_per_token_logps * moved_batch["completion_mask"]).sum(dim=1)).detach().cpu().tolist()
                    new_sum_values = ((new_per_token_logps * moved_batch["completion_mask"]).sum(dim=1)).detach().cpu().tolist()
                    with trace_file.open("a", encoding="utf-8") as handle:
                        for index, completion_text in enumerate(completion_texts):
                            handle.write(json.dumps({
                                "step": int(state.global_step + 1),
                                "sample_index": int(sample_indices[index]),
                                "reward": float(sample_rewards[index]),
                                "advantage": float(advantage_values[index]),
                                "pre_update_mean_token_log_probability": float(old_values[index]),
                                "post_update_mean_token_log_probability": float(new_values[index]),
                                "mean_token_log_probability_delta": float(delta_values[index]),
                                "geometric_mean_token_probability_ratio": float(torch.exp(delta[index]).item()),
                                "pre_update_sequence_log_probability": float(old_sum_values[index]),
                                "post_update_sequence_log_probability": float(new_sum_values[index]),
                                "sequence_probability_ratio": float(torch.exp(torch.tensor(new_sum_values[index] - old_sum_values[index])).item()),
                                "scored_token_count": int(moved_batch["completion_mask"][index].sum().item()),
                                "completion": completion_text,
                            }, sort_keys=True) + "\n")
            return control

        def on_step_begin(self, args: Any, state: Any, control: Any, **_: Any) -> Any:
            """Write the step header before generation begins."""
            append_training_step_header(config.get("log_path", "logs/logs.txt"), state.global_step + 1, state.max_steps)
            return control

        def on_log(self, args: Any, state: Any, control: Any, logs: dict[str, Any] | None = None, **_: Any) -> Any:
            """Write trainer metrics and the cumulative reward average."""
            # Enrich and persist each nonempty trainer log.
            if logs:
                reward = logs.get("rewards/reward/mean")
                # Update cumulative and rolling reward statistics when a reward is present.
                if isinstance(reward, (int, float)):
                    # Accumulate every emitted batch mean across the entire run, including epoch boundaries.
                    self.reward_sum += float(reward)
                    self.reward_count += 1
                    average_reward = self.reward_sum / self.reward_count
                    logs["training/average_reward"] = average_reward
                    self.rolling_reward_values.append(float(reward))
                    logs["training/rolling_average_reward"] = sum(self.rolling_reward_values) / len(self.rolling_reward_values)
                # Add dense reward and group statistics to the trainer's W&B record.
                logs.update(config.pop("_reward_diagnostics", {}))
                # Add gradient and parameter movement diagnostics to the trainer's W&B record.
                logs.update(config.pop("_update_diagnostics", {}))
                for component in ("format", "syntax", "interface", "test_progress"):
                    component_mean = logs.get(f"reward/{component}/mean")
                    # Update component statistics when the trainer emitted a numeric mean.
                    if isinstance(component_mean, (int, float)):
                        self.component_reward_sums[component] = self.component_reward_sums.get(component, 0.0) + float(component_mean)
                        self.component_reward_counts[component] = self.component_reward_counts.get(component, 0) + 1
                        logs[f"training/average_reward/{component}"] = self.component_reward_sums[component] / self.component_reward_counts[component]
                        self.rolling_component_values[component].append(float(component_mean))
                        logs[f"training/rolling_average_reward/{component}"] = sum(self.rolling_component_values[component]) / len(self.rolling_component_values[component])
                logs["training/reward_rolling_window"] = float(self.rolling_window_size)
                append_training_step_metrics(config.get("log_path", "logs/logs.txt"), logs)
                # Send enriched scalar metrics to the active W&B run.
                if wandb is not None and wandb.run is not None:
                    payload = {key: value for key, value in logs.items() if isinstance(value, (int, float))}
                    payload["trainer_step"] = float(state.global_step)
                    wandb.log(payload)
            return control

        def on_save(self, args: Any, state: Any, control: Any, **_: Any) -> Any:
            """Evaluate the current model and persist checkpoint metrics."""
            # Skip checkpoint evaluation when intermediate evaluations are disabled.
            if not config.get("run_intermediate_evals", False):
                return control
            # Evaluate and save the current checkpoint artifacts.
            metrics, details = evaluate_model(model, tokenizer, test_dataset, config, f"checkpoint-{state.global_step}")
            config["training_context"] = "checkpoint"
            config["_evaluation_epoch"] = state.epoch
            save_evaluation(args.output_dir, f"checkpoint-{state.global_step}", metrics, details, config)
            log_evaluation(wandb, metrics, f"checkpoint-{state.global_step}", state.global_step)
            checkpoint_path = Path(args.output_dir) / f"checkpoint-{state.global_step}"
            metric_name = config.get("best_checkpoint_metric", "pass@1")
            metric_key = "pass_at_1" if metric_name == "pass@1" else metric_name
            metric = float(metrics.get(metric_key, float("-inf")))
            # Retain only the checkpoint with the best configured metric.
            if metric > self.best_metric:
                previous_best = self.best_checkpoint_path
                self.best_checkpoint_path = checkpoint_path
                self.best_metric = metric
                self.evaluations_without_improvement = 0
                # Remove the previous best checkpoint after selecting a better one.
                if previous_best is not None and previous_best.exists():
                    shutil.rmtree(previous_best)
            else:
                if checkpoint_path.exists():
                    shutil.rmtree(checkpoint_path)
                self.evaluations_without_improvement += 1
                patience = max(0, int(config.get("checkpoint_eval_patience", 0)))
                if patience and self.evaluations_without_improvement >= patience:
                    control.should_training_stop = True
                    print(f"Stopping after {self.evaluations_without_improvement} checkpoint evaluations without a higher evaluation/pass@1.", flush=True)
            return control

        def on_step_end(self, args: Any, state: Any, control: Any, **_: Any) -> Any:
            """Run the configured checkpoint evaluation at each training step interval."""
            # Skip official evaluations when the step schedule is disabled.
            if int(config.get("evalplus_eval_steps", 10)) <= 0:
                return control
            # Evaluate every crossed step boundary and advance the schedule monotonically.
            while self.next_eval_step <= state.global_step:
                name = f"step-{self.next_eval_step}"
                model_path = Path(args.output_dir) / "evalplus_models" / name
                model_path.mkdir(parents=True, exist_ok=True)
                # Save the PEFT-wrapped trainer model so the evaluator receives adapter metadata.
                evaluation_model = self.evaluation_model
                evaluation_model.save_pretrained(model_path)
                tokenizer.save_pretrained(model_path)
                # Move the training model off the GPU while vLLM owns the evaluation GPU.
                evaluation_model.to("cpu")
                import torch
                torch.cuda.empty_cache()
                try:
                    if config.get("train_subset_evaluation_only", False):
                        # Evaluate only the fixed tiny training set for the overfit diagnostic.
                        training_result = evaluate_training_mbpp(model_path, train_dataset, config, f"training-{name}")
                        evalplus_result = {"metrics": training_result["metrics"]}
                        evaluation_log_name = f"training-{name}"
                        selection_metric = float(training_result["metrics"].get("pass_at_1", float("-inf")))
                    else:
                        # Run the canonical EvalPlus benchmark and add the disjoint training metrics.
                        evalplus_result = run_qwen_evalplus(model_path, Path(args.output_dir), name)
                        training_result = evaluate_training_mbpp(model_path, train_dataset, config, f"training-{name}")
                        evalplus_result["metrics"] = merge_training_metrics(evalplus_result["metrics"], training_result["metrics"])
                        evaluation_log_name = f"evalplus-{name}"
                        selection_metric = float(evalplus_result["metrics"].get("mbpp_plus_pass_at_1", float("-inf")))
                    save_evaluation(args.output_dir, f"training-{name}", training_result["metrics"], training_result["details"], config)
                    # Use evaluation labels for checkpoint selection only when the config permits it.
                    if config.get("select_best_checkpoint", True):
                        best_metric = self.best_metric if config.get("train_subset_evaluation_only", False) else self.best_evalplus_mbpp_plus
                        if selection_metric > best_metric:
                            best_dir = Path(args.output_dir) / "best_checkpoints" / name
                            if best_dir.exists():
                                shutil.rmtree(best_dir)
                            best_dir.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copytree(model_path, best_dir)
                            if config.get("train_subset_evaluation_only", False):
                                self.best_metric = selection_metric
                            else:
                                self.best_evalplus_mbpp_plus = selection_metric
                                config["_best_evalplus_mbpp_plus"] = self.best_evalplus_mbpp_plus
                            self.best_checkpoint_path = best_dir
                            print(f"Saved new best checkpoint at {best_dir} with pass@1={selection_metric:.3f}.", flush=True)
                        else:
                            print(f"Discarded checkpoint at {model_path}; pass@1={selection_metric:.3f} did not exceed {best_metric:.3f}.", flush=True)
                    else:
                        print(f"Recorded {evaluation_log_name}; checkpoint selection is disabled.", flush=True)
                finally:
                    evaluation_model.to(device or "cuda")
                    evaluation_model.train()
                    shutil.rmtree(model_path)
                if wandb is not None and wandb.run is not None:
                    log_evaluation(wandb, evalplus_result["metrics"], evaluation_log_name, state.global_step)
                self.next_eval_step += int(config.get("evalplus_eval_steps", 10))
            return control
    return TrainingCallback()


def _make_sft_callback(model: Any, tokenizer: Any, test_dataset: Any, config: dict[str, Any], wandb: Any | None):
    """Create a callback that tracks loss and evaluates each SFT epoch."""
    # Import the callback base class only when SFT starts.
    from transformers import TrainerCallback

    # Define the SFT callback with access to the current training objects.
    class SFTTrainingCallback(TrainerCallback):
        """Log current, cumulative, and moving-average SFT loss."""

        def __init__(self) -> None:
            """Initialize loss accumulators for the complete SFT stage."""
            # Initialize cumulative, rolling, and latest evaluation state.
            self.loss_sum = 0.0
            self.loss_count = 0
            self.rolling_window_size = max(1, int(config.get("sft_loss_rolling_window", 10)))
            self.rolling_losses: deque[float] = deque(maxlen=self.rolling_window_size)
            self.latest_metrics: dict[str, Any] | None = None
            self.latest_details: list[dict[str, Any]] | None = None

        def on_log(self, args: Any, state: Any, control: Any, logs: dict[str, Any] | None = None, **_: Any) -> Any:
            """Add the three requested SFT loss series to each batch log."""
            # Ignore trainer logs that do not contain a numeric loss.
            loss = logs.get("loss") if logs else None
            if not isinstance(loss, (int, float)):
                return control
            # Compute current, cumulative, and rolling loss metrics.
            self.loss_sum += float(loss)
            self.loss_count += 1
            self.rolling_losses.append(float(loss))
            metrics = {
                "sft/loss": float(loss),
                "sft/average_loss": self.loss_sum / self.loss_count,
                "sft/rolling_average_loss": sum(self.rolling_losses) / len(self.rolling_losses),
                "sft/loss_rolling_window": float(self.rolling_window_size),
                "sft/batch": float(state.global_step),
            }
            logs.update(metrics)
            # Send the computed loss metrics to the active W&B run.
            if wandb is not None and wandb.run is not None:
                wandb.log(metrics)
            return control

        def on_epoch_end(self, args: Any, state: Any, control: Any, **_: Any) -> Any:
            """Evaluate the SFT model after each completed epoch."""
            # Evaluate and save the model at the completed epoch boundary.
            epoch = max(1, int(round(float(state.epoch or 0))))
            name = f"sft-epoch-{epoch}"
            metrics, details = evaluate_model(model, tokenizer, test_dataset, config, name)
            config["training_context"] = "sft"
            config["_evaluation_epoch"] = epoch
            save_evaluation(args.output_dir, name, metrics, details, config)
            log_evaluation(wandb, metrics, name, state.global_step)
            self.latest_metrics = metrics
            self.latest_details = details
            # Resume training mode if another SFT epoch follows.
            model.train()
            return control

    return SFTTrainingCallback()


def run_sft(model: Any, tokenizer: Any, train_dataset: Any, test_dataset: Any, config: dict[str, Any], wandb: Any | None) -> tuple[Any, Any]:
    """Warm-start the model with response-only supervised fine-tuning."""
    # Import SFT dependencies only when the stage is enabled.
    import torch
    from transformers import DataCollatorForSeq2Seq, Trainer, TrainingArguments

    # Prepare the SFT output path, dataset, and trainer configuration.
    sft_output_dir = Path(config["output_dir"]) / "sft"
    sft_dataset = build_sft_dataset(train_dataset, tokenizer, config)
    training_args = TrainingArguments(
        output_dir=str(sft_output_dir),
        learning_rate=float(config.get("sft_learning_rate", 1e-5)),
        num_train_epochs=float(config.get("sft_num_train_epochs", 1)),
        max_steps=int(config.get("sft_max_steps", -1)),
        per_device_train_batch_size=int(config.get("sft_per_device_train_batch_size", 1)),
        gradient_accumulation_steps=int(config.get("sft_gradient_accumulation_steps", 1)),
        logging_steps=1,
        save_strategy="steps",
        report_to=[] if config.get("report_to") in (None, "none") else [config["report_to"]],
        run_name=config.get("wandb_run_name"),
        use_cpu=not torch.cuda.is_available(),
        seed=int(config.get("seed", 42)),
    )
    # Build the collator, callback, and trainer for supervised fine-tuning.
    collator = DataCollatorForSeq2Seq(tokenizer=tokenizer, model=model, padding=True)
    sft_callback = _make_sft_callback(model, tokenizer, test_dataset, config, wandb)
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=sft_dataset,
        data_collator=collator,
        callbacks=[sft_callback],
    )
    # Train and save the final SFT model.
    trainer.train()
    trainer.save_model(str(sft_output_dir / "final"))
    return trainer, sft_callback


def _enable_generation_stop(model: Any, tokenizer: Any) -> None:
    """Pass the tokenizer required by Transformers stop-string criteria during training generation."""
    # Inject the tokenizer into GRPO's model.generate calls without changing the trainer dependency.
    original_generate = model.generate

    def generate_with_tokenizer(*args: Any, **kwargs: Any) -> Any:
        """Forward generation with the official EvalPlus closing fence stop criterion."""
        input_ids = kwargs.get("input_ids")
        if input_ids is None and args:
            input_ids = args[0]
        if input_ids is not None:
            generation_config = kwargs.get("generation_config")
            if generation_config is not None and getattr(generation_config, "stop_strings", None):
                generation_config = copy.deepcopy(generation_config)
                generation_config.stop_strings = None
                kwargs["generation_config"] = generation_config
            kwargs["stopping_criteria"] = code_fence_stopping_criteria(tokenizer, input_ids.shape[-1], QWEN_EVALPLUS_STOP_STRINGS)
        return original_generate(*args, **kwargs)

    model.generate = generate_with_tokenizer


def run_training(config: dict[str, Any], stage: str = "all") -> None:
    """Run baseline evaluation, GRPO training, intermediate evaluations, and final evaluation."""
    # Import training dependencies only when the experiment launches.
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from trl import GRPOConfig, GRPOTrainer

    # Initialize local logs and the optional shared W&B run.
    start_run_log(config.get("log_path", "logs/logs.txt"), config.get("results_log_path", "logs/results.txt"))
    wandb = configure_wandb(config)
    # Define a shared evaluation axis for an active W&B run.
    if wandb is not None and wandb.run is not None:
        wandb.define_metric("evaluation/step")
        wandb.define_metric("evaluation/*", step_metric="evaluation/step")
    # Select the device, seed the process, and prepare a clean output directory.
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Selected device: {device}", flush=True)
    seed_everything(int(config.get("seed", 42)))
    output_dir = Path(config["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)
    # Remove stale intermediate checkpoints before a new training run.
    for checkpoint_path in output_dir.glob("checkpoint-*"):
        # Remove only checkpoint directories matched inside the output directory.
        if checkpoint_path.is_dir():
            shutil.rmtree(checkpoint_path)
    # Load datasets, tokenizer, and the base model.
    train_dataset, eval_dataset = prepare_datasets(config)
    tokenizer = AutoTokenizer.from_pretrained(config["model_name_or_path"], trust_remote_code=bool(config.get("trust_remote_code", False)))
    # Use the end-of-sequence token for padding when the tokenizer lacks one.
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    model_dtype = torch.bfloat16 if bool(config.get("bf16", True)) else None
    model = AutoModelForCausalLM.from_pretrained(config["model_name_or_path"], torch_dtype=model_dtype, trust_remote_code=bool(config.get("trust_remote_code", False)))
    _enable_generation_stop(model, tokenizer)
    model.to(device)
    print(f"Model device: {model.device}", flush=True)
    # Run the selected greedy sanity check before any optimization steps.
    if config.get("run_qwen_evalplus_at_start", True) or config.get("train_subset_evaluation_only", False):
        step_zero_path = output_dir / "evalplus_models" / "step-0"
        if step_zero_path.exists():
            shutil.rmtree(step_zero_path)
        step_zero_path.mkdir(parents=True, exist_ok=True)
        model.save_pretrained(step_zero_path)
        tokenizer.save_pretrained(step_zero_path)
        print("Running step-zero greedy evaluation.", flush=True)
        model.to("cpu")
        torch.cuda.empty_cache()
        try:
            training_result = evaluate_training_mbpp(step_zero_path, train_dataset, config, "training-step-0")
            save_evaluation(output_dir, "training-step-0", training_result["metrics"], training_result["details"], config)
            if config.get("train_subset_evaluation_only", False):
                # Use the tiny training pass rate as the checkpoint selection baseline.
                config["_best_train_pass_at_1"] = training_result["metrics"].get("pass_at_1", float("-inf"))
                log_evaluation(wandb, training_result["metrics"], "training-step-0", 0)
            else:
                # Run the canonical EvalPlus benchmark and merge the training baseline for normal runs.
                step_zero_result = run_qwen_evalplus(step_zero_path, output_dir, "step-0")
                step_zero_result["metrics"] = merge_training_metrics(step_zero_result["metrics"], training_result["metrics"])
                config["_best_evalplus_mbpp_plus"] = step_zero_result["metrics"].get("mbpp_plus_pass_at_1", float("-inf"))
                log_evaluation(wandb, step_zero_result["metrics"], "evalplus-step-0", 0)
        finally:
            model.to(device)
        shutil.rmtree(step_zero_path)
    # Run the SFT baseline, training stage, and final epoch evaluation when enabled.
    if config.get("sft_enabled", False):
        # Evaluate the base model once before supervised updates begin.
        baseline_metrics, baseline_details = evaluate_model(model, tokenizer, eval_dataset, config, "sft-baseline")
        config["training_context"] = "sft-baseline"
        config["_evaluation_epoch"] = 0
        save_evaluation(output_dir / "sft", "sft-baseline", baseline_metrics, baseline_details, config)
        log_evaluation(wandb, baseline_metrics, "sft-baseline", 0)
        _, sft_callback = run_sft(model, tokenizer, train_dataset, eval_dataset, config, wandb)
        baseline_metrics = sft_callback.latest_metrics
        baseline_details = sft_callback.latest_details
        # Require SFT to produce an epoch evaluation for the GRPO baseline.
        if baseline_metrics is None or baseline_details is None:
            raise RuntimeError("SFT completed without an end-of-epoch evaluation.")
    elif config.get("run_baseline_evaluation", True):
        # Evaluate the base model before direct GRPO training.
        cached_baseline = load_cached_evaluation(output_dir, "baseline") if config.get("reuse_baseline", True) else None
        # Compute the baseline when no complete cached evaluation exists.
        if cached_baseline is None:
            print("Computing baseline evaluation.", flush=True)
            baseline_metrics, baseline_details = evaluate_model(model, tokenizer, eval_dataset, config, "baseline")
            config["training_context"] = "baseline"
            config["_evaluation_epoch"] = "baseline"
            save_evaluation(output_dir, "baseline", baseline_metrics, baseline_details, config)
        else:
            print("Reusing cached baseline evaluation.", flush=True)
            baseline_metrics, baseline_details = cached_baseline
            append_evaluation_log(config.get("log_path", "logs/logs.txt"), "baseline-cached", [eval_dataset[index] for index in range(len(eval_dataset))], baseline_details)
    # Stop after SFT when the command requests the isolated stage.
    if stage == "sft":
        return
    # Configure GRPO with the experiment settings.
    training_args = GRPOConfig(
        output_dir=str(output_dir),
        learning_rate=float(config["learning_rate"]),
        lr_scheduler_type=str(config.get("lr_scheduler_type", "linear")),
        num_train_epochs=float(config.get("num_train_epochs", 1)),
        max_steps=int(config.get("max_steps", -1)),
        per_device_train_batch_size=int(config["per_device_train_batch_size"]),
        gradient_accumulation_steps=int(config["gradient_accumulation_steps"]),
        num_generations=int(config["num_generations"]),
        generation_batch_size=int(config["generation_batch_size"]) if config.get("generation_batch_size") else None,
        max_completion_length=int(config["max_completion_length"]),
        beta=float(config.get("beta", 0.0)),
        loss_type=str(config.get("loss_type", "dapo")),
        disable_dropout=bool(config.get("disable_dropout", False)),
        logging_steps=int(config["logging_steps"]),
        save_steps=int(config["save_steps"]),
        save_strategy="no",
        eval_strategy="no",
        bf16=bool(config.get("bf16", False)),
        fp16=bool(config.get("fp16", False)),
        report_to=[] if config.get("report_to") in (None, "none") else [config["report_to"]],
        run_name=config.get("wandb_run_name"),
        use_cpu=not torch.cuda.is_available(),
        seed=int(config.get("seed", 42)),
    )
    trainer_class = GRPOTrainer
    if config.get("mask_reward_stops", True):
        # Align completion-token loss masks with the per-completion stop boundary used by reward scoring.
        stop_ids = stop_token_id_sequences(tokenizer, QWEN_EVALPLUS_STOP_STRINGS)

        class RewardMaskedGRPOTrainer(GRPOTrainer):
            """Mask unscored suffix tokens after every completion's reward stop marker."""

            def _generate_and_score_completions(self, inputs: list[dict[str, Any]]) -> dict[str, Any]:
                """Apply the reward-prefix mask after TRL generates and scores completions."""
                generated = super()._generate_and_score_completions(inputs)
                original_mask = generated["completion_mask"]
                generated["completion_mask"] = mask_completion_tokens_after_stop(
                    generated["completion_ids"], generated["completion_mask"], stop_ids, tokenizer=tokenizer
                )
                # Keep DAPO's token normalizer aligned with the reward-scored completion prefix.
                generated["num_items_in_batch"] = generated["completion_mask"].sum()
                # Report lengths after removing both padded rows and unscored suffixes.
                lengths = generated["completion_mask"].sum(dim=1).float()
                self._metrics["train"]["completions/mean_length"] = [float(lengths.mean())]
                self._metrics["train"]["completions/min_length"] = [float(lengths.min())]
                self._metrics["train"]["completions/max_length"] = [float(lengths.max())]
                masked_fraction = 1.0 - float(generated["completion_mask"].sum() / original_mask.sum().clamp(min=1))
                self._metrics["train"]["reward_stop_masked_token_fraction"].append(masked_fraction)
                return generated

        trainer_class = RewardMaskedGRPOTrainer
    if config.get("probe_update_direction", False):
        # Capture one rollout batch so the callback can measure post-update likelihood changes.
        class ProbeGRPOTrainer(trainer_class):
            """Add one rollout likelihood probe to the normal GRPO trainer."""

            def _compute_loss(self, model: Any, inputs: dict[str, Any]) -> Any:
                """Cache the first rollout batch and delegate the actual GRPO loss to TRL."""
                if "_direction_probe_batches" not in config:
                    config["_direction_probe_batches"] = []
                if len(config["_direction_probe_batches"]) < int(config.get("gradient_accumulation_steps", 1)):
                    import torch
                    batch = {
                        key: inputs[key].detach().cpu()
                        for key in ("prompt_ids", "prompt_mask", "completion_ids", "completion_mask")
                    }
                    was_training = model.training
                    model.eval()
                    with torch.no_grad():
                        moved_batch = {key: value.to(next(model.parameters()).device) for key, value in batch.items()}
                        old_per_token_logps = _probe_per_token_logps(
                            model,
                            moved_batch,
                            float(config.get("temperature", 1.0)),
                            chunk_size=int(config.get("probe_batch_size", 4)),
                        ).detach().cpu()
                        mask = batch["completion_mask"].float()
                        old_logps = ((old_per_token_logps * mask).sum(dim=1) / mask.sum(dim=1).clamp(min=1.0)).detach().cpu()
                    if was_training:
                        model.train()
                    # Preserve the actual loss reference when the TRL batch provides one.
                    loss_old_per_token_logps = inputs.get("old_per_token_logps")
                    if loss_old_per_token_logps is None:
                        loss_old_per_token_logps = old_per_token_logps
                    else:
                        loss_old_per_token_logps = loss_old_per_token_logps.detach().cpu()
                    # Match this shuffled rollout row to its original reward trace entry.
                    reward_rows = config.get("_probe_rewards_by_token_row", {})
                    matched_rewards = []
                    sample_indices = []
                    for token_row in batch["completion_ids"]:
                        key = _probe_token_row_key(token_row)
                        candidates = reward_rows.get(key, [])
                        if not candidates:
                            raise RuntimeError("Could not match a cached GRPO completion to its reward and generation index.")
                        sample_index, reward_value = candidates.pop(0)
                        matched_rewards.append(reward_value)
                        sample_indices.append(sample_index)
                    config["_direction_probe_batches"].append({
                        "batch": batch,
                        "old_logps": old_logps,
                        "current_pre_per_token_logps": old_per_token_logps,
                        "loss_old_per_token_logps": loss_old_per_token_logps,
                        "advantages": inputs["advantages"].detach().cpu(),
                        "rewards": torch.tensor(matched_rewards, dtype=torch.float32),
                        "sample_indices": torch.tensor(sample_indices, dtype=torch.long),
                    })
                return super()._compute_loss(model, inputs)

            def _generate_and_score_completions(self, inputs: list[dict[str, Any]]) -> dict[str, Any]:
                """Retain reward-to-token associations before TRL shuffles the rollout."""
                # Replay the original token rows and advantages when the fixed-batch diagnostic is enabled.
                if self.model.training and config.get("fixed_rollout_replay", False) and "_fixed_rollout_batch" in config:
                    generated = {key: value.clone() if hasattr(value, "clone") else value for key, value in config["_fixed_rollout_batch"].items()}
                    config["_probe_rewards_by_token_row"] = defaultdict(
                        list,
                        {
                            key: list(values)
                            for key, values in config["_fixed_rollout_reward_rows"].items()
                        },
                    )
                    return generated
                # Generate and score a fresh group before the first update or in ordinary on-policy mode.
                generated = super()._generate_and_score_completions(inputs)
                if self.model.training:
                    # Capture the per-completion scorer values in generation order for later matching.
                    reward_name = self.reward_func_names[0]
                    batch_size = generated["completion_ids"].shape[0]
                    reward_values = list(self._logs["rewards"][reward_name])[-batch_size:]
                    reward_rows: dict[tuple[int, ...], list[tuple[int, float]]] = defaultdict(list)
                    for sample_index, (token_row, reward_value) in enumerate(zip(generated["completion_ids"], reward_values, strict=True)):
                        reward_rows[_probe_token_row_key(token_row)].append((sample_index, float(reward_value)))
                    config["_probe_rewards_by_token_row"] = reward_rows
                    if config.get("fixed_rollout_replay", False):
                        # Anchor DAPO ratios to the initial model when TRL would otherwise use current log probabilities.
                        if generated.get("old_per_token_logps") is None:
                            was_training = self.model.training
                            self.model.eval()
                            with torch.no_grad():
                                device = next(self.model.parameters()).device
                                moved = {key: generated[key].to(device) for key in ("prompt_ids", "prompt_mask", "completion_ids", "completion_mask")}
                                generated["old_per_token_logps"] = _probe_per_token_logps(
                                    self.model,
                                    moved,
                                    float(config.get("temperature", 1.0)),
                                    chunk_size=int(config.get("probe_batch_size", 4)),
                                ).detach()
                            if was_training:
                                self.model.train()
                        # Keep the original rollout tensors, rewards, and advantages fixed for every later update.
                        config["_fixed_rollout_batch"] = {
                            key: value.detach().clone() if hasattr(value, "detach") else value
                            for key, value in generated.items()
                        }
                        config["_fixed_rollout_reward_rows"] = {
                            key: list(values)
                            for key, values in reward_rows.items()
                        }
                return generated

        trainer_class = ProbeGRPOTrainer
    evaluation_dataset = train_dataset if config.get("train_subset_evaluation_only", False) else eval_dataset
    training_callback = _make_callback(model, tokenizer, train_dataset, evaluation_dataset, config, wandb, device)
    callbacks = [training_callback]
    print(f"Intermediate evaluations enabled: {bool(callbacks)}", flush=True)
    trainer = trainer_class(
        model=model,
        processing_class=tokenizer,
        reward_funcs=_make_reward(config),
        train_dataset=train_dataset,
        args=training_args,
        callbacks=callbacks,
        peft_config=build_peft_config(config),
    )
    # Give the callback the PEFT-wrapped trainer model used for optimization and evaluation.
    training_callback.set_evaluation_model(trainer.model)
    # Log the direct GRPO baseline because SFT already logged its ending policy.
    if not config.get("sft_enabled", False) and config.get("run_baseline_evaluation", True):
        log_evaluation(wandb, baseline_metrics, "baseline", 0)
    # Train the GRPO model and identify the selected checkpoint.
    trainer.train()
    best_checkpoint_path = training_callback.best_checkpoint_path
    # Reload the selected checkpoint before final evaluation when one exists.
    if best_checkpoint_path is not None and best_checkpoint_path.exists():
        print(f"Loading best checkpoint for final evaluation: {best_checkpoint_path}", flush=True)
        tokenizer = AutoTokenizer.from_pretrained(best_checkpoint_path, trust_remote_code=bool(config.get("trust_remote_code", False)))
        # Restore a padding token when the selected tokenizer lacks one.
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token
        if (best_checkpoint_path / "adapter_config.json").is_file():
            from peft import PeftModel
            base_model = AutoModelForCausalLM.from_pretrained(config["model_name_or_path"], trust_remote_code=bool(config.get("trust_remote_code", False)))
            model = PeftModel.from_pretrained(base_model, best_checkpoint_path)
        else:
            model = AutoModelForCausalLM.from_pretrained(best_checkpoint_path, trust_remote_code=bool(config.get("trust_remote_code", False)))
        model.to(device)
        trainer.model = model
    # Save and evaluate the final selected model.
    trainer.save_model(str(output_dir / "final"))
    # Release the training model before vLLM loads the merged adapter for final generation.
    trainer.model.to("cpu")
    torch.cuda.empty_cache()
    if config.get("train_subset_evaluation_only", False):
        # Evaluate the final policy only on the fixed tiny training set.
        final_result = evaluate_training_mbpp(output_dir / "final", train_dataset, config, "training-final")
        final_metrics, final_details = final_result["metrics"], final_result["details"]
    else:
        # Evaluate normal runs on the canonical EvalPlus evaluation set.
        final_metrics, final_details = evaluate_model(model, tokenizer, eval_dataset, config, "final")
    config["training_context"] = "best-checkpoint-final" if best_checkpoint_path is not None else "final"
    config["_evaluation_epoch"] = trainer.state.epoch
    save_evaluation(output_dir, "final", final_metrics, final_details, config)
    log_evaluation(wandb, final_metrics, "final", trainer.state.global_step)
    (output_dir / "config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")


def main() -> None:
    """Parse the command line and launch the configured experiment."""
    # Parse the configuration path and requested training stage.
    parser = argparse.ArgumentParser(description="Train Qwen with GRPO on MBPP.")
    parser.add_argument("--config", default="configs/default.yaml", help="Path to a YAML experiment configuration.")
    parser.add_argument("--stage", choices=("all", "sft"), default="all", help="Run the full pipeline or stop after SFT.")
    args = parser.parse_args()
    # Load environment values and preserve the source configuration for logging.
    load_dotenv()
    config = load_config(args.config)
    config["_config_path"] = str(args.config)
    config["_config_yaml"] = Path(args.config).read_text(encoding="utf-8")
    # Display the resolved configuration and launch training.
    print("Experiment configuration:")
    print(pformat(config, sort_dicts=False), flush=True)
    run_training(config, stage=args.stage)


# Launch the command-line entry point when this file is executed directly.
if __name__ == "__main__":
    main()
