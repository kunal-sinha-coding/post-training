# This file runs the complete MBPP training flow from configuration loading through evaluation.
# It prepares data and models, optionally runs SFT, and then runs GRPO.
# It records metrics, selects checkpoints, and saves the final artifacts.

from __future__ import annotations

import argparse
import json
import os
import random
import shutil
from collections import deque
from pathlib import Path
from pprint import pformat
import copy
from typing import Any

import yaml
from dotenv import load_dotenv

from data import build_sft_dataset, prepare_datasets
from evaluate import append_training_step_header, append_training_step_metrics, append_training_step_samples, append_evaluation_log, code_fence_stopping_criteria, evaluate_model, forced_code_prefix_length, forced_code_prefix_processor, save_evaluation, start_run_log
from sandbox import reward_function


def load_config(path: str | Path) -> dict[str, Any]:
    """Load one YAML experiment configuration."""
    with Path(path).open(encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


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
    # Resolve the sandbox timeout once for the reward closure.
    timeout = float(config.get("sandbox_timeout_seconds", 3))

    def reward(completions: list[object], test_code: list[str], **kwargs: object) -> list[float]:
        """Score the current GRPO completion batch."""
        # Share reward diagnostics with the training callback for W&B and local logs.
        diagnostics: dict[str, float] = {}
        # Keep the proven dense reward mixture fixed throughout training.
        pass_weight = float(config.get("pass_weight", 0.5))
        append_training_step_samples(config.get("log_path", "logs/logs.txt"), completions)
        rewards = reward_function(completions, test_code, timeout, diagnostics=diagnostics, group_size=int(config.get("num_generations", 4)), pass_weight=pass_weight, **kwargs)
        # Record the number of hidden assertions exercised by this reward batch.
        synthetic_counts = kwargs.get("synthetic_test_count", [])
        if isinstance(synthetic_counts, list) and synthetic_counts:
            diagnostics["reward/synthetic_tests/mean"] = sum(float(count) for count in synthetic_counts) / len(synthetic_counts)
        config["_reward_diagnostics"] = diagnostics
        return rewards

    return reward

def _make_callback(model: Any, tokenizer: Any, test_dataset: Any, config: dict[str, Any], wandb: Any | None):
    """Create callbacks for step logging and checkpoint evaluation."""
    # Import the callback base class only when training starts.
    from transformers import TrainerCallback

    # Define the GRPO callback with access to the current training objects.
    class TrainingCallback(TrainerCallback):
        """Log each training step and evaluate saved checkpoints."""

        def __init__(self) -> None:
            """Track the best checkpoint selected by intermediate pass rate."""
            # Initialize checkpoint, cumulative, and rolling metric state.
            self.best_checkpoint_path: Path | None = None
            self.best_metric = float("-inf")
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
        save_strategy="no",
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
        """Forward generation with a stop criterion that ignores prompt fence tokens."""
        input_ids = kwargs.get("input_ids")
        if input_ids is None and args:
            input_ids = args[0]
        if input_ids is not None:
            generation_config = kwargs.get("generation_config")
            if generation_config is not None and getattr(generation_config, "stop_strings", None):
                generation_config = copy.deepcopy(generation_config)
                generation_config.stop_strings = None
                kwargs["generation_config"] = generation_config
            kwargs["logits_processor"] = [forced_code_prefix_processor(tokenizer, input_ids.shape[-1])]
            kwargs["stopping_criteria"] = code_fence_stopping_criteria(tokenizer, input_ids.shape[-1] + forced_code_prefix_length(tokenizer))
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
    train_dataset, test_dataset = prepare_datasets(config)
    tokenizer = AutoTokenizer.from_pretrained(config["model_name_or_path"], trust_remote_code=bool(config.get("trust_remote_code", False)))
    # Use the end-of-sequence token for padding when the tokenizer lacks one.
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(config["model_name_or_path"], trust_remote_code=bool(config.get("trust_remote_code", False)))
    _enable_generation_stop(model, tokenizer)
    model.to(device)
    print(f"Model device: {model.device}", flush=True)
    # Run the SFT baseline, training stage, and final epoch evaluation when enabled.
    if config.get("sft_enabled", False):
        # Evaluate the base model once before supervised updates begin.
        baseline_metrics, baseline_details = evaluate_model(model, tokenizer, test_dataset, config, "sft-baseline")
        config["training_context"] = "sft-baseline"
        config["_evaluation_epoch"] = 0
        save_evaluation(output_dir / "sft", "sft-baseline", baseline_metrics, baseline_details, config)
        log_evaluation(wandb, baseline_metrics, "sft-baseline", 0)
        _, sft_callback = run_sft(model, tokenizer, train_dataset, test_dataset, config, wandb)
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
            baseline_metrics, baseline_details = evaluate_model(model, tokenizer, test_dataset, config, "baseline")
            config["training_context"] = "baseline"
            config["_evaluation_epoch"] = "baseline"
            save_evaluation(output_dir, "baseline", baseline_metrics, baseline_details, config)
        else:
            print("Reusing cached baseline evaluation.", flush=True)
            baseline_metrics, baseline_details = cached_baseline
            append_evaluation_log(config.get("log_path", "logs/logs.txt"), "baseline-cached", [test_dataset[index] for index in range(len(test_dataset))], baseline_details)
    # Stop after SFT when the command requests the isolated stage.
    if stage == "sft":
        return
    # Configure GRPO with the experiment settings.
    training_args = GRPOConfig(
        output_dir=str(output_dir),
        learning_rate=float(config["learning_rate"]),
        num_train_epochs=float(config.get("num_train_epochs", 1)),
        max_steps=int(config.get("max_steps", -1)),
        per_device_train_batch_size=int(config["per_device_train_batch_size"]),
        gradient_accumulation_steps=int(config["gradient_accumulation_steps"]),
        generation_batch_size=int(config.get("generation_batch_size", int(config["per_device_train_batch_size"]) * int(config["gradient_accumulation_steps"]))),
        num_generations=int(config["num_generations"]),
        max_completion_length=int(config["max_completion_length"]),
        logging_steps=int(config["logging_steps"]),
        save_steps=int(config["save_steps"]),
        eval_strategy="no",
        bf16=bool(config.get("bf16", False)),
        fp16=bool(config.get("fp16", False)),
        report_to=[] if config.get("report_to") in (None, "none") else [config["report_to"]],
        run_name=config.get("wandb_run_name"),
        use_cpu=not torch.cuda.is_available(),
        seed=int(config.get("seed", 42)),
        generation_kwargs=dict(config.get("generation_kwargs", {"stop_strings": ["```"]})),
    )
    # Build the GRPO callback and trainer.
    training_callback = _make_callback(model, tokenizer, test_dataset, config, wandb)
    callbacks = [training_callback]
    print(f"Intermediate evaluations enabled: {bool(callbacks)}", flush=True)
    trainer = GRPOTrainer(
        model=model,
        processing_class=tokenizer,
        reward_funcs=_make_reward(config),
        train_dataset=train_dataset,
        args=training_args,
        callbacks=callbacks,
    )
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
        model = AutoModelForCausalLM.from_pretrained(best_checkpoint_path, trust_remote_code=bool(config.get("trust_remote_code", False)))
        model.to(device)
        trainer.model = model
    # Save and evaluate the final selected model.
    trainer.save_model(str(output_dir / "final"))
    final_metrics, final_details = evaluate_model(model, tokenizer, test_dataset, config, "final")
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
