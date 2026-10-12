# GRPO plateau audit, 2026-10-12

The new candidate-level audit changes the hypothesis ranking. The most actionable concern is the combination of predominantly hard synthetic tasks, rewards for incomplete solutions, and normalization within each task group. The prior audit placed too much weight on modest KL and entropy changes. Those changes remain a secondary hypothesis and do not establish harmful policy drift.

## Run and scope

The run is `kunal-personal/grpo-mbpp/mbpphard10x1009`. The model is Qwen/Qwen2.5-Coder-0.5B-Instruct with LoRA rank 16, alpha 32, dropout 0.05, BF16, TRL 0.25.0, and EvalPlus 0.3.1. The configured pool contains 591 original MBPP tasks and 5,319 harder synthetic tasks. The synthetic artifact is `analysis/mbpp_category_synthetic_tasks_harder5319.jsonl`, SHA256 `7e120dd9b7891f3b5a057cfb438734345a73ed2b93b01d9e8239577e74350098`.

The config is `configs/grpo-mbpp-fulltrain-8x16-b128-micro2-workers8-0.5b-50000-dual-greedy-evalplus031-visible1-save10-10x-harder-luna-20261009.yaml`. The output root is `outputs/grpo-mbpp-fulltrain-8x16-b128-micro2-workers8-0.5b-50000-dual-greedy-evalplus031-visible1-save10-10x-harder-luna-20261009`. Paths below are relative to that root unless otherwise stated.

Saved checkpoint-1330 arguments confirm DAPO, group reward scaling, 16 candidates per task, generation batch 128, eight prompt groups per optimizer update, gradient accumulation 64 with microbatch two, temperature 1, top-p 1, one iteration per rollout, beta 0.01, initial learning rate 1e-5, and linear decay over 50,000 steps. The reward is 0.75 times all-tests success plus 0.25 times assertion-pass fraction. Prompts show one assertion. The reward scores all configured assertions. Maximum prompt length is 512 and maximum completion length is 2,048. Dropout remains active during training.

This audit used existing artifacts and W&B history. It did not generate candidates, execute generated code, run training, change tests, or alter checkpoints. Training tests supply RL supervision. Canonical EvalPlus IDs and normalized matching descriptions are excluded from training. The comparisons of benchmark checkpoints are retrospective and must not be reported as independent test-set selection.

## Exact rollout audit

All 172,416 stored candidate rows form 10,776 complete groups of 16. Every group has one task ID and consecutive candidate indices. Scalar rewards were reconstructed from passed and total test counts. All 172,416 reconstructed rewards agree with the saved rewards within 1e-6. This validates the scalar calculation from saved outcomes, not the correctness of test oracles or sandbox execution.

The coverage trace has 10,856 groups. Ordered alignment by task ID, group index, and counts passing at least one, two, and three tests matches every candidate group, with 80 coverage-only rows in eight inserted blocks. These extra coverage rows are excluded from candidate statistics. The audit does not assume that they represent completed optimizer updates. Coverage step labels span 1 through 1,340. Late means a matched step label greater than 900.

| Recorded group category | All groups | Original groups | Hard synthetic groups |
|---|---:|---:|---:|
| No fully correct candidate, varying rewards. | 5,525 | 222 | 5,303 |
| No fully correct candidate, equal rewards. | 1,782 | 162 | 1,620 |
| Both fully correct and incorrect candidates. | 3,314 | 607 | 2,707 |
| All 16 candidates fully correct. | 155 | 101 | 54 |
| Total. | 10,776 | 1,092 | 9,684 |

The no-full-success but variable-reward category represents 51.27% of all groups and 62.51% of nonflat groups. Thus the earlier observation that about 82% of groups have reward variation misses the type of comparison supplied by most of those groups.

Original tasks provide a full-success versus failure comparison in 55.59% of groups. Hard synthetic tasks provide it in 27.95%. Synthetic tasks account for 89.87% of recorded groups. The candidate full-success rate is 6,153/17,472 (35.22%) for originals and 14,054/154,944 (9.07%) for synthetic tasks.

Of 60,673 candidates whose scalar reward is strictly above their own group mean, 42,946 (70.78%) still fail at least one test. This is 1,356/5,893 (23.01%) on originals and 41,590/54,780 (75.92%) on synthetic tasks. These are counts of positive-advantage candidates, not a measurement of gradient contribution or parameter changes. DAPO token weighting, gradients, and KL can change their effective influence.

This pattern persists late. Among 3,198 synthetic groups after step 900, 1,584 (49.53%) contain no full solution but have variable rewards, 543 have equal non-full rewards, 1,033 have a correct/incorrect contrast, and 38 are all correct. In those late synthetic groups, 13,111/19,115 positive-advantage candidates (68.59%) are incomplete.

## Why normalization matters

The installed trainer computes A = (reward minus group mean) divided by (group standard deviation plus 1e-4). In a group with no full solution, the full-success bonus is identically zero. Multiplying all partial rewards by 0.25 also scales their standard deviation by 0.25, so the coefficient largely cancels in the standardized advantage. A modest difference between incomplete solutions can therefore produce advantages of similar numerical scale to differences between successful and failing solutions in another group.

This does not make partial progress intrinsically harmful. It demonstrates that 75% full-success weight in the scalar reward does not allocate 75% of learning to full correctness. Partial-only groups can remain influential while learning fails to transfer to complete benchmark solutions. The mechanism is confirmed; its causal contribution to the plateau requires an ablation. Official TRL 0.25.0 documentation describes group, batch, and unscaled reward alternatives: https://huggingface.co/docs/trl/v0.25.0/en/grpo_trainer.

## Held-out regressions and a correction

Canonical MBPP+ success requires both base_status and plus_status to equal pass. The earlier task-transition audit counted plus_status alone. The aggregate reported MBPP+ scores were correct, but that earlier transition count was not. Corrected paired results follow.

| Step | MBPP | MBPP+ combined |
|---|---:|---:|
| 940 | 235/378 (62.17%). | 204/378 (53.97%). |
| 1,250 | 239/378 (63.23%). | 201/378 (53.17%). |
| 1,330 | 229/378 (60.58%). | 196/378 (51.85%). |

Between steps 1,250 and 1,330, MBPP gains one task and loses 11. Combined MBPP+ gains three and loses eight. The earlier plus-only calculation reported seven losses. Task Mbpp/734 passes extra tests but fails base tests, which explains the correction. Between steps 940 and 1,330, MBPP gains 11 and loses 17, while combined MBPP+ gains eight and loses 16.

All 12 distinct lost tasks in the union of the 1,250-to-1,330 comparisons have complete, parseable functions, 287 to 702 characters long. Ten exhibit semantic changes and two exhibit direct runtime errors. This classification covers the selected regression cohort, not every benchmark failure.

| Task | Observed regression |
|---|---|
| Mbpp/101 | Sorting replaces positional lookup with lookup by value order. |
| Mbpp/119 | Adjacent inequality replaces frequency counting for singleton detection. |
| Mbpp/120 | The code multiplies across tuples instead of within each tuple. |
| Mbpp/240 | Only the final element of list2 replaces the final list1 element, instead of splicing all of list2. |
| Mbpp/413 | Row selection replaces extraction of the requested column. |
| Mbpp/445 | Multiplication of a tuple by a tuple causes TypeError. |
| Mbpp/472 | An any-pair condition replaces the required all-pairs condition. |
| Mbpp/620 | An incorrect adjacent recursive rule replaces divisibility dynamic programming. |
| Mbpp/734 | The code accesses nums[n], causing IndexError on base inputs. |
| Mbpp/788 | Tuple assembly reverses order and splits an appended string into characters. |
| Mbpp/91 | Whole-string equality replaces substring containment. |
| Mbpp/116 | Arithmetic concatenation assumes each tuple item is one decimal digit and fails on larger integers. |

The first 11 tasks are MBPP base regressions. Mbpp/116 is an additional combined-only regression. These outputs show changes to the preferred greedy algorithm. They do not prove whether correct alternatives disappeared from the sampling distribution.

## Setup and alternative hypotheses

Policy drift remains possible but is not established as the primary cause. Prior W&B samples show KL increasing from about 0.018 to 0.043 across thirds and token entropy decreasing from about 0.279 to 0.220. Such changes can occur during useful learning. The 50,000-step linear schedule has reduced learning rate by only 2.66% at step 1,330, so a lower-rate continuation is a reasonable separate test.

Saved arguments enable LoRA dropout 0.05 and disable_dropout=False. Standard Hugging Face rollout generation does not switch the model to eval mode, while greedy evaluation does. This adds noise to the training and rollout policy. Disabling dropout is a controlled setup ablation, not a proven solution.

Policy-ratio clipping is inactive for the saved configuration. With one iteration and steps_per_generation equal to gradient_accumulation_steps, the standard TRL path uses detached current log probabilities as old log probabilities. Ratios equal one. All 300 sampled W&B train/clip_ratio/region_mean rows are zero, as expected. This does not show that parameter updates are small. KL regularization remains active.

All 5,319 synthetic prompts were reconstructed with the saved tokenizer and one visible test. Mean length is 216.19 tokens and maximum length is 463. None exceed 512. This rules out prompt truncation for the hard synthetic data. Original prompt lengths were not measured in this check.

The generation wrapper, reward scorer, and completion loss masks use matching stop boundaries, and DAPO normalization is recomputed after masking. Historical code at 172fe90 already contains this masking. No stop-boundary mismatch was found. The 300 sampled train/completions/clipped_ratio values average 0.00792 and have maximum 0.03125. In this TRL version, that metric checks the final token against EOS and PAD. Custom stop-string termination can also trigger it, so it is not an exact count of completions reaching 2,048 tokens.

Synthetic oracle quality and specification ambiguity remain possible concerns, but this audit did not independently execute teacher solutions or establish widespread incorrect tests. The training and evaluation sets differ in difficulty and source. The observed source imbalance is concrete, while a claim that most synthetic tests are wrong would be unsupported.

## Existing sampled benchmark evidence

The saved 50-task comparison in `outputs/evalplus-pass16-mbpphard10x1009-seed42-20261011/summary.json` already evaluates the base and checkpoint 940. Seed 42 selected task IDs uniformly before expected outputs were loaded. Each model generated 16 completions per task with temperature 1, top-p 1, and maximum 2,048 new tokens.

For MBPP+, sampled pass@1 increased from 36.75% to 49.25%, while observed pass@16 changed from 35/50 (70%) to 36/50 (72%). For MBPP, sampled pass@1 increased from 45.375% to 62%, while pass@16 changed from 39/50 (78%) to 41/50 (82%). Sampled pass@1 here is the mean success probability estimated from the 800 sampled completions, not greedy decoding. The pattern is consistent with making existing successes more probable, with little observed expansion of task coverage on this small subset. It does not establish a full-benchmark ceiling or a late-run loss of sampling capability. There is no matched pass@16 snapshot at step 1,330 in this audit.

## Ranked hypotheses and next experiments

1. The most actionable hypothesis is that group normalization gives substantial learning pressure to incomplete solutions on a training stream dominated by harder synthetic tasks. Keep the hybrid reward and the source mixture fixed, and compare scale_rewards=batch with the current group normalization from the same checkpoint. This retains partial progress while avoiding a separate unit-variance rescaling for each weak partial-only group. The training code needs to expose and pass this setting into GRPOConfig.
2. The source mixture may spend too few updates on task groups that offer a full-correctness comparison. Test a fixed 50% original and 50% synthetic sampling mixture against the existing approximately 10% original mixture, changing only source sampling. A later curriculum can favor tasks that sometimes produce full solutions, with a reserved exploration share for harder tasks. This is training-task selection using training rewards, not selection using EvalPlus labels.
3. A learning rate that remains near 1e-5 may prevent stable consolidation of a better greedy solution. Compare a 3e-6 continuation with 1e-5, changing only learning rate. A further independent test can set disable_dropout=True. Do not change reward scaling, mixture, learning rate, and dropout in a single comparison.
4. Partial-test reward could favor shortcuts that fail broader tests. Stronger independently validated training tests are a later test if the first experiments fail. These logs do not justify rewriting original tests or assuming weak tests are the primary cause.

Use checkpoint 940 for an MBPP+ development objective because it is the strongest observed checkpoint on that metric. Run the unchanged control and each ablation for the same proposed 300 optimizer steps, log every 50 steps, and compare matched rollout and token budgets as well as step counts. More than one seed is needed before treating a small difference as reliable. Treat the repeatedly inspected 378-task benchmark as development data and reserve independent data for final confirmation.

For the user's goal of moving greedy pass@1 toward sampled pass@20, reuse the existing 50 task IDs and base/940 generations and add a matched late-checkpoint sampling measurement. If sampled coverage is stable but greedy accuracy falls, focus on probability allocation and stabilization. If sampled coverage also falls, investigate retention and exploration. Do not infer that base pass@20 is a theoretical greedy ceiling or that one of these changes guarantees 75%.

## Reproduction and artifact identities

The analysis baseline was repository commit 521ae77. The step-1,250 evaluation record lists 32cd7cb, and step 1,330 lists 49103a5. Training arguments were read from the saved checkpoint, not inferred solely from the current YAML.

The reward trace SHA256 is `86aa585492b6726833bd77e70fe01be1b3c4c43ab301b5f63548ad77fc92108b`. The coverage trace SHA256 is `347bee3ca0800f1cd6a4777ea579df1585de920d820dbea3568bebfaab6e6532`. The checkpoint-1330/training_args.bin SHA256 is `c847ada0acd60bbfeed2d7ad1869c600f0a4c3a2fc8587a40457f2f290551866`.

To reproduce group counts, stream reward-trace.jsonl in groups of 16. Require one task ID and consecutive indices per group. Full success requires total_tests greater than zero and passed_tests equal to total_tests. Compare the group's minimum and maximum scalar rewards to identify flat groups. Count a positive candidate when its reward is strictly greater than its group's arithmetic mean. Classify source by the synthetic- task-ID prefix. Align to task-coverage-trace.jsonl using difflib.SequenceMatcher with autojunk=False and signatures of task ID, first candidate index divided by 16, and the three threshold counts. Exclude coverage-only rows.

Evaluation files are `evalplus/step-{940,1250,1330}/mbpp/qwen2_chat_temp_0.0/eval_results.json`. Use the one saved result per task, calculate base success and the conjunction for combined success, join by task ID, and count pass-to-fail and fail-to-pass transitions. The regression classification above was performed by inspecting the complete saved code. It is a semantic code audit, not a new execution replay.
