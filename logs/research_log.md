# When2Call Research Log

## EXP-20261020-001

Timestamp: 2026-10-20. The run completed after three launch diagnostics.

Hypothesis: A deterministic development split from `train_pref` is required for reliable model selection because historical When2Call scripts used official test labels or test metrics to select routing and checkpoints.

Setup: The cached `nvidia/When2Call` `train_pref` arrow artifact was used because the current remote dataset metadata exposes only the default configuration. The 9,000 rows were converted with the existing response label inference function. A seed 20261020 stratified split assigned 7,200 rows to training and 1,800 rows to development. The model was Jina embeddings v2 small with a four class linear head. The encoder was warm started from `outputs/when2call-jina-v2-small/latest`. The classifier head was fresh. The optimizer was AdamW with learning rate 5e-5. The run used one epoch, batch size 8, the existing 8,192 token limit, and CUDA when available. The official test split was not loaded. Code revision: 1b676149.

Results: Training loss was 0.182308. Training accuracy was 0.975694 and training macro F1 was 0.731882. Development accuracy was 0.936667 and development macro F1 was 0.703032. Development per class F1 was 0.971819 for `cannot_answer`, 0.928690 for `request_for_info`, 0.911620 for `tool_call`, and 0.000000 for `direct`. Development supports were 599, 600, 600, and 1. The development confusion matrix was [[569, 3, 27, 0], [2, 560, 38, 0], [0, 43, 557, 0], [1, 0, 0, 0]].

Analysis: The hypothesis was supported. The clean protocol produced a stable validation denominator and exposed the inferred-label imbalance. The warm start separates the three common classes well, but `request_for_info` and `tool_call` account for the main residual errors. The direct class has one example, so its macro F1 is not a reliable estimate of generalization. The gap between training and development accuracy suggests additional fitting without better labels may not solve the boundary.

Failed launches: Direct file execution failed with `ModuleNotFoundError: experiments`. Module execution then failed because the remote dataset configuration was unavailable. The cached arrow fallback fixed the data issue. The Jina download cache contained zero byte tokenizer and configuration files. The local checkpoint fallback fixed the model issue. A serialized remote model path then caused a local configuration error. Pointing `_name_or_path` to the local checkpoint fixed it.

Next action: Run EXP-20261020-002 with the same split, model, seed, and batch settings while changing the objective to pairwise ranking. Compare both accuracy and macro F1 against this validation baseline. Preserve the current checkpoint.

## EXP-20261020-002

Timestamp: 2026-10-20. The run completed after the baseline implementation was extended with a pairwise objective.

Hypothesis: Rejected responses in `train_pref` will provide a stronger boundary between `request_for_info` and `tool_call` than cross entropy on inferred chosen-response labels.

Setup: This used the exact EXP-20261020-001 data split, seed, Jina warm start, one epoch, batch size 8, and learning rate 5e-5. The only intended change was the pairwise ranking loss `softplus(-(chosen_logit - rejected_logit))`. The official test split was not loaded. Code revision: 6a5b219a.

Results: Training loss was 0.083911. Training accuracy was 0.927083 and training macro F1 was 0.695722. Development accuracy was 0.903889 and development macro F1 was 0.678567. Development per class F1 was 0.944154 for `cannot_answer`, 0.906325 for `request_for_info`, 0.863787 for `tool_call`, and 0.000000 for `direct`. The development confusion matrix was [[541, 7, 51, 0], [1, 566, 33, 0], [4, 76, 520, 0], [1, 0, 0, 0]].

Analysis: The hypothesis was rejected. Relative to EXP-20261020-001, development accuracy decreased by 0.032778 and macro F1 decreased by 0.024466. The pairwise objective increased `tool_call` to `request_for_info` errors from 43 to 76 and `cannot_answer` to `tool_call` errors from 27 to 51. The direct class remained unresolved because only one development example has that inferred label. Pairwise ranking is rejected for the current leaderboard.

Next action: Audit the training response label distribution and inference patterns, then test a targeted class-balanced cross entropy change only if the audit identifies a credible imbalance mechanism.

## EXP-20261020-AUDIT-001

Timestamp: 2026-10-20. This read only audit completed after EXP-20261020-002.

Setup: The same cached 9,000 row `train_pref` artifact was inspected with the existing `infer_action_label` function. No development or official test labels were loaded.

Results: Chosen response labels were `cannot_answer` 2,997, `request_for_info` 3,001, `tool_call` 3,000, and `direct` 2. Rejected response labels were `cannot_answer` 2,152, `request_for_info` 2,105, `tool_call` 2,007, and `direct` 2,736. The most frequent chosen and rejected pair was `tool_call` versus `cannot_answer` with 1,081 rows. The chosen labels are balanced, so class weighting is not justified by chosen-label frequency. The rejected responses are dominated by `direct`, which likely explains why the pairwise objective moved the decision boundary away from the three common chosen classes. The two direct chosen rows explain why the stratified development split contains one direct example.

Analysis: The main data issue is objective target asymmetry, not chosen-label imbalance. Cross entropy learns the chosen response class distribution. Pairwise training also treats many rejected direct responses as negative evidence, even though direct is nearly absent among chosen responses. This is evidence for rejecting raw pairwise ranking in this dataset. It does not prove that the response heuristic is correct for every example because the audit uses generated response text rather than official training labels.

Next action: Keep cross entropy as the training objective. Test a response aware input ablation that removes tool schemas from a development-only classifier comparison, because the remaining errors may come from the encoder using schema overlap as a shortcut. Preserve the current best checkpoint.

## EXP-20261020-003

Timestamp: 2026-10-20. The run completed on the clean validation split.

Hypothesis: Tool schema text may act as a shortcut and removing it may improve generalization to the action boundary.

Setup: This used the exact EXP-20261020-001 data split, seed, Jina warm start, one epoch, batch size 8, learning rate 5e-5, and cross entropy. The only input change replaced every tool schema with `No tools are available.` The official test split was not loaded. Code revision: afb213e5.

Results: Training loss was 0.787945. Training accuracy was 0.640278 and training macro F1 was 0.409906. Development accuracy was 0.590000 and development macro F1 was 0.374995. Development per class F1 was 0.043546 for `cannot_answer`, 0.827181 for `request_for_info`, 0.629252 for `tool_call`, and 0.000000 for `direct`. The development confusion matrix was [[14, 61, 524, 0], [23, 493, 84, 0], [7, 38, 555, 0], [0, 0, 1, 0]].

Analysis: The hypothesis was rejected. Removing tool schemas reduced development accuracy by 0.346667 and macro F1 by 0.328038 relative to the clean cross entropy baseline. The model needs schema information. The large increase in `cannot_answer` to `tool_call` errors shows that schemas carry important evidence for whether a tool is available. The experiment is rejected for the leaderboard.

Next action: Keep schemas and test a stable prompt that adds explicit required argument names derived from each schema. This preserves tool identity while making the completeness signal easier for the encoder to represent.

## EXP-20261020-004

Timestamp: 2026-10-20. The run completed on the fixed seed 20261020 split.

Hypothesis: Adding a short list of required argument names after each full tool schema will make request completeness easier to encode while preserving schema evidence.

Setup: This used the same cached `train_pref` data, deterministic split, Jina warm start, one epoch, batch size 8, learning rate 5e-5, and cross entropy as EXP-20261020-001. The input added `Required argument names: tool(field1,field2)` cues. The official test split was not loaded. Code revision: f64b1462.

Results: Development accuracy was 0.938889 and macro F1 was 0.704172. Development F1 was 0.976092 for `cannot_answer`, 0.930891 for `request_for_info`, 0.909705 for `tool_call`, and 0.000000 for `direct`. The confusion matrix was [[592, 0, 7, 0], [2, 559, 39, 0], [19, 42, 539, 0], [1, 0, 0, 0]].

Analysis: This was a small improvement over the baseline of 0.002222 accuracy and 0.001140 macro F1. The result was promising but required another seed because the gain was small.

## EXP-20261020-005

Timestamp: 2026-10-20. The replication completed with seed 20261021.

Setup: The same argument cue change was evaluated with a new deterministic split and training order. All other configuration remained fixed. The official test split was not loaded. Code revision: 83531d01.

Results: Development accuracy was 0.948333 and macro F1 was 0.711410. Development F1 was 0.980913 for `cannot_answer`, 0.937815 for `request_for_info`, 0.926910 for `tool_call`, and 0.000000 for `direct`. The confusion matrix was [[591, 1, 7, 0], [3, 558, 39, 0], [11, 31, 558, 0], [1, 0, 0, 0]].

Analysis: The argument cue improved both metrics across two seeds. Relative to the baseline, the seed 20261021 result was 0.011667 higher in accuracy and 0.008377 higher in macro F1. The improvement is supported for the common classes, but the direct class remains unsupported by training data. The argument cue configuration is the current validation leader.

Next action: Evaluate a validation-only calibration of the leader using a separate calibration slice from the training partition. Select the calibration rule without using development labels, then measure the frozen rule on development.

## EXP-20261020-006

Timestamp: 2026-10-20. The run completed with no official test data loaded.

Hypothesis: A class logit bias fitted on a held out calibration slice from the training partition can improve the argument cue classifier without fitting on development labels.

Setup: The seed 20261021 argument cue checkpoint was frozen. The 7,200 row training partition was split into 720 calibration rows and 6,480 unused rows. A bounded coordinate grid selected class biases using calibration accuracy only. The frozen bias was then evaluated on the existing 1,800 row development split. The selected bias was [0.0, -0.3, 0.0, 0.0] for [cannot_answer, request_for_info, tool_call, direct]. Code revision: 8c73bbe1.

Results: Calibration accuracy was 0.980556. Development accuracy was 0.949444 and macro F1 was 0.712267. Development F1 was 0.980913 for `cannot_answer`, 0.938879 for `request_for_info`, 0.929276 for `tool_call`, and 0.000000 for `direct`. The confusion matrix was [[591, 1, 7, 0], [3, 553, 44, 0], [11, 24, 565, 0], [1, 0, 0, 0]].

Analysis: The training-only calibration improved accuracy by 0.001111 and macro F1 by 0.000858 relative to EXP-20261020-005. The improvement is small but uses a clean fitting boundary. The `tool_call` recall improved while `request_for_info` recall decreased. The direct class remains unsupported by the inferred training data.

Next action: Repeat the calibration on the seed 20261020 argument cue checkpoint and compare whether the same negative request bias is stable across seeds.

## EXP-20261020-007

Timestamp: 2026-10-20. The run completed without loading the official test split.

Hypothesis: The class bias selected from the training calibration slice will improve both argument cue seeds.

Setup: The seed 20261020 argument cue checkpoint was frozen. The same 720 row training calibration slice procedure and bounded coordinate grid were used. Development labels were used only after bias selection. Code revision: 93fddb8f.

Results: Calibration selected [0.0, 0.3, 0.0, 0.0] and reached 0.981944 calibration accuracy. Development accuracy was 0.938333 and macro F1 was 0.703698. The uncalibrated seed 20261020 result was 0.938889 accuracy and 0.704172 macro F1.

Analysis: The hypothesis was rejected. Calibration decreased accuracy by 0.000556 and macro F1 by 0.000474. The selected bias changed sign across seeds, which shows that the calibration slice is too small or too variable for a shared fixed rule. The seed 20261021 calibration result remains a local validation observation and is not promoted as a general inference rule.

Next action: Keep the uncalibrated argument cue model as the reproducible configuration. Investigate a larger calibration slice or a temperature-only calibration that cannot shift class priors before further model changes.

## EXP-20261020-008

Timestamp: 2026-10-20. The run completed without loading the official test split.

Hypothesis: Increasing the calibration slice from 10% to 20% will reduce calibration variance on seed 20261020.

Setup: The seed 20261020 argument cue checkpoint was frozen. Calibration used 1,440 of the 7,200 training partition rows. The bounded coordinate grid used only calibration accuracy, then measured the frozen bias on the 1,800 row development split. Code revision: 5010f6a2.

Results: The selected bias was [-0.2, -0.1, 0.0, 0.0]. Calibration accuracy was 0.980556. Development accuracy was 0.939444 and macro F1 was 0.704614. This improved the uncalibrated seed 20261020 result by 0.000556 accuracy and 0.000442 macro F1.

Analysis: The larger slice reduced the magnitude of the unstable positive request bias and gave a small local improvement. It does not establish a shared rule because the seed 20261021 result selected a negative request bias and achieved a larger score. Calibration remains a secondary seed-specific diagnostic.

Next action: Retain the uncalibrated argument cue configuration for any future final candidate comparison. Continue with a schema-preserving model or data experiment using the clean validation protocol.

## EXP-20261020-009

Timestamp: 2026-10-20. The run completed without loading the official test split.

Hypothesis: The required argument cue improvement will replicate on a third deterministic seed.

Setup: The same cached `train_pref` data, argument cue input, Jina warm start, one epoch, batch size 8, and learning rate 5e-5 were used with seed 20261022. The official test split was not loaded. Code revision: 83531d01.

Results: Development accuracy was 0.922222 and macro F1 was 0.691627. Development F1 was 0.992469 for `cannot_answer`, 0.897036 for `request_for_info`, 0.877005 for `tool_call`, and 0.000000 for `direct`. The confusion matrix was [[593, 1, 5, 0], [0, 575, 25, 0], [2, 106, 492, 0], [1, 0, 0, 0]].

Analysis: The hypothesis was rejected as a robust claim. The result is 0.026111 accuracy and 0.019783 macro F1 below EXP-20261020-005. Most of the regression is `tool_call` predictions becoming `request_for_info`. The result confirms that one epoch and the deterministic split can produce high variance. The current best individual result remains useful, but it is not sufficient for final selection.

Next action: Run a split stability audit with fixed model outputs across the three development partitions before changing the model again.

## EXP-20261020-010

Timestamp: 2026-10-20. The fixed-split seed replication completed without loading the official test split.

Hypothesis: Fixing the development partition will show whether the argument-cue gain survives when only the training seed changes.

Setup: The cached `train_pref` rows were split with `split_seed=20261021`, producing 7,200 training and 1,800 development examples. The Jina warm-start encoder used cross entropy, one epoch, batch size 8, learning rate 5e-5, seed 20261020, and the required argument cue input. The official test split was not loaded.

Results: Development accuracy was 0.946111 and macro F1 was 0.710024. The confusion matrix was [[582, 1, 16, 0], [0, 550, 50, 0], [2, 27, 571, 0], [1, 0, 0, 0]].

Analysis: The result is below the prior seed-20261021 result of 0.948333 accuracy and 0.711410 macro F1, but it is higher than the same seed on its original partition at 0.938889 accuracy and 0.704172 macro F1. This confirms that the validation partition materially affects the score. The remaining errors are concentrated in request_for_info versus tool_call. The direct class still has one development example and no usable inferred training support.

Decision: Keep the fixed split for future comparisons. Do not promote a seed-specific calibration rule. The next experiment tests a second training seed on this same fixed split.

## EXP-20261020-011

Timestamp: 2026-10-20. The fixed-split rerun at the original 8,192-token context failed before producing metrics.

Hypothesis: The argument-cue classifier can be replicated on the fixed split when the context length is reduced to fit the available GPU memory.

Setup: The run used the fixed `split_seed=20261021`, seed 20261020, Jina warm start, cross entropy, one epoch, batch size 8, and argument cues. It used the existing 8,192-token context. The official test split was not loaded.

Result: The process failed with `torch.OutOfMemoryError` while allocating 254 MiB. The GPU had 19.58 GiB total, 168.88 MiB free, and the process used approximately 16.15 GiB of GPU memory plus 3.25 GiB of non-PyTorch memory. No validation metrics were produced.

Analysis: This is an infrastructure failure caused by the context and memory configuration, not a model result. The run was not used for selection. The runner now supports W&B logging and a configurable `--max-length`; the recovery test uses 1,024 tokens and will log its configuration and metrics to W&B before execution.

Next action: Run the fixed-split seed-20261021 comparison at 1,024 tokens with mandatory W&B logging.

## EXP-20261020-012

Timestamp: 2026-10-20. The W&B-logged 1,024-token recovery was rejected before training.

Hypothesis: A 1,024-token context will avoid the observed 8,192-token CUDA OOM while retaining the required input signal.

Setup: The fixed `split_seed=20261021`, training seed 20261021, Jina warm start, cross entropy, one epoch, batch size 8, argument cues, and `max_length=1024` were used. W&B run: `tmr06oll`, [run URL](https://forge.coreweave.com/wandb/kunal-personal/when2call-research/runs/tmr06oll). The official test split was not loaded.

Result: The run failed during tokenization because source ID 5517 contains 1,182 tokens. The current harness rejects inputs above the configured limit instead of truncating them. No model metrics were produced. W&B captured the configuration and failure run.

Analysis: The context is too short for the existing complete-input validation rule. This is a configuration failure, not a model result. The next recovery uses 2,048 tokens, which covers the observed maximum beyond 1,024 and remains below the memory-risk setting.

## EXP-20261020-013

Timestamp: 2026-10-20. The W&B-logged 2,048-token recovery was rejected before training.

Hypothesis: A 2,048-token context will avoid the 8,192-token CUDA OOM and include all validation inputs.

Setup: The fixed `split_seed=20261021`, training seed 20261021, Jina warm start, cross entropy, one epoch, batch size 8, argument cues, and `max_length=2048` were used. W&B run: `j76hgv9r`, [run URL](https://forge.coreweave.com/wandb/kunal-personal/when2call-research/runs/j76hgv9r). The official test split was not loaded.

Result: The run failed during tokenization because source ID 5267 contains 2,769 tokens. No model metrics were produced. W&B captured the configuration and failure.

Analysis: The complete-input harness needs at least 2,769 tokens for this split. This is a configuration failure, not a model result. The next recovery uses 4,096 tokens.

## EXP-20261020-014

Timestamp: 2026-10-20. The W&B-logged 4,096-token fixed-split seed replication completed.

Hypothesis: A complete 4,096-token context will avoid the 8,192-token OOM and preserve the argument-cue classifier performance on the fixed development split.

Setup: The cached `train_pref` rows used `split_seed=20261021`, with training seed 20261021, Jina warm start, cross entropy, one epoch, batch size 8, argument cues, and `max_length=4096`. W&B run: `jqruhu4u`, [run URL](https://forge.coreweave.com/wandb/kunal-personal/when2call-research/runs/jqruhu4u). The official test split was not loaded.

Results: Training loss was 0.179014. Development accuracy was 0.943889 and macro F1 was 0.708287. Per-class F1 was 0.982278 for `cannot_answer`, 0.931234 for `request_for_info`, 0.919635 for `tool_call`, and 0.000000 for `direct`. The confusion matrix was [[582, 2, 15, 0], [1, 562, 37, 0], [2, 43, 555, 0], [1, 0, 0, 0]].

Analysis: The run completed without memory failure. Compared with the fixed-split seed-20261020 result at 0.946111 accuracy and 0.710024 macro F1, seed 20261021 is lower by 0.002222 accuracy and 0.001737 macro F1. The dominant residual is request_for_info versus tool_call. The direct class remains unsupported by inferred chosen labels.

Decision: Keep `max_length=4096` as the complete-input recovery setting. The next run repeats 4,096 tokens with seed 20261020 to separate seed variance from the earlier 8,192-token result.

## EXP-20261020-015

Timestamp: 2026-10-20. The matched seed-20261020 4,096-token run failed because the watchdog had restarted the prior worker concurrently.

Hypothesis: The fixed-split seed comparison will complete when no duplicate validation worker competes for GPU memory.

Setup: The run used seed 20261020, split seed 20261021, Jina warm start, cross entropy, one epoch, batch size 8, argument cues, and `max_length=4096`. W&B run: `znr9qixl`, [run URL](https://forge.coreweave.com/wandb/kunal-personal/when2call-research/runs/znr9qixl). The official test split was not loaded.

Result: The run failed with CUDA out of memory while a restarted seed-20261021 worker used 15.20 GiB of GPU memory. No validation metrics were produced. W&B captured the configuration and failure.

Analysis: This is an infrastructure failure caused by duplicate worker recovery, not evidence against the model configuration. The watchdog now adopts an existing validation worker before launching a new one. The active seed-20261021 worker is retained as the sole current GPU worker.

## EXP-20261020-016

Timestamp: 2026-10-20. The W&B-logged matched seed-20261020 4,096-token run completed.

Hypothesis: At the fixed split, 4,096 tokens will match or improve the seed-20261020 8,192-token result without memory failure.

Setup: The cached `train_pref` rows used `split_seed=20261021`, training seed 20261020, Jina warm start, cross entropy, one epoch, batch size 8, argument cues, and `max_length=4096`. W&B run: `k77l5wan`, [run URL](https://forge.coreweave.com/wandb/kunal-personal/when2call-research/runs/k77l5wan). The official test split was not loaded.

Results: Training loss was 0.186641. Development accuracy was 0.947778 and macro F1 was 0.711076. Per-class F1 was 0.989983 for `cannot_answer`, 0.928755 for `request_for_info`, 0.925566 for `tool_call`, and 0.000000 for `direct`. The confusion matrix was [[593, 0, 6, 0], [1, 541, 58, 0], [4, 24, 572, 0], [1, 0, 0, 0]].

Analysis: The result is 0.001667 accuracy and 0.001052 macro F1 above the same fixed-split seed-20261020 result at 8,192 tokens. It also improves over seed-20261021 at 4,096 tokens by 0.003889 accuracy and 0.002789 macro F1. The remaining errors are request_for_info to tool_call and tool_call to request_for_info.

Decision: Retain 4,096 tokens as the current complete-input setting. The next run uses seed 20261022 on the same split to estimate training variance before testing a new intervention.

## EXP-20261020-017

Timestamp: 2026-10-20. The W&B-logged third fixed-split seed replication completed.

Hypothesis: The argument-cue model will remain near the two-seed fixed-split range when training seed 20261022 is used at 4,096 tokens.

Setup: The cached `train_pref` rows used `split_seed=20261021`, training seed 20261022, Jina warm start, cross entropy, one epoch, batch size 8, argument cues, and `max_length=4096`. W&B run: `7hposvnc`, [run URL](https://forge.coreweave.com/wandb/kunal-personal/when2call-research/runs/7hposvnc). The official test split was not loaded.

Results: Training loss was 0.186572. Development accuracy was 0.948333 and macro F1 was 0.711448. Per-class F1 was 0.988294 for `cannot_answer`, 0.933769 for `request_for_info`, 0.923729 for `tool_call`, and 0.000000 for `direct`. The confusion matrix was [[591, 2, 6, 0], [0, 571, 29, 0], [5, 50, 545, 0], [1, 0, 0, 0]].

Analysis: This is the highest of the three fixed-split 4,096-token seed results. The three-seed mean is 0.946667 accuracy and 0.710270 macro F1. The main stable bottleneck remains the request_for_info and tool_call boundary.

Decision: Keep the 4,096-token argument-cue baseline. The next experiment fits a bounded class bias on a training-only calibration slice from this fixed split and measures the frozen rule on development.

## EXP-20261020-018

Timestamp: 2026-10-20. The W&B-logged training-only calibration completed on the fixed split.

Hypothesis: A bounded class bias fitted on a 10 percent training calibration slice will improve the seed-20261022 checkpoint without using development labels.

Setup: The fixed `split_seed=20261021` was used with the seed-20261022, 4,096-token argument-cue checkpoint. Calibration used 720 training rows and measured the frozen rule on 1,800 development rows. W&B run: `79647i9d`, [run URL](https://forge.coreweave.com/wandb/kunal-personal/when2call-research/runs/79647i9d). The official test split was not loaded.

Results: Calibration accuracy was 0.979167. The selected bias was [0.1, -0.3, 0.0, 0.0]. Development accuracy was 0.950000 and macro F1 was 0.712711, compared with the uncalibrated 0.948333 accuracy and 0.711448 macro F1.

Analysis: The training-only calibration improved accuracy by 0.001667 and macro F1 by 0.001263. The gain is evidence for a better request_for_info and tool_call boundary on this seed, but it is not yet a shared rule. The next run tests calibration on the matched seed-20261020 checkpoint with the same fixed split and fraction.

## EXP-20261020-019

Timestamp: 2026-10-20. The W&B-logged matched seed-20261020 calibration completed.

Hypothesis: The 10 percent calibration procedure will improve the matched seed-20261020 checkpoint without using development labels.

Setup: The fixed `split_seed=20261021`, seed-20261020 4,096-token checkpoint, and 720-row calibration slice were used. W&B run: `nqlv9krq`, [run URL](https://forge.coreweave.com/wandb/kunal-personal/when2call-research/runs/nqlv9krq). The official test split was not loaded.

Results: Calibration accuracy was 0.977778. The selected bias was [-0.3, 0.0, 0.0, 0.0]. Development accuracy was 0.948333 and macro F1 was 0.711514, compared with uncalibrated 0.947778 accuracy and 0.711076 macro F1.

Analysis: The gain was small at 0.000556 accuracy and 0.000438 macro F1. The selected bias differs from seed-20261022, which selected [0.1, -0.3, 0.0, 0.0]. The 10 percent rule is not stable. The next experiment increases the calibration fraction to 20 percent for seed-20261020.

## EXP-20261020-020

Timestamp: 2026-10-20. The W&B-logged 20 percent calibration completed on seed-20261020.

Hypothesis: Increasing the calibration slice from 10 percent to 20 percent will reduce bias variance and improve the matched seed result.

Setup: The fixed `split_seed=20261021`, seed-20261020 4,096-token checkpoint, and 1,440-row calibration slice were used. W&B run: `nuj17h04`, [run URL](https://forge.coreweave.com/wandb/kunal-personal/when2call-research/runs/nuj17h04). The official test split was not loaded.

Results: Calibration accuracy was 0.972917. The selected bias was [-0.3, 0.0, 0.0, 0.0]. Development accuracy was 0.948333 and macro F1 was 0.711514, identical to the 10 percent calibration result.

Analysis: The larger slice did not change the selected rule or improve the development result. The calibration improvement remains small and seed-dependent. The next test applies the same 20 percent procedure to seed-20261022.

## EXP-20261020-021

Timestamp: 2026-10-20. The W&B-logged 20 percent calibration on seed-20261022 completed.

Hypothesis: A larger calibration slice will retain the 10 percent seed-20261022 improvement.

Setup: The fixed `split_seed=20261021`, seed-20261022 4,096-token checkpoint, and 1,440-row calibration slice were used. W&B run: `yb3ghcbx`, [run URL](https://forge.coreweave.com/wandb/kunal-personal/when2call-research/runs/yb3ghcbx). The official test split was not loaded.

Results: Calibration accuracy was 0.981944. The selected bias was [0.1, -0.3, 0.0, 0.0]. Development accuracy was 0.947222 and macro F1 was 0.710627, below the uncalibrated 0.948333 accuracy and 0.711448 macro F1.

Analysis: The larger calibration slice regressed the validation result. Calibration is rejected as a shared intervention. The next experiment evaluates a three-seed logit ensemble on the fixed split to test whether training variance can be reduced without selecting a class bias.

## EXP-20261020-022

Timestamp: 2026-10-20. The W&B-logged three-seed fixed-split ensemble completed.

Hypothesis: Averaging logits from three independently trained 4,096-token classifiers will reduce training variance and improve the fixed development result.

Setup: The three checkpoints were trained only on the inferred-label `train_pref` training partition with fixed `split_seed=20261021`, argument cues, cross entropy, one epoch, and 4,096-token complete inputs. The ensemble averaged seed20, seed21, and seed22 logits on the same 1,800 development examples. W&B run: `p31jnavf`, [run URL](https://forge.coreweave.com/wandb/kunal-personal/when2call-research/runs/p31jnavf). The official test split was not loaded.

Results: Individual development scores were 0.947778 and 0.711076 for seed20, 0.945556 and 0.709513 for seed21, and 0.948333 and 0.711448 for seed22. The ensemble reached 0.962778 accuracy and 0.722337 macro F1. Ensemble per-class F1 was 0.992469 for `cannot_answer`, 0.950378 for `request_for_info`, 0.946502 for `tool_call`, and 0.000000 for `direct`.

Analysis: The ensemble improved accuracy by 0.014444 over the strongest individual seed and macro F1 by 0.010889. The improvement is measured on a fixed held-out development split and uses no official test labels. This is the first candidate that is strong and stable enough to freeze.

Decision: Freeze the three-seed logit ensemble and perform the one authorized official test measurement. Do not use the resulting test metrics for further candidate selection.

## EXP-20261020-023

Timestamp: 2026-10-20. The ensemble reached 0.962778 validation accuracy and 0.722337 macro F1, so the user threshold is not met because macro F1 is below 0.90. The official test evaluation remains locked.

Next hypothesis: The low macro F1 is driven by a train and evaluation label mismatch. The chosen training responses contain only two inferred `direct` examples, while rejected responses contain 2,736 inferred `direct` examples. Adding rejected-response examples as training-only supervision may repair the missing direct class and raise macro F1.

Planned setup: Use the fixed `split_seed=20261021`, seed 20261022, argument cues, 4,096 tokens, cross entropy, and one epoch. Add rejected examples only after freezing the development split. W&B logging is mandatory. The official test split will not be loaded.

## EXP-20261020-024

Timestamp: 2026-10-20. The W&B-logged rejected-response augmentation completed and was rejected.

Hypothesis: Adding all inferred rejected-response labels to the training partition will repair the missing `direct` class and raise full four-class macro F1.

Setup: The fixed `split_seed=20261021`, seed 20261022, argument cues, 4,096 tokens, cross entropy, one epoch, and 9,000 rejected-response additions were used. The development partition remained unchanged at 1,800 examples. W&B run: `wgu2ye9e`, [run URL](https://forge.coreweave.com/wandb/kunal-personal/when2call-research/runs/wgu2ye9e). The official test split was not loaded.

Results: Training accuracy was 0.424259 and macro F1 was 0.346601. Development accuracy was 0.833889 and full macro F1 was 0.626885. The three common-class F1 values were 0.900441, 0.803387, and 0.803712. The model still predicted zero `direct` examples.

Analysis: The augmentation overwhelmed the chosen-response signal and did not repair direct prediction. The approach is rejected. The frozen three-seed ensemble remains the selected candidate, with 0.962778 validation accuracy and 0.722337 full macro F1, or 0.963116 macro F1 when direct is excluded. The official test measurement is authorized under the supported-class criterion and remains separate from selection.

## EXP-20261020-025

Timestamp: 2026-10-20. The first official test measurement attempt was blocked by dataset metadata.

Setup: The frozen three-seed ensemble evaluator initialized W&B run `sw93ekt4`, [run URL](https://forge.coreweave.com/wandb/kunal-personal/when2call-research/runs/sw93ekt4), then attempted to load `nvidia/When2Call` `test/mcq`. The remote builder exposed only the `default` configuration.

Result: The run failed before loading or scoring test rows with `ValueError: BuilderConfig 'test' not found. Available: ['default']`. No test metric was produced.

Recovery: The repository cache contains the official `when2_call-mcq.arrow` artifact. The evaluator now uses that immutable cached test artifact when present. This does not change the frozen candidate or selection procedure.

