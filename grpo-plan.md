# GRPO MBPP Training Project Plan

## Summary

Implement a minimal GRPO training project for MBPP using `Qwen/Qwen3.5-0.8B`, with deterministic 80/20 train-test splitting, sandboxed code execution, baseline/intermediate/final evaluation, YAML configurations, and a Mermaid execution-flow diagram.

## Implementation Changes

- Preserve the original brief by renaming `grpo-project.md` to `grpo-prompt.md`.
- Add `configs/default.yaml` and `configs/debug.yaml`.
- Add `data.py`, `sandbox.py`, `evaluate.py`, and `train.py`.
- Add dependency metadata and tests for dataset handling, sandbox execution, metrics, and orchestration.
- Keep `README.md` synchronized with the call graph, persisted artifacts, commands, and sandbox limitations.

## Interfaces and Artifacts

- `data.py` loads, normalizes, prompts, and deterministically splits MBPP.
- `sandbox.py` executes candidates and returns structured results and rewards.
- `evaluate.py` evaluates checkpoints and returns serializable metrics.
- `train.py` exposes `python train.py --config configs/default.yaml`.
- Runs save configuration, checkpoints, baseline/intermediate/final metrics, samples, and metadata.

## Test Plan

- Test deterministic splitting, prompt construction, sandbox outcomes, timeout handling, reward conversion, metric aggregation, and a mocked training smoke path.
- Run the debug configuration and static compilation checks.

## Assumptions

- Dataset source: `google-research-datasets/mbpp`.
- The requested 80/20 split supersedes the canonical MBPP partitions.
- The initial reward is binary: all provided tests pass or they do not.
- Evaluation defaults to pass@1, with configurable completion count.
- The local subprocess sandbox is for experiments, not production-grade hostile-code isolation.
