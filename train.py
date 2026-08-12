"""Command-line GRPO training orchestration for MBPP."""

from __future__ import annotations

import argparse
import json
import os
import random
import shutil
from collections import deque
from pathlib import Path
from pprint import pformat
from typing import Any

import yaml
from dotenv import load_dotenv

from data import build_sft_dataset, prepare_datasets
from evaluate import append_training_step_header, append_training_step_metrics, append_training_step_samples, append_evaluation_log, evaluate_model, save_evaluation, start_run_log
from sandbox import reward_function


def load_config(path: str | Path) -> dict[str, Any]:
    """Load one YAML experiment configuration."""
    with Path(path).open(encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def seed_everything(seed: int) -> None:
    """Seed Python and available numerical frameworks for reproducibility."""
    random.seed(seed)
    try:
        import numpy as np
        np.random.seed(seed)
    except ImportError:
        pass
    try:
        import torch
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
    except ImportError:
        pass


def configure_wandb(config: dict[str, Any]) -> Any | None:
    """Load the local W&B key and authenticate when W&B logging is enabled."""
    if config.get("report_to") in (None, "none", []):
        return None
    try:
        import wandb
    except ImportError as exc:
        raise RuntimeError("W&B logging is enabled, but wandb is not installed.") from exc
    api_key = os.getenv("WANDB_API_KEY")
    if not api_key:
        raise RuntimeError("W&B logging is enabled, but WANDB_API_KEY is missing from the environment.")
    wandb.login(key=api_key, relogin=False)
    os.environ.setdefault("WANDB_PROJECT", str(config.get("wandb_project", "grpo-mbpp")))
    return wandb


def log_evaluation(wandb: Any | None, metrics: dict[str, Any], evaluation_name: str, step: int | None = None) -> None:
    """Log one evaluation event with a shared custom W&B x-axis."""
    if wandb is None or wandb.run is None:
        return
    payload: dict[str, Any] = {
        "evaluation/step": float(step or 0),
        "evaluation/name": evaluation_name,
    }
    for key, value in metrics.items():
        if isinstance(value, (int, float)):
            payload[f"evaluation/{key}"] = value
        elif key == "status_counts" and isinstance(value, dict):
            for status, count in value.items():
                payload[f"evaluation/status_{status}"] = count
    wandb.log(payload)


def load_cached_evaluation(output_dir: Path, name: str) -> tuple[dict[str, Any], list[dict[str, Any]]] | None:
    """Load a complete cached evaluation when both JSON artifacts are present."""
    metrics_path = output_dir / f"{name}-metrics.json"
    details_path = output_dir / f"{name}-details.json"
    if not metrics_path.is_file() or not details_path.is_file():
        return None
    with metrics_path.open(encoding="utf-8") as handle:
        metrics = json.load(handle)
    with details_path.open(encoding="utf-8") as handle:
        details = json.load(handle)
    return metrics, details


def _make_reward(config: dict[str, Any]):
    """Bind sandbox configuration to the TRL reward-function contract."""
    timeout = float(config.get("sandbox_timeout_seconds", 3))

    def reward(completions: list[object], test_code: list[str], **kwargs: object) -> list[float]:
        """Score the current GRPO completion batch."""
        # Share reward diagnostics with the training callback for W&B and local logs.
        diagnostics: dict[str, float] = {}
        append_training_step_samples(config.get("log_path", "logs/logs.txt"), completions)
        rewards = reward_function(completions, test_code, timeout, diagnostics=diagnostics, group_size=int(config.get("num_generations", 4)), **kwargs)
        config["_reward_diagnostics"] = diagnostics
        return rewards

    return reward

def _make_callback(model: Any, tokenizer: Any, test_dataset: Any, config: dict[str, Any], wandb: Any | None):
    """Create callbacks for step logging and checkpoint evaluation."""
    from transformers import TrainerCallback

    class TrainingCallback(TrainerCallback):
        """Log each training step and evaluate saved checkpoints."""

        def __init__(self) -> None:
            """Track the best checkpoint selected by intermediate pass rate."""
            self.best_checkpoint_path: Path | None = None
            self.best_metric = float("-inf")
            self.reward_sum = 0.0
            self.reward_count = 0
            self.component_reward_sums: dict[str, float] = {}
            self.component_reward_counts: dict[str, int] = {}
            self.rolling_window_size = max(1, int(config.get("reward_rolling_window", 10)))
            self.rolling_reward_values: deque[float] = deque(maxlen=self.rolling_window_size)
            self.rolling_component_values: dict[str, deque[float]] = {
                component: deque(maxlen=self.rolling_window_size)
                for component in ("format", "syntax", "interface", "execution", "test_progress")
            }

        def on_step_begin(self, args: Any, state: Any, control: Any, **_: Any) -> Any:
            """Write the step header before generation begins."""
            append_training_step_header(config.get("log_path", "logs/logs.txt"), state.global_step + 1, state.max_steps)
            return control

        def on_log(self, args: Any, state: Any, control: Any, logs: dict[str, Any] | None = None, **_: Any) -> Any:
            """Write trainer metrics and the cumulative reward average."""
            if logs:
                reward = logs.get("rewards/reward/mean")
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
                for component in ("format", "syntax", "interface", "execution", "test_progress"):
                    component_mean = logs.get(f"reward/{component}/mean")
                    if isinstance(component_mean, (int, float)):
                        self.component_reward_sums[component] = self.component_reward_sums.get(component, 0.0) + float(component_mean)
                        self.component_reward_counts[component] = self.component_reward_counts.get(component, 0) + 1
                        logs[f"training/average_reward/{component}"] = self.component_reward_sums[component] / self.component_reward_counts[component]
                        self.rolling_component_values[component].append(float(component_mean))
                        logs[f"training/rolling_average_reward/{component}"] = sum(self.rolling_component_values[component]) / len(self.rolling_component_values[component])
                logs["training/reward_rolling_window"] = float(self.rolling_window_size)
                append_training_step_metrics(config.get("log_path", "logs/logs.txt"), logs)
                if wandb is not None and wandb.run is not None:
                    # Log callback-added metrics after the built-in W&B callback so every scalar is graphable.
                    payload = {key: value for key, value in logs.items() if isinstance(value, (int, float))}
                    payload["trainer_step"] = float(state.global_step)
                    wandb.log(payload)
            return control

        def on_save(self, args: Any, state: Any, control: Any, **_: Any) -> Any:
            """Evaluate the current model and persist checkpoint metrics."""
            if not config.get("run_intermediate_evals", False):
                return control
            metrics, details = evaluate_model(model, tokenizer, test_dataset, config, f"checkpoint-{state.global_step}")
            config["training_context"] = "checkpoint"
            config["_evaluation_epoch"] = state.epoch
            save_evaluation(args.output_dir, f"checkpoint-{state.global_step}", metrics, details, config)
            log_evaluation(wandb, metrics, f"checkpoint-{state.global_step}", state.global_step)
            checkpoint_path = Path(args.output_dir) / f"checkpoint-{state.global_step}"
            metric = float(metrics.get(config.get("best_checkpoint_metric", "pass_at_1"), float("-inf")))
            if metric > self.best_metric:
                previous_best = self.best_checkpoint_path
                self.best_checkpoint_path = checkpoint_path
                self.best_metric = metric
                if previous_best is not None and previous_best.exists():
                    shutil.rmtree(previous_best)
            elif checkpoint_path.exists():
                shutil.rmtree(checkpoint_path)
            return control
    return TrainingCallback()


def _make_sft_callback(config: dict[str, Any], wandb: Any | None):
    """Create a callback that tracks per-batch and averaged SFT loss."""
    from transformers import TrainerCallback

    class SFTTrainingCallback(TrainerCallback):
        """Log current, cumulative, and moving-average SFT loss."""

        def __init__(self) -> None:
            """Initialize loss accumulators for the complete SFT stage."""
            self.loss_sum = 0.0
            self.loss_count = 0
            self.rolling_window_size = max(1, int(config.get("sft_loss_rolling_window", 10)))
            self.rolling_losses: deque[float] = deque(maxlen=self.rolling_window_size)

        def on_log(self, args: Any, state: Any, control: Any, logs: dict[str, Any] | None = None, **_: Any) -> Any:
            """Add the three requested SFT loss series to each batch log."""
            loss = logs.get("loss") if logs else None
            if not isinstance(loss, (int, float)):
                return control
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
            if wandb is not None and wandb.run is not None:
                # Log callback-added metrics explicitly so W&B retains every batch.
                wandb.log(metrics)
            return control

    return SFTTrainingCallback()


def run_sft(model: Any, tokenizer: Any, train_dataset: Any, config: dict[str, Any], wandb: Any | None) -> Any:
    """Warm-start the model with response-only supervised fine-tuning."""
    import torch
    from transformers import DataCollatorForSeq2Seq, Trainer, TrainingArguments

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
    # Pad inputs and masked labels dynamically for each batch.
    collator = DataCollatorForSeq2Seq(tokenizer=tokenizer, model=model, padding=True)
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=sft_dataset,
        data_collator=collator,
        callbacks=[_make_sft_callback(config, wandb)],
    )
    trainer.train()
    trainer.save_model(str(sft_output_dir / "final"))
    return trainer


def run_training(config: dict[str, Any], stage: str = "all") -> None:
    """Run baseline evaluation, GRPO training, intermediate evaluations, and final evaluation."""
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from trl import GRPOConfig, GRPOTrainer

    start_run_log(config.get("log_path", "logs/logs.txt"), config.get("results_log_path", "logs/results.txt"))
    wandb = configure_wandb(config)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Selected device: {device}", flush=True)
    seed_everything(int(config.get("seed", 42)))
    output_dir = Path(config["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)
    for checkpoint_path in output_dir.glob("checkpoint-*"):
        if checkpoint_path.is_dir():
            shutil.rmtree(checkpoint_path)
    train_dataset, test_dataset = prepare_datasets(config)
    tokenizer = AutoTokenizer.from_pretrained(config["model_name_or_path"], trust_remote_code=bool(config.get("trust_remote_code", False)))
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(config["model_name_or_path"], trust_remote_code=bool(config.get("trust_remote_code", False)))
    model.to(device)
    print(f"Model device: {model.device}", flush=True)
    cached_baseline = load_cached_evaluation(output_dir, "baseline") if config.get("reuse_baseline", True) else None
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
    if config.get("sft_enabled", False):
        # Warm-start the same model instance before constructing the GRPO trainer.
        run_sft(model, tokenizer, train_dataset, config, wandb)
    if stage == "sft":
        # Stop after SFT so short validation runs do not launch GRPO.
        return
    training_args = GRPOConfig(
        output_dir=str(output_dir),
        learning_rate=float(config["learning_rate"]),
        num_train_epochs=float(config.get("num_train_epochs", 1)),
        max_steps=int(config.get("max_steps", -1)),
        per_device_train_batch_size=int(config["per_device_train_batch_size"]),
        gradient_accumulation_steps=int(config["gradient_accumulation_steps"]),
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
    )
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
    if wandb is not None and wandb.run is not None:
        wandb.define_metric("evaluation/step")
        wandb.define_metric("evaluation/*", step_metric="evaluation/step")
    log_evaluation(wandb, baseline_metrics, "baseline", 0)
    trainer.train()
    best_checkpoint_path = training_callback.best_checkpoint_path
    if best_checkpoint_path is not None and best_checkpoint_path.exists():
        print(f"Loading best checkpoint for final evaluation: {best_checkpoint_path}", flush=True)
        tokenizer = AutoTokenizer.from_pretrained(best_checkpoint_path, trust_remote_code=bool(config.get("trust_remote_code", False)))
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token
        model = AutoModelForCausalLM.from_pretrained(best_checkpoint_path, trust_remote_code=bool(config.get("trust_remote_code", False)))
        model.to(device)
        trainer.model = model
    trainer.save_model(str(output_dir / "final"))
    final_metrics, final_details = evaluate_model(model, tokenizer, test_dataset, config, "final")
    config["training_context"] = "best-checkpoint-final" if best_checkpoint_path is not None else "final"
    config["_evaluation_epoch"] = trainer.state.epoch
    save_evaluation(output_dir, "final", final_metrics, final_details, config)
    log_evaluation(wandb, final_metrics, "final", trainer.state.global_step)
    (output_dir / "config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")


def main() -> None:
    """Parse the command line and launch the configured experiment."""
    parser = argparse.ArgumentParser(description="Train Qwen with GRPO on MBPP.")
    parser.add_argument("--config", default="configs/default.yaml", help="Path to a YAML experiment configuration.")
    parser.add_argument("--stage", choices=("all", "sft"), default="all", help="Run the full pipeline or stop after SFT.")
    args = parser.parse_args()
    load_dotenv()
    config = load_config(args.config)
    config["_config_path"] = str(args.config)
    config["_config_yaml"] = Path(args.config).read_text(encoding="utf-8")
    print("Experiment configuration:")
    print(pformat(config, sort_dicts=False), flush=True)
    run_training(config, stage=args.stage)


if __name__ == "__main__":
    main()
