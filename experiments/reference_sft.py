# This experiment loads MBPP and harder synthetic tasks, trains on their reference solutions, and measures greedy pass@1 on a fixed eight-task batch.
# It first overfits that batch without checkpoints, then runs one full-data SFT epoch with isolated checkpoints after the batch reaches 100% pass@1.

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Any

# Add the repository root so this script can import the shared experiment helpers.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def run_stage(config: dict[str, Any], stage: str) -> bool:
    # Load the shared data, training, evaluation, and tracking libraries.
    import torch
    import wandb
    from experiments.incremental_rejection_sampling_sft import evaluate_greedy, load_model, load_training_tasks, load_config
    from transformers import DataCollatorForSeq2Seq, Trainer, TrainerCallback, TrainingArguments

    # Resolve paths and create a stage-specific output directory.
    root = Path(__file__).resolve().parents[1]
    config_path = Path(config["_config_path"])
    output_root = Path(config["output_dir"])
    if not output_root.is_absolute():
        output_root = root / output_root
    stage_dir = output_root / ("pilot8" if stage == "pilot" else "full")
    stage_dir.mkdir(parents=True, exist_ok=True)

    # Load the same filtered original and synthetic task pool used by the prior run.
    tasks = load_training_tasks(config)
    if any(not str(task.get("reference_code", "")).strip() for task in tasks):
        missing = [str(task["task_id"]) for task in tasks if not str(task.get("reference_code", "")).strip()]
        raise ValueError(f"Reference solutions are missing for {len(missing)} tasks: {missing[:20]}")

    # Reuse the fixed pilot IDs after the first random selection.
    pilot_ids_path = output_root / "pilot-task-ids.json"
    if pilot_ids_path.exists():
        pilot_ids = [str(value) for value in json.loads(pilot_ids_path.read_text(encoding="utf-8"))]
        task_map = {str(task["task_id"]): task for task in tasks}
        pilot_tasks = [task_map[task_id] for task_id in pilot_ids]
    else:
        pilot_tasks = random.Random(int(config["seed"])).sample(tasks, int(config["pilot_task_count"]))
        pilot_ids = [str(task["task_id"]) for task in pilot_tasks]
        pilot_ids_path.write_text(json.dumps(pilot_ids, indent=2) + "\n", encoding="utf-8")
    if len(pilot_tasks) != int(config["pilot_task_count"]):
        raise ValueError(f"Expected {config['pilot_task_count']} fixed pilot tasks, found {len(pilot_tasks)}.")

    # Select the eight-task pilot or the complete task pool as the training set.
    train_tasks = pilot_tasks if stage == "pilot" else tasks
    if stage == "pilot":
        eval_tasks = pilot_tasks
    else:
        task_map = {str(task["task_id"]): task for task in tasks}
        eval_tasks = [task_map[task_id] for task_id in pilot_ids]

    # Seed model and data operations for repeatable training.
    torch.set_num_threads(int(config["torch_num_threads"]))
    torch.manual_seed(int(config["seed"]))
    random.seed(int(config["seed"]))
    model, tokenizer = load_model(config)
    tokenizer.padding_side = "left"
    train_dataset = build_reference_dataset(train_tasks, tokenizer, config)

    # Start a distinct live W&B run for this SFT stage.
    run_name = config["pilot_wandb_run_name"] if stage == "pilot" else config["full_wandb_run_name"]
    run = wandb.init(
        project=config["wandb_project"],
        entity=config.get("wandb_entity"),
        name=run_name,
        job_type=f"reference-sft-{stage}",
        config={**config, "stage": stage, "task_ids": [str(task["task_id"]) for task in train_tasks], "pilot_task_ids": pilot_ids},
        reinit=True,
    )
    run.define_metric("ref_sft/eval_step")
    run.define_metric("ref_sft/pass_at_1", step_metric="ref_sft/eval_step", summary="last")

    # Evaluate greedy pass@1 on the fixed eight tasks before any SFT updates.
    baseline = evaluate_greedy(model, tokenizer, eval_tasks, config)
    eval_path = stage_dir / "evaluations.jsonl"
    with eval_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"step": 0, **baseline}, ensure_ascii=False) + "\n")
    run.log({"ref_sft/eval_step": 0, "ref_sft/pass_at_1": baseline["pass_rate"], "ref_sft/pass_count": baseline["pass_count"], "ref_sft/task_count": baseline["task_count"]})

    # Evaluate the fixed pilot at configured optimizer steps and stop it at full pass@1.
    class ProgressCallback(TrainerCallback):
        # Save all live Trainer metrics and greedy pilot evaluations for audit.
        def on_log(self, args: Any, state: Any, control: Any, logs: dict[str, Any] | None = None, **kwargs: Any) -> Any:
            # Append loss, learning rate, gradient norm, and other Trainer metrics locally.
            if logs:
                with (stage_dir / "training-metrics.jsonl").open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps({"step": int(state.global_step), **logs}, ensure_ascii=False) + "\n")
            return control

        def on_step_end(self, args: Any, state: Any, control: Any, **kwargs: Any) -> Any:
            # Run pass@1 only at the configured interval to keep training efficient.
            interval = int(config["pilot_eval_steps"] if stage == "pilot" else config["full_eval_steps"])
            if state.global_step == 0 or state.global_step % interval != 0:
                return control
            model.eval()
            result = evaluate_greedy(model, tokenizer, eval_tasks, config)
            row = {"step": int(state.global_step), **result}
            with eval_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
            run.log({"ref_sft/eval_step": int(state.global_step), "ref_sft/pass_at_1": result["pass_rate"], "ref_sft/pass_count": result["pass_count"], "ref_sft/task_count": result["task_count"]})
            model.train()
            if stage == "pilot" and result["pass_rate"] == 1.0:
                control.should_training_stop = True
            return control

    # Configure batch-eight reference SFT with checkpoints only for full-data training.
    is_pilot = stage == "pilot"
    training_args = TrainingArguments(
        output_dir=str(stage_dir / "checkpoints"),
        learning_rate=float(config["learning_rate"]),
        num_train_epochs=int(config["full_epochs"]) if not is_pilot else 10000,
        max_steps=int(config["pilot_max_steps"]) if is_pilot else -1,
        per_device_train_batch_size=int(config["sft_per_device_train_batch_size"]),
        gradient_accumulation_steps=int(config["gradient_accumulation_steps"]),
        logging_steps=int(config["logging_steps"]),
        save_strategy="no" if is_pilot else "steps",
        save_steps=int(config["save_steps"]),
        report_to=["wandb"],
        bf16=bool(config.get("bf16", True)) and torch.cuda.is_available(),
        fp16=bool(config.get("fp16", False)) and torch.cuda.is_available(),
        dataloader_num_workers=int(config["dataloader_num_workers"]),
        seed=int(config["seed"]),
        gradient_checkpointing=bool(config.get("gradient_checkpointing", False)),
        gradient_checkpointing_kwargs={"use_reentrant": False},
        disable_tqdm=True,
        remove_unused_columns=False,
    )

    # Train only on dataset reference_code targets and keep prompts masked from the loss.
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        data_collator=DataCollatorForSeq2Seq(tokenizer=tokenizer, model=model, padding=True),
        callbacks=[ProgressCallback()],
    )
    trainer.train()

    # Save the full-data model and record whether the pilot reached its required threshold.
    final = evaluate_greedy(model, tokenizer, eval_tasks, config)
    with eval_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"step": int(trainer.state.global_step), "final": True, **final}, ensure_ascii=False) + "\n")
    run.log({"ref_sft/eval_step": int(trainer.state.global_step), "ref_sft/pass_at_1": final["pass_rate"], "ref_sft/pass_count": final["pass_count"], "ref_sft/task_count": final["task_count"], "ref_sft/final": 1})
    if stage == "full":
        trainer.save_model(str(stage_dir / "final-model"))
        tokenizer.save_pretrained(stage_dir / "final-model")
    run.summary["ref_sft/final_pass_at_1"] = final["pass_rate"]
    run.summary["ref_sft/optimizer_steps"] = int(trainer.state.global_step)
    run.finish()
    return final["pass_rate"] == 1.0 if is_pilot else True


def build_reference_dataset(tasks: list[dict[str, Any]], tokenizer: Any, config: dict[str, Any]) -> Any:
    # Tokenize reference code as a direct continuation of the prompt's open Python fence.
    from datasets import Dataset

    rows = []
    # Mask prompt tokens so loss applies only to the reference solution and end token.
    for task in tasks:
        prompt_ids = tokenizer(str(task["prompt"]), add_special_tokens=True, truncation=True, max_length=int(config["max_prompt_length"]))["input_ids"]
        target_ids = tokenizer(str(task["reference_code"]).strip(), add_special_tokens=False, truncation=True, max_length=int(config["max_completion_length"]))["input_ids"]
        if tokenizer.eos_token_id is not None and len(target_ids) < int(config["max_completion_length"]):
            target_ids.append(tokenizer.eos_token_id)
        rows.append({"input_ids": [*prompt_ids, *target_ids], "attention_mask": [1] * (len(prompt_ids) + len(target_ids)), "labels": [-100] * len(prompt_ids) + target_ids.copy()})
    return Dataset.from_list(rows)


def main() -> None:
    # Parse the dedicated YAML path and select the pilot or full-data stage.
    parser = argparse.ArgumentParser(description="Train on MBPP reference solutions and measure greedy pass@1.")
    parser.add_argument("--config", required=True)
    parser.add_argument("--stage", choices=["pilot", "full"], required=True)
    args = parser.parse_args()

    # Load the existing rejection-sampling task definition without using its solution cache.
    root = Path(__file__).resolve().parents[1]
    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = root / config_path
    from experiments.incremental_rejection_sampling_sft import load_config

    config = load_config(config_path)
    config["_config_path"] = str(config_path)
    for key in ("model_name_or_path", "synthetic_training_tasks_path", "synthetic_tests_path"):
        if config.get(key):
            path = Path(config[key])
            if not path.is_absolute():
                config[key] = str(root / path)
    if not run_stage(config, args.stage):
        raise SystemExit("The eight-task pilot reached its maximum steps before pass@1 reached 100%.")


if __name__ == "__main__":
    # Run the requested reference-SFT stage from the command line.
    main()
