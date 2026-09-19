# post-training

This repository contains a small GRPO experiment that trains `Qwen/Qwen3.5-0.8B` to generate Python solutions for MBPP.

## Setup

```bash
python -m pip install -r requirements.txt
```

`start.sh` also clones or updates the skills repository and registers every child directory containing `SKILL.md` under `${CODEX_HOME:-~/.codex}/skills`. Set `SKILLS_REPOSITORY_URL` to use a different skills repository.

The first run downloads the model and MBPP from Hugging Face. A CUDA-capable environment is recommended. Copy `.env.example` to `.env` and set `WANDB_API_KEY`; `.env` is ignored by Git and must never be committed.

## Run

```bash
accelerate launch --num_processes 1 train.py --config configs/debug.yaml
accelerate launch --num_processes 1 train.py --config configs/default.yaml
```

The debug configuration limits the dataset and training steps. `run_baseline_evaluation: false` skips the baseline. When it is enabled, `reuse_baseline: true` reuses both cached baseline JSON files when present, while `false` recomputes the baseline. `run_intermediate_evals` controls checkpoint evaluation. Each run writes its configuration, available evaluation metrics, per-example details, and model artifacts under its configured `output_dir`.

## Experiment evaluation protocol

Candidate selection must not use the ground-truth answer for the task being evaluated. During selection, use only answer-independent evidence such as whether the candidate executes, its observable outputs, resource behavior, and agreement with other candidates. Ground truth may be used afterward only to measure the selected method's benchmark score, and that measurement must be kept separate from candidate selection. If an experiment request is ambiguous about this boundary, clarify it before proceeding.

## Data and reward

`data.py` loads every example from the official MBPP train, validation, and test splits. It excludes all 399 task IDs used by the installed canonical EvalPlus MBPP runner, leaving 572 training examples. The optional Hugging Face EvalPlus dataset has 378 tasks and is a subset of the canonical benchmark. `sandbox.py` executes each generated candidate in a timed isolated-mode subprocess. Training reward measures the fraction of original MBPP tests passed. The canonical MBPP+ evaluation uses the full augmented tests.

W&B logging is enabled by default. TRL logs reward, reward variance, loss, gradient norm, entropy, completion lengths, clipping, token counts, learning rate, and step time. The project additionally logs baseline, checkpoint, and final pass@1, average reward, and execution status counts to W&B. Baseline evaluation runs before training, checkpoint evaluation runs on saves, and final evaluation runs after training.

Every evaluation appends each prompt, code output, execution result, and award to `logs/logs.txt`. Each run starts with a timestamped `RUN STARTING` header; `logs/` is ignored by Git.

The subprocess sandbox is intended for local experiments. It is not a production-grade hostile-code isolation boundary; use containers or a separate execution service for untrusted workloads.
