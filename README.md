# post-training

This repository contains a small GRPO experiment that trains `Qwen/Qwen3.5-0.8B` to generate Python solutions for MBPP.

## Setup

```bash
python -m pip install -r requirements.txt
```

The first run downloads the model and MBPP from Hugging Face. A CUDA-capable environment is recommended. Copy `.env.example` to `.env` and set `WANDB_API_KEY`; `.env` is ignored by Git and must never be committed.

## Run

```bash
accelerate launch --num_processes 1 train.py --config configs/debug.yaml
accelerate launch --num_processes 1 train.py --config configs/default.yaml
```

The debug configuration limits the dataset and training steps. `reuse_baseline: true` reuses both cached baseline JSON files when present; set it to `false` to recompute baseline evaluation. `run_intermediate_evals` defaults to `false`, so evaluation runs only at the end unless explicitly enabled. Each run writes its configuration, baseline metrics, checkpoint metrics, final metrics, per-example details, and model artifacts under its configured `output_dir`.

## Data and reward

`data.py` loads MBPP, normalizes task descriptions and assertions, and creates a deterministic 80/20 train-test split. No validation set is used. `sandbox.py` executes each generated candidate in a timed isolated-mode subprocess. A candidate receives reward `1.0` only when all supplied assertions pass; syntax errors, failed assertions, empty responses, and timeouts receive `0.0`.

W&B logging is enabled by default. TRL logs reward, reward variance, loss, gradient norm, entropy, completion lengths, clipping, token counts, learning rate, and step time. The project additionally logs baseline, checkpoint, and final pass@1, average reward, and execution status counts to W&B. Baseline evaluation runs before training, checkpoint evaluation runs on saves, and final evaluation runs after training.

Every evaluation appends each prompt, code output, execution result, and award to `logs/logs.txt`. Each run starts with a timestamped `RUN STARTING` header; `logs/` is ignored by Git.

The subprocess sandbox is intended for local experiments. It is not a production-grade hostile-code isolation boundary; use containers or a separate execution service for untrusted workloads.

## Execution flow

```mermaid
flowchart TD
    A[User runs accelerate launch train.py --config] --> B[load_config]
    B --> C[seed_everything]
    C --> D[prepare_datasets]
    D --> E[load_mbpp]
    E --> F[normalize_record and split_dataset]
    F --> G[Train and test Dataset]
    G --> H[Load tokenizer and model]
    H --> I[evaluate_model baseline]
    I --> J[evaluate_texts]
    J --> K[execute_code in sandbox]
    K --> L[Save baseline metrics and details]
    L --> M[Authenticate W&B and create GRPOConfig and GRPOTrainer]
    M --> N[trainer.train]
    N --> O[Checkpoint save callback]
    P --> I2[evaluate_model checkpoint]
    I2 --> R2[Save checkpoint metrics, details, and logs]
    Q --> S[Save final model and tokenizer]
    S --> R[evaluate_model final]
    R --> T[Save final metrics, details, and logs]
```
