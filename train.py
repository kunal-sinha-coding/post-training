"""Command-line GRPO training orchestration for MBPP."""

from __future__ import annotations

import argparse
import json
import os
import random
import shutil
from pathlib import Path
from pprint import pformat
from typing import Any

import yaml
from dotenv import load_dotenv

from data import prepare_datasets
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


def log_evaluation(wandb: Any | None, metrics: dict[str, Any], prefix: str, step: int | None = None) -> None:
    """Send scalar evaluation metrics to the active W&B run without logging secrets."""
    if wandb is None or wandb.run is None:
        return
    payload = {}
    for key, value in metrics.items():
        if isinstance(value, (int, float)):
            payload[f"{prefix}/{key}"] = value
        elif key == "status_counts" and isinstance(value, dict):
            for status, count in value.items():
                payload[f"{prefix}/status_{status}"] = count
    if payload:
        wandb.log(payload, step=step) if step is not None else wandb.log(payload)


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
                # Add dense reward and group statistics to the trainer's W&B record.
                logs.update(config.pop("_reward_diagnostics", {}))
                append_training_step_metrics(config.get("log_path", "logs/logs.txt"), logs)
            return control

        def on_save(self, args: Any, state: Any, control: Any, **_: Any) -> Any:
            """Evaluate the current model and persist checkpoint metrics."""
            if not config.get("run_intermediate_evals", False):
                return control
            metrics, details = evaluate_model(model, tokenizer, test_dataset, config, f"checkpoint-{state.global_step}")
            config["training_context"] = "checkpoint"
            config["_evaluation_epoch"] = state.epoch
            save_evaluation(args.output_dir, f"checkpoint-{state.global_step}", metrics, details, config)
            log_evaluation(wandb, metrics, "evaluation/checkpoint", state.global_step)
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


def run_training(config: dict[str, Any]) -> None:
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
    log_evaluation(wandb, baseline_metrics, "evaluation/baseline", trainer.state.global_step)
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
    log_evaluation(wandb, final_metrics, "evaluation/final", trainer.state.global_step)
    (output_dir / "config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")


def main() -> None:
    """Parse the command line and launch the configured experiment."""
    parser = argparse.ArgumentParser(description="Train Qwen with GRPO on MBPP.")
    parser.add_argument("--config", default="configs/default.yaml", help="Path to a YAML experiment configuration.")
    args = parser.parse_args()
    load_dotenv()
    config = load_config(args.config)
    config["_config_path"] = str(args.config)
    config["_config_yaml"] = Path(args.config).read_text(encoding="utf-8")
    print("Experiment configuration:")
    print(pformat(config, sort_dicts=False), flush=True)
    run_training(config)


if __name__ == "__main__":
    main()
