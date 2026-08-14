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

## Data and reward

`data.py` loads all 374 examples from the official MBPP training split and uses all 90 examples from the official validation split for evaluation. The official test split is not loaded. `sandbox.py` executes each generated candidate in a timed isolated-mode subprocess. Training uses the fixed dense reward mixture that produced the strongest GRPO-only result. It combines format, syntax, interface, execution, and partial-test progress, and full passes remain worth `1.0` throughout training.

W&B logging is enabled by default. TRL logs reward, reward variance, loss, gradient norm, entropy, completion lengths, clipping, token counts, learning rate, and step time. The project additionally logs baseline, checkpoint, and final pass@1, average reward, and execution status counts to W&B. Baseline evaluation runs before training, checkpoint evaluation runs on saves, and final evaluation runs after training.

Every evaluation appends each prompt, code output, execution result, and award to `logs/logs.txt`. Each run starts with a timestamped `RUN STARTING` header; `logs/` is ignored by Git.

The subprocess sandbox is intended for local experiments. It is not a production-grade hostile-code isolation boundary; use containers or a separate execution service for untrusted workloads.
