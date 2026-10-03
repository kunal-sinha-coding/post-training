# MBPP checkpoint evaluation comparison

Both selected checkpoints were sampled and evaluated on the same 378 EvalPlus MBPP tasks. The MBPP table scores the original base tests. The MBPP+ table scores the base and extra tests together. Each task has 16 temperature-sampled candidates.

## Checkpoint selection

All 131 saved checkpoint evaluation logs from W&B run `c4fthzd3` were scanned. The MBPP+ winner is step 630. The MBPP base-test winner is step 830. The MBPP values below use the saved greedy checkpoint logs only for checkpoint selection; the tables below are fresh 16-sample evaluations.

| Checkpoint | Selection basis | Saved MBPP pass@1 | Saved MBPP+ pass@1 |
|---|---|---:|---:|
| 630 | Highest saved MBPP+ greedy eval pass@1 | 64.0% | 54.0% |
| 830 | Highest saved MBPP greedy eval pass@1 | 65.1% | 53.2% |

## MBPP results

The verifier rows report expected accuracy over every uniformly selected subset of size k from the 16 candidates for each task. The raw row is the standard unbiased pass@k estimate.

| Checkpoint | Method | pass@1 | pass@2 | pass@4 | pass@8 | pass@16 |
|---:|---|---:|---:|---:|---:|---:|
| 630 | Raw sampling | 58.85% | 65.96% | 71.42% | 76.27% | 80.42% |
| 630 | Execution verifier | 58.85% | 64.86% | 69.11% | 72.69% | 75.40% |
| 630 | Execution verifier + joint output clustering | 58.85% | 64.87% | 69.20% | 72.70% | 76.19% |
| 830 | Raw sampling | 60.63% | 67.04% | 71.47% | 74.65% | 76.98% |
| 830 | Execution verifier | 60.63% | 65.97% | 69.40% | 71.64% | 72.22% |
| 830 | Execution verifier + joint output clustering | 60.63% | 66.01% | 69.59% | 71.84% | 73.02% |

## MBPP+ results

The verifier rows report expected accuracy over every uniformly selected subset of size k from the 16 candidates for each task. The raw row is the standard unbiased pass@k estimate.

| Checkpoint | Method | pass@1 | pass@2 | pass@4 | pass@8 | pass@16 |
|---:|---|---:|---:|---:|---:|---:|
| 630 | Raw sampling | 49.74% | 56.17% | 61.02% | 65.16% | 69.05% |
| 630 | Execution verifier | 49.74% | 53.98% | 56.69% | 58.61% | 59.52% |
| 630 | Execution verifier + joint output clustering | 49.74% | 53.98% | 56.82% | 58.79% | 60.05% |
| 830 | Raw sampling | 51.09% | 57.04% | 61.33% | 64.76% | 67.72% |
| 830 | Execution verifier | 51.09% | 55.21% | 57.80% | 59.43% | 60.05% |
| 830 | Execution verifier + joint output clustering | 51.09% | 55.22% | 57.92% | 59.51% | 60.32% |

## Setup and methodology

- Model: `Qwen/Qwen2.5-Coder-0.5B-Instruct`, with the LoRA adapter from run `c4fthzd3` at checkpoints 630 and 830.
- Sampling: vLLM 0.10.2, 16 candidates per task, temperature 1.0, top-p 1.0, seed 42, maximum 2,048 new tokens, using the repository EvalPlus prompt wrapped in Qwen ChatML.
- Dataset: EvalPlus 0.3.1 MBPP release, 378 tasks, dataset hash `ee43ecabebf20deef4bb776a405ac5b1`.
- Scoring: EvalPlus checked both base and extra tests. `MBPP` success means `base_status == pass`; `MBPP+` success means both base and plus status are pass. Early-exit test checking was enabled, with a 1-second minimum test limit, 4x ground-truth time factor, four workers, and a 2 GiB per-test-process memory limit.
- Execution verifier: test each candidate against the first visible assertion, then select the first visible-passing candidate in each subset, falling back to the earliest candidate if none passes.
- Joint output clustering: among visible-passing candidates, run the candidate on the remaining MBPP base-test inputs without reading expected outputs. Select the earliest candidate in a largest exact typed-output cluster; if no candidate yields a complete signature, fall back to execution selection.
- Selection separation: candidate verifier selections were fixed before full-test labels were read. MBPP labels were used only for the MBPP table; combined base-plus-extra labels were used only for the MBPP+ table.
- Selection caveat: each checkpoint was chosen using greedy pass@1 on the same benchmark family later used for reporting, so these checkpoint-comparison results have selection bias and are not an independent held-out estimate.
- Environment: Python 3.12, PyTorch 2.8.0+cu128, NVIDIA RTX 2000 Ada Generation with 16,380 MiB memory. Repository source commit `ba8b794085828aef55d617ac1d2b7a20dd2dee89`.
- Raw candidates, EvalPlus results, verifier selection counts and metrics, and the exact sampling and verifier scripts are in ignored artifact `outputs/mbpp-eval-best-checkpoints-20261003/`.
