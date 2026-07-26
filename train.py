"""Command-line GRPO training orchestration for MBPP."""

from __future__ import annotations

import argparse
import json
import os
import random
from pathlib import Path
from pprint import pformat
from typing import Any

import yaml
from dotenv import load_dotenv

from data import prepare_datasets
from evaluate import evaluate_model, save_evaluation
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


def _make_reward(config: dict[str, Any]):
    """Bind sandbox configuration to the TRL reward-function contract."""
    timeout = float(config.get("sandbox_timeout_seconds", 3))

    def reward(completions: list[object], test_code: list[str], **kwargs: object) -> list[float]:
        """Score the current GRPO completion batch."""
        return reward_function(completions, test_code, timeout, **kwargs)

    return reward


def _make_callback(model: Any, tokenizer: Any, test_dataset: Any, config: dict[str, Any], wandb: Any | None):
    """Create a callback that evaluates at trainer save steps."""
    from transformers import TrainerCallback

    class EvaluationCallback(TrainerCallback):
        """Run sandbox evaluation whenever the trainer saves a checkpoint."""

        def on_save(self, args: Any, state: Any, control: Any, **_: Any) -> Any:
            """Evaluate the current model and persist checkpoint metrics."""
            metrics, details = evaluate_model(model, tokenizer, test_dataset, config)
            save_evaluation(args.output_dir, f"checkpoint-{state.global_step}", metrics, details)
            log_evaluation(wandb, metrics, "evaluation/checkpoint", state.global_step)
            return control

    return EvaluationCallback()


def run_training(config: dict[str, Any]) -> None:
    """Run baseline evaluation, GRPO training, intermediate evaluations, and final evaluation."""
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from trl import GRPOConfig, GRPOTrainer

    wandb = configure_wandb(config)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Selected device: {device}", flush=True)
    seed_everything(int(config.get("seed", 42)))
    output_dir = Path(config["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)
    train_dataset, test_dataset = prepare_datasets(config)
    tokenizer = AutoTokenizer.from_pretrained(config["model_name_or_path"], trust_remote_code=bool(config.get("trust_remote_code", False)))
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(config["model_name_or_path"], trust_remote_code=bool(config.get("trust_remote_code", False)))
    model.to(device)
    print(f"Model device: {model.device}", flush=True)
    baseline_metrics, baseline_details = evaluate_model(model, tokenizer, test_dataset, config)
    save_evaluation(output_dir, "baseline", baseline_metrics, baseline_details)
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
    trainer = GRPOTrainer(
        model=model,
        processing_class=tokenizer,
        reward_funcs=_make_reward(config),
        train_dataset=train_dataset,
        args=training_args,
        callbacks=[_make_callback(model, tokenizer, test_dataset, config, wandb)],
    )
    log_evaluation(wandb, baseline_metrics, "evaluation/baseline", trainer.state.global_step)
    trainer.train()
    trainer.save_model(str(output_dir / "final"))
    final_metrics, final_details = evaluate_model(model, tokenizer, test_dataset, config)
    save_evaluation(output_dir, "final", final_metrics, final_details)
    log_evaluation(wandb, final_metrics, "evaluation/final", trainer.state.global_step)
    (output_dir / "config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")


def main() -> None:
    """Parse the command line and launch the configured experiment."""
    parser = argparse.ArgumentParser(description="Train Qwen with GRPO on MBPP.")
    parser.add_argument("--config", default="configs/default.yaml", help="Path to a YAML experiment configuration.")
    args = parser.parse_args()
    load_dotenv()
    config = load_config(args.config)
    print("Experiment configuration:")
    print(pformat(config, sort_dicts=False), flush=True)
    run_training(config)


if __name__ == "__main__":
    main()
