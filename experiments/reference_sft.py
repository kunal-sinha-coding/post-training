# This experiment loads configured MBPP reference examples, trains a fresh GRPO-matched LoRA adapter, evaluates the optional base model and every saved epoch, and preserves resumable checkpoints.
# The supervisor restarts failed attempts from the newest complete Trainer checkpoint and repeats this cycle until the configured epoch limit is complete.

from __future__ import annotations

import argparse
import json
import os
import random
import secrets
import sys
import time
from pathlib import Path
from typing import Any

# Add the repository root so direct execution can import shared experiment code.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def append_jsonl(path: Path, record: dict[str, Any]) -> None:
    # Append and flush one durable experiment record.
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def build_reference_dataset(tasks: list[dict[str, Any]], tokenizer: Any, config: dict[str, Any]) -> Any:
    # Tokenize each prompt and reference while masking prompt tokens from the causal loss.
    from datasets import Dataset

    rows = []
    for task in tasks:
        prompt_ids = tokenizer(str(task["prompt"]), add_special_tokens=True, truncation=True, max_length=int(config["max_prompt_length"]))["input_ids"]
        target_ids = tokenizer(str(task["reference_code"]).strip(), add_special_tokens=False, truncation=True, max_length=int(config["max_completion_length"]))["input_ids"]
        if tokenizer.eos_token_id is not None and len(target_ids) < int(config["max_completion_length"]):
            target_ids.append(tokenizer.eos_token_id)
        rows.append({"input_ids": [*prompt_ids, *target_ids], "attention_mask": [1] * (len(prompt_ids) + len(target_ids)), "labels": [-100] * len(prompt_ids) + target_ids.copy()})
    return Dataset.from_list(rows)


def load_model(config: dict[str, Any]) -> tuple[Any, Any]:
    # Load only the configured original base model and attach a new GRPO-matched LoRA adapter.
    import torch
    from peft import LoraConfig, get_peft_model
    from transformers import AutoModelForCausalLM, AutoTokenizer

    model_path = str(config["model_name_or_path"])
    tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=False, local_files_only=True)
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "left"
    dtype = torch.bfloat16 if bool(config.get("bf16", True)) else torch.float16
    model = AutoModelForCausalLM.from_pretrained(model_path, torch_dtype=dtype, device_map="cuda", trust_remote_code=False, local_files_only=True)
    model = get_peft_model(model, LoraConfig(
        task_type="CAUSAL_LM",
        r=int(config["lora_r"]),
        lora_alpha=int(config["lora_alpha"]),
        lora_dropout=float(config["lora_dropout"]),
        target_modules=list(config["lora_target_modules"]),
    ))
    model.config.use_cache = False
    model.print_trainable_parameters()
    return model, tokenizer


def start_wandb(config: dict[str, Any], stage_dir: Path) -> Any:
    # Resume one stable W&B run ID across supervisor restarts.
    from dotenv import load_dotenv
    import wandb

    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    if not os.getenv("WANDB_API_KEY"):
        raise RuntimeError("W&B logging is enabled, but WANDB_API_KEY is unavailable.")
    id_path = stage_dir / "wandb-run-id.json"
    if id_path.exists():
        run_id = str(json.loads(id_path.read_text(encoding="utf-8"))["run_id"])
    else:
        run_id = secrets.token_hex(4)
        id_path.write_text(json.dumps({"run_id": run_id}) + "\n", encoding="utf-8")
    run = wandb.init(
        project=str(config["wandb_project"]),
        entity=str(config["wandb_entity"]),
        name=str(config.get("full_wandb_run_name", config.get("wandb_run_name"))),
        id=run_id,
        resume="allow",
        job_type="reference-sft-full",
        config={key: value for key, value in config.items() if not key.startswith("_")},
    )
    run.define_metric("optimizer_step")
    run.define_metric("sft/*", step_metric="optimizer_step")
    run.define_metric("evalplus/*", step_metric="optimizer_step")
    run.define_metric("training_set/*", step_metric="optimizer_step")
    print(f"W&B run: {run.url}", flush=True)
    return run


def evaluate_checkpoint(model: Any, tokenizer: Any, train_dataset: Any, config: dict[str, Any], stage_dir: Path, run: Any, epoch: int, step: int, checkpoint_dir: Path) -> None:
    # Run canonical EvalPlus and full training-set greedy evaluation from the same saved adapter.
    import gc
    import torch
    from train import evaluate_training_mbpp, run_qwen_evalplus

    completion_marker = stage_dir / f"epoch-{epoch:05d}.complete.json"
    if completion_marker.exists():
        return
    model.eval()
    model.to("cpu")
    torch.cuda.empty_cache()
    try:
        evalplus_result = run_qwen_evalplus(checkpoint_dir, stage_dir, f"epoch-{epoch:05d}")
        training_result = evaluate_training_mbpp(checkpoint_dir, train_dataset, config, f"training-epoch-{epoch:05d}")
        evaluation = {
            "epoch": epoch,
            "optimizer_step": step,
            "checkpoint": str(checkpoint_dir),
            "evalplus": evalplus_result["metrics"],
            "training_set": training_result["metrics"],
            "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        append_jsonl(stage_dir / "evaluations.jsonl", evaluation)
        payload = {"optimizer_step": step, "epoch": epoch}
        payload.update({f"evalplus/{key}": value for key, value in evalplus_result["metrics"].items() if isinstance(value, (int, float))})
        payload.update({f"training_set/{key}": value for key, value in training_result["metrics"].items() if isinstance(value, (int, float))})
        run.log(payload)
        completion_marker.write_text(json.dumps(evaluation, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
        print(f"Completed epoch {epoch} evaluation at optimizer step {step}: MBPP={evalplus_result['metrics'].get('mbpp_pass_at_1')} MBPP+={evalplus_result['metrics'].get('mbpp_plus_pass_at_1')} training_pass@1={training_result['metrics'].get('pass_at_1')}", flush=True)
    finally:
        gc.collect()
        torch.cuda.empty_cache()
        model.to("cuda")
        model.train()


def run_training(config: dict[str, Any], config_path: Path, resume_from_checkpoint: str | None) -> None:
    # Train the full reference dataset and evaluate each complete epoch from its durable checkpoint.
    import torch
    import wandb
    from transformers import DataCollatorForSeq2Seq, Trainer, TrainerCallback, TrainingArguments
    from experiments.incremental_rejection_sampling_sft import load_config, load_training_tasks

    root = Path(__file__).resolve().parents[1]
    output_root = Path(config["output_dir"])
    if not output_root.is_absolute():
        output_root = root / output_root
    stage_dir = output_root / "full"
    checkpoint_root = stage_dir / "checkpoints"
    checkpoint_root.mkdir(parents=True, exist_ok=True)
    config["log_path"] = os.devnull
    config["_config_path"] = str(config_path)
    tasks = load_training_tasks(config)
    if len(tasks) != int(config["expected_train_samples"]):
        raise ValueError(f"Expected {config['expected_train_samples']} tasks, loaded {len(tasks)}.")
    missing = [str(task["task_id"]) for task in tasks if not str(task.get("reference_code", "")).strip()]
    if missing:
        raise ValueError(f"Reference solutions are missing for {len(missing)} tasks: {missing[:20]}.")
    random.seed(int(config["seed"]))
    torch.manual_seed(int(config["seed"]))
    torch.set_num_threads(int(config["torch_num_threads"]))
    model, tokenizer = load_model(config)
    train_dataset = build_reference_dataset(tasks, tokenizer, config)
    run = start_wandb(config, stage_dir)
    run.config.update({"task_count": len(tasks), "task_ids": [str(task["task_id"]) for task in tasks], "resume_from_checkpoint": resume_from_checkpoint}, allow_val_change=True)

    # Measure the untrained base model at optimizer step zero when the experiment requests a direct baseline.
    if bool(config.get("run_baseline_evaluation", False)):
        evaluate_checkpoint(model, tokenizer, tasks, config, stage_dir, run, 0, 0, Path(config["model_name_or_path"]))

    class ProgressCallback(TrainerCallback):
        # Log training metrics live and evaluate each saved epoch checkpoint.
        def on_log(self, args: Any, state: Any, control: Any, logs: dict[str, Any] | None = None, **kwargs: Any) -> Any:
            # Send each Trainer log row to the local trace and W&B immediately.
            if logs:
                row = {"optimizer_step": int(state.global_step), "epoch": float(state.epoch or 0), **logs}
                append_jsonl(stage_dir / "training-metrics.jsonl", row)
                run.log({"optimizer_step": int(state.global_step), **{f"sft/{key}": value for key, value in logs.items() if isinstance(value, (int, float))}})
            return control

        def on_save(self, args: Any, state: Any, control: Any, **kwargs: Any) -> Any:
            # Evaluate only after the complete epoch checkpoint has been written.
            epoch = int(round(float(state.epoch or 0)))
            if epoch > 0:
                checkpoint_dir = checkpoint_root / f"checkpoint-{state.global_step}"
                if not checkpoint_dir.is_dir():
                    raise FileNotFoundError(f"Trainer reported a save but the checkpoint is missing: {checkpoint_dir}.")
                evaluate_checkpoint(model, tokenizer, tasks, config, stage_dir, run, epoch, int(state.global_step), checkpoint_dir)
            return control

        def on_train_begin(self, args: Any, state: Any, control: Any, **kwargs: Any) -> Any:
            # Finish a checkpoint evaluation interrupted by a previous process failure.
            epoch = int(round(float(state.epoch or 0)))
            if resume_from_checkpoint and epoch > 0:
                checkpoint_dir = Path(resume_from_checkpoint)
                evaluate_checkpoint(model, tokenizer, tasks, config, stage_dir, run, epoch, int(state.global_step), checkpoint_dir)
            return control

    training_args = TrainingArguments(
        output_dir=str(checkpoint_root),
        learning_rate=float(config["learning_rate"]),
        num_train_epochs=int(config["full_epochs"]),
        max_steps=-1,
        per_device_train_batch_size=int(config["sft_per_device_train_batch_size"]),
        gradient_accumulation_steps=int(config["gradient_accumulation_steps"]),
        logging_steps=int(config["logging_steps"]),
        save_strategy="epoch",
        save_total_limit=None,
        report_to=[],
        bf16=bool(config.get("bf16", True)) and torch.cuda.is_available(),
        fp16=bool(config.get("fp16", False)) and torch.cuda.is_available(),
        dataloader_num_workers=int(config["dataloader_num_workers"]),
        seed=int(config["seed"]),
        gradient_checkpointing=bool(config.get("gradient_checkpointing", True)),
        gradient_checkpointing_kwargs={"use_reentrant": False},
        disable_tqdm=True,
        remove_unused_columns=False,
        save_only_model=False,
    )
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        data_collator=DataCollatorForSeq2Seq(tokenizer=tokenizer, model=model, padding=True),
        callbacks=[ProgressCallback()],
    )
    trainer.train(resume_from_checkpoint=resume_from_checkpoint)
    trainer.save_model(str(stage_dir / "final-model"))
    tokenizer.save_pretrained(stage_dir / "final-model")
    run.summary["sft/completed_epochs"] = int(config["full_epochs"])
    run.summary["sft/optimizer_steps"] = int(trainer.state.global_step)
    run.finish(exit_code=0)
    (stage_dir / "completed.json").write_text(json.dumps({"completed_epochs": int(config["full_epochs"]), "optimizer_steps": int(trainer.state.global_step)}) + "\n", encoding="utf-8")


def main() -> None:
    # Parse the experiment configuration and optional checkpoint resume path.
    parser = argparse.ArgumentParser(description="Train reference SFT with per-epoch full EvalPlus and training-set evaluation.")
    parser.add_argument("--config", required=True)
    parser.add_argument("--resume-from-checkpoint", default=None)
    args = parser.parse_args()
    from experiments.incremental_rejection_sampling_sft import load_config

    root = Path(__file__).resolve().parents[1]
    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = root / config_path
    config = load_config(config_path)
    for key in ("model_name_or_path", "synthetic_training_tasks_path", "synthetic_tests_path"):
        if config.get(key):
            path = Path(config[key])
            if not path.is_absolute():
                config[key] = str(root / path)
    run_training(config, config_path, args.resume_from_checkpoint)


if __name__ == "__main__":
    # Run the configured full-data reference-SFT experiment.
    main()
