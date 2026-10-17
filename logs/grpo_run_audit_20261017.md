# GRPO run audit, 2026-10-17

## Scope and conclusion

This read-only audit covers the active W&B run `kunal-personal/grpo-mbpp/85ae19bd` and local artifacts through optimizer step 126, queried at 2026-10-17 02:30 UTC. The process was still active during the audit. The run is learning on its training rollouts, but the current evidence does not show a durable MBPP improvement. It also does not establish generalization to held-out OpenCode tasks because that evaluation currently returns blank completions.

## Setup and artifacts

- Configuration: `configs/grpo-mbpp-opencode-selfinstruct-from-sft3000-eval100-20261016.yaml`.
- Starting adapter: `outputs/sft-mbpp-opencode-score1-selfinstruct-streaming-resume2000-20261015/checkpoints/checkpoint-3000`.
- Training mix: 591 MBPP training tasks and 1,170,852 pinned OpenCode rows, for 1,171,443 examples. OpenCode revision: `8f3ba5bafe4d6e8db46082cf7ae6741bc370604d`.
- GRPO settings: LoRA rank 16, learning rate 1e-5, 16 completions per prompt, generation batch size 128, DAPO loss, hybrid reward with coefficient 0.75, max 50,000 optimizer steps, checkpoint and EvalPlus cadence 10 steps.
- Run identity: [W&B run 85ae19bd](https://wandb.ai/kunal-personal/grpo-mbpp/runs/85ae19bd).
- EvalPlus checkpoint artifacts: `outputs/grpo-mbpp-opencode-selfinstruct-from-sft3000-eval100-20261016/evalplus/step-{0,30,40,50,60,70,80,90,100,110,120}`.
- Training generations: `outputs/grpo-mbpp-opencode-selfinstruct-from-sft3000-eval100-20261016/reward-trace.jsonl`, sampled while the active process was appending to it.
- Environment observed: Python 3.12.3 and NVIDIA RTX 2000 Ada Generation. Repository HEAD at audit time: `a458d52c`; the working tree also contained unrelated active changes.

## Metrics

W&B reported optimizer step 126. The latest rollout had reward 0.653, full-pass fraction 0.617, test-pass fraction 0.762, interface-valid fraction 0.734, KL 0.077, and entropy 0.130. The logged running average reward was 0.656, versus 0.611 at step 1. These are training-rollout measurements on changing training examples, not held-out OpenCode measurements.

| Optimizer step | MBPP pass@1 | MBPP+ pass@1 |
| ---: | ---: | ---: |
| 0 | 0.590 | 0.500 |
| 30 | 0.603 | 0.500 |
| 40 | 0.603 | 0.503 |
| 50 | 0.616 | 0.513 |
| 60 | 0.624 | 0.513 |
| 70 | 0.608 | 0.503 |
| 80 | 0.608 | 0.503 |
| 90 | 0.601 | 0.503 |
| 100 | 0.601 | 0.497 |
| 110 | 0.598 | 0.503 |
| 120 | 0.598 | 0.503 |

The initial-to-final changes are +0.8 percentage points on MBPP and +0.3 points on MBPP+. The peak MBPP score at step 60 is +3.4 points, then falls 2.6 points by step 120. On the 378 task-level records saved for MBPP, step 0 to 60 had 22 pass gains and 9 losses. Step 60 to 120 had 6 gains and 16 losses. Initial to final had 19 gains and 16 losses. The apparent peak is therefore real task movement, but it is not sustained. Selecting the best of 11 intermediate evaluations would also favor an upward fluctuation. The aggregate MBPP+ scores are used here because the saved per-task `plus_status` counts do not reconcile exactly with the EvalPlus summary text; per-task MBPP+ transition counts are not treated as authoritative.

The local OpenCode holdout evaluation reports 500/500 `format_error`, 0.002 unique completion rate, and 0.998 repeated completion fraction. Its saved examples have blank completions; the fixed training evaluation similarly saved `raw_completion` as only ` ```python\n ` for all 500 tasks. These metrics indicate an evaluation-path failure and cannot be used as model-quality evidence. The independent EvalPlus callback does produce code and provides the MBPP scores above.

## Generation audit

At the trace snapshot, 18,176 training generations had 11,332 full passes (62.3%), 4,540 partial passes (25.0%), 1,868 zero-test failures (10.3%), and 436 syntax errors (2.4%). This file spans retries and was read during active appends, so it is not an exact optimizer-step sample.

Zero-test failures were often more complex than full passes in this trace: mean raw completion length was 957 characters for failed generations versus 581 for passed generations. Class definitions appeared in 7.8% of failures and 1.5% of passes. Imports appeared in 16.5% of failures and 6.8% of passes. Interface validation failed for 49.7% of zero-test failures, 36.8% of partial passes, and 10.1% of full passes. Task complexity is a confounder, so these correlations do not show that verbosity or class use causes failure.

The checkpoint comparisons show mostly semantic regressions rather than an obvious OpenCode-specific output style:

- `Mbpp/782` regressed when the code changed `sum(arr[i:j+1])` to `arr[i:j+1]`, adding a list to an integer.
- `Mbpp/12` regressed when the code began sorting row sums and then indexing the original matrix, rather than sorting rows by their sums.
- `Mbpp/614` regressed when the code summed only `tup[1]` values rather than all values in each tuple.
- `Mbpp/801` returned 1 for three equal inputs instead of returning 3.
- `Mbpp/460` improved when the code changed from flattening every sublist to returning each sublist's first element.

At the early peak, changed solutions that fixed base-test failures were 122 characters shorter on average than their step-0 versions, while newly broken solutions were 110 characters longer. From step 60 to 120, that relationship did not persist: newly broken solutions were 32 characters shorter on average. This is not enough evidence for a general verbosity or OpenCode-style bias. The concrete recurring issue is loss of exact task semantics, especially the target operation or data shape.

## Runtime feasibility

The run advanced from step 1 to step 126 over roughly nine hours after startup, about 4.4 minutes per optimizer step on average. At the configured pace, 50,000 steps would take about 150 days. The current supervisor remains active, but the configured maximum is not a realistic near-term target without a major throughput change. A 300-step diagnostic endpoint would be roughly another 13 hours at the observed pace.

## Evaluation-to-evaluation regression and reward alignment

At the later W&B snapshot, training had advanced to optimizer step 128. EvalPlus still had a complete result only through step 120. The adjacent MBPP pass changes below compare the same 378 saved tasks at each checkpoint. “Lost” means a task passed at the earlier checkpoint and failed at the later checkpoint. “Gained” is the reverse.

| Checkpoints | Lost | Gained | Net change in passing tasks | MBPP score change |
| --- | ---: | ---: | ---: | ---: |
| 0 to 30 | 10 | 15 | +5 | +1.3 points |
| 30 to 40 | 7 | 7 | 0 | 0.0 points |
| 40 to 50 | 1 | 6 | +5 | +1.3 points |
| 50 to 60 | 4 | 7 | +3 | +0.8 points |
| 60 to 70 | 8 | 2 | -6 | -1.6 points |
| 70 to 80 | 4 | 4 | 0 | 0.0 points |
| 80 to 90 | 5 | 2 | -3 | -0.8 points |
| 90 to 100 | 4 | 4 | 0 | 0.0 points |
| 100 to 110 | 6 | 5 | -1 | -0.3 points |
| 110 to 120 | 5 | 5 | 0 | 0.0 points |

The largest adjacent regression was step 60 to 70: 8 previously passing tasks failed, 2 previously failing tasks passed, and the net score dropped 1.6 points. Even a flat score hides task churn: 7 tasks were lost and 7 gained from step 30 to 40. Since evaluation uses greedy decoding on the same saved task set, these flips are checkpoint behavior changes rather than sampling noise in the evaluation prompts.

The reward objective explains why better training rewards can coexist with these regressions. The data mix contains 1,170,852 OpenCode rows and 591 MBPP rows, so MBPP is about 0.05% of the examples. The stream interleaves the two sources according to their row counts. The configured hybrid scalar is 0.75 times full test pass plus 0.25 times the fraction of tests passed. It optimizes tests on the sampled task and has no term that preserves each prior MBPP solution or directly rewards MBPP evaluation. The interface validator is reported as a diagnostic, but its boolean is not included in that scalar reward. The trainer uses 16 completions per prompt and the 128-completion generation batch produces 8 prompt groups per update, so the update direction also depends on a small batch of task groups. KL regularization is configured with beta 0.01, which limits policy movement but does not guarantee per-task retention.

Thus semantic drift is expected under this objective: updates improve expected reward for the sampled, OpenCode-dominated distribution, while shared model parameters can change greedy outputs on other tasks. The finite test suites are also proxies for the full task contract. They can award a solution that matches their assertions while missing an untested edge case. The measured churn is real, but it does not by itself prove catastrophic forgetting or an OpenCode-specific style bias.

## Observed MBPP training exposure

A later read of `task-coverage-trace.jsonl` found 1,176 rollout-group records spanning logged steps 1 to 130, and every record had an `opencode-` task ID. No MBPP task ID appeared in that trace. W&B reports 8 prompt groups per optimizer update. At the configured mixture ratio, 1,040 prompt draws over 130 steps would contain about 0.52 MBPP examples on average, so observing none is expected about 59% of the time under uniform interleaving. The expected interval is about one MBPP prompt per 1,981 training examples, or one per 248 optimizer steps at 8 prompts per step. This directly explains why the early GRPO updates have no MBPP-specific reward signal. It does not establish performance on held-out OpenCode tasks, because the OpenCode holdout evaluator remains broken.

## Limitations

- Training reward is not a held-out OpenCode score. The current OpenCode holdout evaluator is unusable until its blank-output behavior is fixed.
- MBPP showed a small final gain, but no multi-seed replication was run. The intermediate peak is not a final checkpoint result.
- The matched task analysis uses the 378 saved task records. The MBPP+ per-task statuses do not match the reported aggregate closely enough for a reliable paired MBPP+ test.
- Reward-trace counts are a point-in-time read of an append-only file during live training and include retry history.
- No checkpoint was selected or promoted in this audit. EvalPlus labels were used only to measure benchmark outcomes.
