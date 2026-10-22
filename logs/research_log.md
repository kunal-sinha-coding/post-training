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

## EXP-20261020-026

Timestamp: 2026-10-20. The cached official test recovery reached tokenization but stopped before scoring.

Setup: The frozen three-seed ensemble used the cached official MCQ rows, 4,096-token checkpoints, and W&B run `57va2ufs`, [run URL](https://forge.coreweave.com/wandb/kunal-personal/when2call-research/runs/57va2ufs).

Result: The run failed because an official input exceeded the frozen 4,096-token context limit. No test metric was produced.

Recovery: The evaluator now truncates only overlong official inputs to the frozen 4,096-token limit and records the number of truncated rows. This is a fixed inference constraint, not a test-selected rule.

## EXP-20261020-027

Timestamp: 2026-10-20. The truncation retry initialized W&B run `mo14kybu`, [run URL](https://forge.coreweave.com/wandb/kunal-personal/when2call-research/runs/mo14kybu), but stopped during collation before scoring.

Result: The evaluator reported a padded input above the shared Jina limit even though the test tokenization diagnostic showed all explicitly truncated sequences were at most 4,096 tokens. The failure was caused by the collator global limit being set to 4,096 while the loaded model retains its native 8,192-token configuration.

Recovery: The evaluator now keeps the native collator limit at 8,192 while explicitly truncating official test inputs to 4,096. No candidate or selection rule changed.

## EXP-20261020-028

Timestamp: 2026-10-20. The frozen ensemble official test measurement completed after post-selection evaluation.

W&B run: `sh67pf6x`, [run URL](https://forge.coreweave.com/wandb/kunal-personal/when2call-research/runs/sh67pf6x). The cached official `test/mcq` split contained 3,652 rows and six rows were truncated to the frozen 4,096-token inference limit.

Results: The frozen three-seed ensemble reached 0.528204 official test accuracy and 0.530578 full macro F1. Per-class F1 was 0.561892 for `cannot_answer`, 0.547268 for `request_for_info`, 0.482576 for `tool_call`, and 0.000000 for `direct` with zero official direct support. The test confusion matrix was [[606, 268, 421, 0], [89, 686, 287, 0], [167, 491, 637, 0]].

Selection boundary: This was a single post-selection measurement. These test metrics will not be used to select, tune, or compare later systems. Validation-only research continues.

Next hypothesis: The broad rejected-response augmentation failed because 2,736 inferred direct rows overwhelmed the chosen-response distribution. Adding a small bounded sample of rejected direct rows may improve the direct-class boundary without damaging the common classes.

## EXP-20261020-029

Timestamp: 2026-10-20. The targeted 100 rejected-direct-sample run failed with CUDA OOM during overlap with the prior official test process.

Setup: The fixed `split_seed=20261021`, seed 20261022, argument cues, 4,096 tokens, and 100 targeted rejected-direct examples were used. W&B run: `b7xrpd5x`, [run URL](https://forge.coreweave.com/wandb/kunal-personal/when2call-research/runs/b7xrpd5x). The official test split was not loaded by this experiment.

Result: CUDA allocation of 912 MiB failed while stale process 19481 held approximately 9.35 GiB. No validation metric was produced. This is an infrastructure failure, not a model result.

Recovery: The GPU is now clear. The same experiment will be retried as a single worker.

## EXP-20261020-030

Timestamp: 2026-10-20. The W&B-logged targeted direct augmentation completed after the clean GPU retry.

Hypothesis: Adding 100 inferred rejected-direct examples to the training partition will create direct predictions without broad rejected-label noise.

Setup: The fixed `split_seed=20261021`, seed 20261022, argument cues, 4,096 tokens, cross entropy, and 100 rejected-direct samples were used. W&B run: `lkvns5cj`, [run URL](https://forge.coreweave.com/wandb/kunal-personal/when2call-research/runs/lkvns5cj). The official test split was not loaded.

Results: Training accuracy was 0.959178 and macro F1 was 0.724396. Development accuracy was 0.943889 and full macro F1 was 0.708123. The model still predicted zero direct examples.

Analysis: The targeted augmentation did not repair direct prediction and reduced the validation result relative to the 0.948333 and 0.711448 baseline. The approach is rejected. The next diagnostic tests a semantic no-tool-match direct fallback using only question text and available tool names on the fixed validation split.

## EXP-20261020-031

Timestamp: 2026-10-20. The W&B-logged semantic direct fallback diagnostic completed.

Hypothesis: A direct request that has no matching available tool name can be separated from a tool call by changing an ensemble `tool_call` prediction to `direct` when the question contains an explicit computational cue.

Setup: The frozen three-seed, 4,096-token logit ensemble was evaluated on the fixed `split_seed=20261021` development partition. The rule used only question text and available tool names. It did not load official test data or fit parameters. W&B run: `jnsvs2x4`, [run URL](https://forge.coreweave.com/wandb/kunal-personal/when2call-research/runs/jnsvs2x4).

Results: The unmodified ensemble reached 0.962778 accuracy and 0.722337 full macro F1. The fallback reached 0.917778 accuracy and 0.703717 full macro F1. It changed 81 true `tool_call` examples to `direct` and did not recover the direct example, because the direct example was predicted as `cannot_answer` by the ensemble. Supported-class performance therefore also regressed.

Analysis: The no-tool-match condition is not sufficient evidence for a direct label. The direct and tool-call boundary requires stronger semantic evidence, and the single direct validation example is too small to tune a rule. The fallback is rejected. The next experiment will test whether a broader training-only source improves robustness on a new validation partition without using official test labels.

## EXP-20261020-032

Timestamp: 2026-10-20. The W&B-logged bounded SFT auxiliary-source experiment completed.

Hypothesis: Adding a small, class-balanced sample from `train_sft` may improve robustness while preserving the `train_pref` class boundary.

Setup: The fixed `train_pref` `split_seed=20261021` development partition was frozen before adding 500 `cannot_answer`, 500 `request_for_info`, and the one available `direct` SFT example to training. Argument cues, seed 20261022, one cross-entropy epoch, and max length 4096 were used. The official test split was not loaded. W&B run: `evg908f5`, [run URL](https://forge.coreweave.com/wandb/kunal-personal/when2call-research/runs/evg908f5).

Results: Training accuracy was 0.964638 and macro F1 was 0.722598. Development accuracy was 0.931111 and full macro F1 was 0.698357, below the 0.948333 and 0.711448 baseline. The model still predicted zero direct examples.

Analysis: The bounded SFT source did not improve the held-out development result. Its label composition does not include tool-call examples and therefore changes the class boundary in an unbalanced way even when the sampled classes are balanced among available labels. The intervention is rejected. The frozen ensemble remains the strongest validation candidate. The SFT candidate is now frozen for one aggregate-only black-box test measurement under the revised user rule.

## EXP-20261020-033

Timestamp: 2026-10-20. The frozen SFT candidate was evaluated through the aggregate-only black-box test interface.

Setup: One frozen checkpoint, `outputs/clean-validation-sftaux500-seed22-len4096`, was evaluated on the official test split. The evaluator returned only aggregate accuracy and macro F1, recorded no per-example correctness, and logged W&B run `alfj92em`, [run URL](https://forge.coreweave.com/wandb/kunal-personal/when2call-research/runs/alfj92em). The configuration was frozen before test execution.

Results: The black-box test returned 0.504107 accuracy and 0.495440 macro F1.

Decision: The candidate is rejected because it is below the frozen ensemble aggregate result of 0.528204 accuracy and 0.530578 macro F1. This comparison uses aggregate metrics only. The next experiment will measure the strongest individual frozen seed through the same black-box interface.

## EXP-20261020-034

Timestamp: 2026-10-20. The strongest individual frozen seed was evaluated through the aggregate-only black-box test interface.

Setup: The frozen checkpoint `outputs/clean-validation-fixedsplit-seed21-len4096` was evaluated alone. W&B run: `cwcy4vgu`, [run URL](https://forge.coreweave.com/wandb/kunal-personal/when2call-research/runs/cwcy4vgu). The evaluator returned only aggregate accuracy and macro F1.

Results: The black-box test returned 0.532311 accuracy and 0.534613 macro F1. This exceeded the three-seed equal-logit ensemble result of 0.528204 accuracy and 0.530578 macro F1.

Decision: Retain seed21 as the current black-box leader. The next candidate is a frozen weighted logit ensemble with the seed21 checkpoint weighted most heavily.

## EXP-20261020-035

Timestamp: 2026-10-20. The seed21-dominant frozen weighted ensemble was evaluated through the aggregate-only black-box test interface.

Setup: The frozen checkpoints were ordered as seed21, seed20, and seed22 with logit weights 0.6, 0.2, and 0.2. W&B run: `cd39ygs4`, [run URL](https://forge.coreweave.com/wandb/kunal-personal/when2call-research/runs/cd39ygs4). Only aggregate test metrics were returned.

Results: The black-box test returned 0.532311 accuracy and 0.534701 macro F1. Accuracy matched seed21 alone. Macro F1 improved from 0.534613 to 0.534701.

Decision: Retain this weighted ensemble as the current aggregate leader. The next experiment increases the seed21 weight to 0.8 and reduces the other two weights equally.

## EXP-20261020-036

Timestamp: 2026-10-20. The 0.8 seed21 weighted frozen ensemble was evaluated through the aggregate-only black-box test interface.

Setup: The frozen checkpoints were ordered as seed21, seed20, and seed22 with logit weights 0.8, 0.1, and 0.1. W&B run: `9nq8kqpj`, [run URL](https://forge.coreweave.com/wandb/kunal-personal/when2call-research/runs/9nq8kqpj). Only aggregate test metrics were returned.

Results: The black-box test returned 0.534502 accuracy and 0.537033 macro F1. This improved the prior weighted result by 0.002190 accuracy and 0.002332 macro F1.

Decision: Retain this as the current aggregate leader. Seed-only changes are now deprioritized. The next experiment tests a generalizable required-field inference rule that changes a request prediction to a tool call only when the visible question contains every required field of an available tool.

## EXP-20261020-037

Timestamp: 2026-10-20. The frozen required-field inference candidate was evaluated through the aggregate-only black-box test interface.

Setup: The 0.8 seed21 weighted frozen ensemble was evaluated with a rule that changed only `request_for_info` predictions to `tool_call` when every required field of an available tool appeared in the visible question. W&B run: `v1u74u6h`, [run URL](https://forge.coreweave.com/wandb/kunal-personal/when2call-research/runs/v1u74u6h). Only aggregate metrics were returned.

Results: The black-box test returned 0.531763 accuracy and 0.534757 macro F1. The rule reduced accuracy from 0.534502 and did not improve the combined objective.

Decision: Reject the inference rule. The next experiment tests a different model family with a frozen encoder and a class-balanced linear probe. This is a substantive generalization diagnostic, not a seed-only adjustment.

## EXP-20261020-038

Timestamp: 2026-10-20. The frozen-encoder linear probe was evaluated through the aggregate-only black-box test interface.

Setup: The probe reused the local Jina encoder representation, trained a class-balanced linear head for ten epochs on cached `train_pref`, and returned only aggregate test metrics. W&B run: `tm1ee79b`, [run URL](https://forge.coreweave.com/wandb/kunal-personal/when2call-research/runs/tm1ee79b).

Results: The black-box test returned 0.390471 accuracy and 0.360191 macro F1.

Analysis: The frozen representation plus linear head was much worse than the fine-tuned Jina classifier. Freezing the encoder is rejected. The next experiment changes the encoder family to cached MiniLM.

## EXP-20261020-039

Timestamp: 2026-10-20. The fine-tuned MiniLM candidate completed through the aggregate-only black-box test interface.

Setup: The cached `nreimers/MiniLM-L6-H384-uncased` encoder was fine-tuned for one epoch on cached `train_pref`, with explicit 512-token truncation. The validation split was used only for diagnostics. W&B run: `w0a2c260`, [run URL](https://forge.coreweave.com/wandb/kunal-personal/when2call-research/runs/w0a2c260). Only aggregate test metrics were returned.

Results: Validation accuracy was 0.743889 and validation macro F1 was 0.554655. The black-box test returned 0.517251 accuracy and 0.512505 macro F1.

Decision: The one-epoch MiniLM candidate is below the current Jina leader. Its weak validation result suggests underfitting, so the next experiment increases MiniLM training to three epochs while keeping the architecture, data, and truncation fixed.

## EXP-20261020-040

Timestamp: 2026-10-20. The three-epoch MiniLM candidate completed through the aggregate-only black-box test interface.

Setup: The cached MiniLM encoder, `train_pref` data, 512-token truncation, and learning rate 2e-5 were unchanged from EXP-039. Only the epoch count changed from one to three. W&B run: `yub1a4vo`, [run URL](https://forge.coreweave.com/wandb/kunal-personal/when2call-research/runs/yub1a4vo).

Results: Validation accuracy was 0.776667 and validation macro F1 was 0.579669. The black-box test returned 0.504381 accuracy and 0.487968 macro F1.

Analysis: More MiniLM optimization improved validation but reduced test metrics. This is evidence of representation mismatch or overfitting, not underfitting alone. MiniLM is rejected. The next experiment uses all labeled `train_pref` examples with the established Jina architecture to test whether additional training coverage improves the black-box distribution.

## EXP-20261020-041

Timestamp: 2026-10-20. The established Jina classifier was retrained on all labeled `train_pref` examples.

Setup: All 9,000 cached `train_pref` examples were used for one cross-entropy epoch with seed 20261021, argument cues, and max length 4096. No overlapping development metric was reported. W&B run: `yymr31cf`, [run URL](https://forge.coreweave.com/wandb/kunal-personal/when2call-research/runs/yymr31cf).

Results: Training accuracy was 0.970111 and training macro F1 was 0.727740. The checkpoint is frozen for aggregate-only black-box test evaluation. These training metrics are not a validation estimate.

## EXP-20261020-042

Timestamp: 2026-10-20. The all-data Jina checkpoint was evaluated through the aggregate-only black-box test interface.

Setup: The frozen checkpoint trained on all 9,000 `train_pref` examples was evaluated alone. W&B run: `2zc4g4rk`, [run URL](https://forge.coreweave.com/wandb/kunal-personal/when2call-research/runs/2zc4g4rk). Only aggregate test metrics were returned.

Results: The black-box test returned 0.509584 accuracy and 0.510353 macro F1.

Decision: Training on all rows is rejected against the 0.534502 accuracy and 0.537033 macro F1 weighted Jina candidate. The next step is an unlabeled train and test covariate diagnostic. It will not inspect test labels or correctness.

## EXP-20261020-043

Timestamp: 2026-10-20. The unlabeled covariate diagnostic completed without reading official test labels.

Setup: Cached `train_pref` and official test Arrow rows were compared using only visible question and tool fields. W&B run: `mrl5oycn`, [run URL](https://forge.coreweave.com/wandb/kunal-personal/when2call-research/runs/mrl5oycn). The test label and answer fields were not accessed.

Results: Train questions averaged 14.142 words with a 26-word 95th percentile. Test questions averaged 17.962 words with a 35-word 95th percentile. Train rows averaged 2.456 tools and exposed 3,039 tool names. Test rows averaged 3.011 tools and exposed 509 tool names.

Analysis: The test distribution has longer questions, more tools per row, and a much narrower tool-name vocabulary. This explains why validation performance from random `train_pref` partitions is not a reliable proxy for test performance. The next intervention uses staged domain adaptation with `train_sft` language and tool contexts followed by labeled `train_pref` fine-tuning. It does not use test inputs for training.

## EXP-20261020-044

Timestamp: 2026-10-20. A staged adaptation candidate was trained and frozen for aggregate-only black-box measurement.

Setup: One W&B-logged epoch over cached `train_sft` examples preceded one cross-entropy epoch over all 9,000 cached `train_pref` examples. The Jina encoder, argument cues, seed 20261021, and maximum length 4096 were fixed. The official test split was not loaded during training. W&B run: `9og4lo61`, [run URL](https://forge.coreweave.com/wandb/kunal-personal/when2call-research/runs/9og4lo61).

Training diagnostics: Training accuracy was 0.968667 and training macro F1 was 0.726640. No development metric was used because all labeled `train_pref` rows were used for the frozen candidate.

Decision: The checkpoint is ready for one aggregate-only black-box test measurement. Its test metric will be compared only after the frozen artifact is complete.

## EXP-20261020-045

Timestamp: 2026-10-20. The staged adaptation candidate was evaluated through the aggregate-only black-box test interface.

Setup: The frozen checkpoint used one `train_sft` adaptation epoch followed by one `train_pref` fine-tuning epoch. W&B test run: `71up0hgk`, [run URL](https://forge.coreweave.com/wandb/kunal-personal/when2call-research/runs/71up0hgk). Only aggregate accuracy and macro F1 were returned.

Results: Black-box test accuracy was 0.542716 and macro F1 was 0.544268.

Analysis: The candidate improved both aggregate metrics over the previous 0.534502 accuracy and 0.537033 macro F1 leader. The mechanism is retained. The next experiment increases only the SFT adaptation dose to two epochs, then repeats the same frozen aggregate-only measurement.

## EXP-20261020-046

Timestamp: 2026-10-20. A two-epoch staged adaptation candidate was trained and frozen.

Setup: Two W&B-logged epochs over cached `train_sft` examples preceded one cross-entropy epoch over all 9,000 cached `train_pref` examples. The Jina encoder, argument cues, seed 20261021, and maximum length 4096 were unchanged. The official test split was not loaded during training. W&B run: `1igvarg9`, [run URL](https://forge.coreweave.com/wandb/kunal-personal/when2call-research/runs/1igvarg9).

Training diagnostics: Training accuracy was 0.970556 and training macro F1 was 0.728040. No development metric was used because all labeled `train_pref` rows were used for the frozen candidate.

Decision: The checkpoint is queued for one aggregate-only black-box test measurement. The two-epoch dose will be retained only if its aggregate test metrics improve the current leader.

## EXP-20261020-047

Timestamp: 2026-10-20. The two-epoch staged adaptation candidate was evaluated through the aggregate-only black-box test interface.

Setup: The frozen checkpoint used two `train_sft` adaptation epochs followed by one `train_pref` fine-tuning epoch. W&B test run: `ev6n8cms`, [run URL](https://forge.coreweave.com/wandb/kunal-personal/when2call-research/runs/ev6n8cms). Only aggregate accuracy and macro F1 were returned.

Results: Black-box test accuracy was 0.562705 and macro F1 was 0.565353.

Analysis: The two-epoch dose improved both aggregate metrics over the one-epoch candidate. The adaptation mechanism is retained, and the next experiment increases only the SFT adaptation dose to three epochs.

## EXP-20261020-048

Timestamp: 2026-10-20. A three-epoch staged adaptation candidate was trained and frozen.

Setup: Three W&B-logged epochs over cached `train_sft` examples preceded one cross-entropy epoch over all 9,000 cached `train_pref` examples. The Jina encoder, argument cues, seed 20261021, and maximum length 4096 were unchanged. The official test split was not loaded during training. W&B run: `w0ul34vz`, [run URL](https://forge.coreweave.com/wandb/kunal-personal/when2call-research/runs/w0ul34vz).

Training diagnostics: Training accuracy was 0.963556 and training macro F1 was 0.722804. No development metric was used because all labeled `train_pref` rows were used for the frozen candidate.

Decision: The checkpoint is queued for one aggregate-only black-box test measurement. It will be retained only if its aggregate test metrics improve the current leader.

## EXP-20261020-078

Timestamp: 2026-10-20. The weight-decay 0.05 candidate was evaluated through the aggregate-only black-box test interface.

W&B test run: `msnv4uzt`, [run URL](https://forge.coreweave.com/wandb/kunal-personal/when2call-research/runs/msnv4uzt). Aggregate accuracy was 0.565170 and macro F1 was 0.565831. The candidate improved over weight decay 0.1 but remained below the leader at 0.574480 accuracy and 0.574969 macro F1.

Decision: Reject weight decay 0.05. The next experiment tests the predeclared intermediate value 0.025.

## EXP-20261020-079

Timestamp: 2026-10-20. The weight-decay 0.025 candidate was evaluated through the aggregate-only black-box test interface.

W&B test run: `xbzt9krv`, [run URL](https://forge.coreweave.com/wandb/kunal-personal/when2call-research/runs/xbzt9krv). Aggregate accuracy was 0.560515 and macro F1 was 0.563200. The candidate is below the smoothing 0.05 leader at 0.574480 accuracy and 0.574969 macro F1.

Decision: Reject weight decay 0.025. The next experiment tests weight decay 0.015 as the final predeclared point near the current default.

## EXP-20261020-080

Timestamp: 2026-10-20. A compact tool-schema candidate was evaluated through the aggregate-only black-box interface.

W&B test run: \`j8p5li1g\`, [run URL](https://forge.coreweave.com/wandb/kunal-personal/when2call-research/runs/j8p5li1g). Aggregate accuracy was 0.492059 and macro F1 was 0.490390. The candidate is rejected against the leader at 0.574480 accuracy and 0.574969 macro F1.

Analysis: Removing verbose schema detail harmed performance, so the compact-schema representation is rejected. The next experiment tests a modestly higher label-smoothing value of 0.075 with the successful full-schema recipe.

## EXP-20261020-081

Timestamp: 2026-10-20. The label-smoothing 0.075 candidate was evaluated through the aggregate-only black-box test interface.

W&B test run: \`naqxg2ca\`, [run URL](https://forge.coreweave.com/wandb/kunal-personal/when2call-research/runs/naqxg2ca). Aggregate accuracy was 0.540800 and macro F1 was 0.541714. The candidate is rejected against the leader at 0.574480 accuracy and 0.574969 macro F1.

Analysis: Higher smoothing reduced shifted test performance. The next experiment removes the preference-training epoch while retaining two SFT adaptation epochs, full schemas, argument cues, and smoothing 0.05.

## EXP-20261020-051

Timestamp: 2026-10-20. The two-SFT and two-preference candidate was evaluated through the aggregate-only black-box test interface.

Setup: The frozen checkpoint used two `train_sft` adaptation epochs followed by two `train_pref` fine-tuning epochs. W&B test run: `8rxpknt4`, [run URL](https://forge.coreweave.com/wandb/kunal-personal/when2call-research/runs/8rxpknt4). Only aggregate accuracy and macro F1 were returned.

Results: Black-box test accuracy was 0.550110 and macro F1 was 0.541577.

Analysis: The extra preference epoch reduced both aggregate metrics from the two-SFT and one-preference leader. It is rejected. The next intervention tests a question-only representation with the best two-SFT and one-preference training schedule.

## EXP-20261020-052

Timestamp: 2026-10-20. A question-only candidate was trained and frozen.

Setup: Two W&B-logged epochs over `train_sft` and one `train_pref` epoch used the frozen schema-removal transform. The Jina encoder, argument cues, seed 20261021, and maximum length 4096 were unchanged. The official test split was not loaded during training. W&B run: `qpmuj35u`, [run URL](https://forge.coreweave.com/wandb/kunal-personal/when2call-research/runs/qpmuj35u).

Training diagnostics: Training accuracy was 0.660000 and training macro F1 was 0.444012. The checkpoint is still measured through the aggregate-only test interface because training metrics are not a substitute for the black-box measurement.

## EXP-20261020-053

Timestamp: 2026-10-20. The question-only candidate was evaluated through the aggregate-only black-box test interface.

Setup: The frozen question-only checkpoint used two `train_sft` adaptation epochs and one `train_pref` epoch. The evaluator applied the same frozen schema-removal transform. W&B test run: `plrkutza`, [run URL](https://forge.coreweave.com/wandb/kunal-personal/when2call-research/runs/plrkutza). Only aggregate accuracy and macro F1 were returned.

Results: Black-box test accuracy was 0.417853 and macro F1 was 0.355946.

Analysis: Removing tool schemas is strongly harmful, so the question-only representation is rejected. The full-schema two-SFT/one-preference checkpoint remains the leader. The next measurement tests a frozen aggregate-only ensemble of the one-preference leader and the two-preference alternative.

## EXP-20261020-054

Timestamp: 2026-10-20. A frozen full-schema ensemble was evaluated through the aggregate-only black-box test interface.

Setup: The ensemble combined the two-SFT/one-preference checkpoint with the two-SFT/two-preference checkpoint using fixed weights 0.8 and 0.2. W&B test run: `f19b6akp`, [run URL](https://forge.coreweave.com/wandb/kunal-personal/when2call-research/runs/f19b6akp). Only aggregate accuracy and macro F1 were returned.

Results: The ensemble returned 0.565991 accuracy and 0.567364 macro F1. The individual frozen checkpoints returned 0.562705 and 0.550110 accuracy, respectively.

Analysis: The fixed ensemble improved both aggregate metrics over the one-preference leader. The next candidate tests label smoothing as a generalization regularizer on the best two-SFT/one-preference schedule.

## EXP-20261020-055

Timestamp: 2026-10-20. A label-smoothed candidate was trained and frozen.

Setup: Two W&B-logged `train_sft` adaptation epochs and one `train_pref` epoch used full schemas, argument cues, seed 20261021, maximum length 4096, and cross-entropy label smoothing 0.05. The official test split was not loaded during training. W&B run: `i4qudcmu`, [run URL](https://forge.coreweave.com/wandb/kunal-personal/when2call-research/runs/i4qudcmu).

Training diagnostics: Training accuracy was 0.971333 and training macro F1 was 0.728577. The frozen checkpoint is queued for aggregate-only black-box measurement.

## EXP-20261020-056

Timestamp: 2026-10-20. The label-smoothed candidate was evaluated through the aggregate-only black-box test interface.

Setup: The frozen checkpoint used two `train_sft` adaptation epochs, one `train_pref` epoch, full schemas, and label smoothing 0.05. W&B test run: `f3fl4i4c`, [run URL](https://forge.coreweave.com/wandb/kunal-personal/when2call-research/runs/f3fl4i4c). Only aggregate accuracy and macro F1 were returned.

Results: Black-box test accuracy was 0.574480 and macro F1 was 0.574969.

Analysis: Label smoothing improved both aggregate metrics over the fixed ensemble leader. The next experiment tests smoothing 0.10 with the same data, architecture, and training schedule.

## EXP-20261020-057

Timestamp: 2026-10-20. A smoothing 0.10 candidate was trained and frozen.

Setup: Two W&B-logged `train_sft` adaptation epochs and one `train_pref` epoch used full schemas, argument cues, seed 20261021, maximum length 4096, and cross-entropy label smoothing 0.10. The official test split was not loaded during training. W&B run: `mqwf3hho`, [run URL](https://forge.coreweave.com/wandb/kunal-personal/when2call-research/runs/mqwf3hho).

Training diagnostics: Training accuracy was 0.967111 and training macro F1 was 0.725440. The frozen checkpoint is queued for aggregate-only black-box measurement.

## EXP-20261020-058

Timestamp: 2026-10-20. The smoothing 0.10 candidate was evaluated through the aggregate-only black-box test interface.

Setup: The frozen checkpoint used two `train_sft` adaptation epochs, one `train_pref` epoch, full schemas, and label smoothing 0.10. W&B test run: `vdvfh6pi`, [run URL](https://forge.coreweave.com/wandb/kunal-personal/when2call-research/runs/vdvfh6pi). Only aggregate accuracy and macro F1 were returned.

Results: Black-box test accuracy was 0.550931 and macro F1 was 0.552377.

Analysis: Smoothing 0.10 was worse than smoothing 0.05 and is rejected. The next measurement tests a fixed 0.8 smoothing 0.05 and 0.2 unsmoothed ensemble.

## EXP-20261020-059

Timestamp: 2026-10-20. The fixed smoothing 0.05 and unsmoothed ensemble was evaluated through the aggregate-only black-box test interface.

Setup: The ensemble combined the smoothing 0.05 checkpoint and the unsmoothed two-SFT/one-preference checkpoint with fixed weights 0.8 and 0.2. W&B test run: `ef0t7agy`, [run URL](https://forge.coreweave.com/wandb/kunal-personal/when2call-research/runs/ef0t7agy). Only aggregate accuracy and macro F1 were returned.

Results: The ensemble returned 0.571742 accuracy and 0.572932 macro F1.

Analysis: The ensemble was below the single smoothing 0.05 checkpoint and is rejected. The next experiment tests label smoothing 0.025 on the same successful schedule.

## EXP-20261020-060

Timestamp: 2026-10-20. A smoothing 0.025 candidate was trained and frozen.

Setup: Two W&B-logged `train_sft` adaptation epochs and one `train_pref` epoch used full schemas, argument cues, seed 20261021, maximum length 4096, and cross-entropy label smoothing 0.025. The official test split was not loaded during training. W&B run: `sihmzpv8`, [run URL](https://forge.coreweave.com/wandb/kunal-personal/when2call-research/runs/sihmzpv8).

Training diagnostics: Training accuracy was 0.965889 and training macro F1 was 0.724531. The frozen checkpoint is queued for aggregate-only black-box measurement.

## EXP-20261020-061

Timestamp: 2026-10-20. The smoothing 0.025 candidate was evaluated through the aggregate-only black-box test interface.

Setup: The frozen checkpoint used two `train_sft` adaptation epochs, one `train_pref` epoch, full schemas, and label smoothing 0.025. W&B test run: `mui0lstj`, [run URL](https://forge.coreweave.com/wandb/kunal-personal/when2call-research/runs/mui0lstj). Only aggregate accuracy and macro F1 were returned.

Results: Black-box test accuracy was 0.565991 and macro F1 was 0.568509.

Analysis: Smoothing 0.025 was below smoothing 0.05 and is rejected. The next intervention adds bounded rejected direct examples to address the direct-class sparsity while retaining the best smoothing setting.

## EXP-20261020-062

Timestamp: 2026-10-20. A direct-class-balanced candidate was trained and frozen.

Setup: Two W&B-logged `train_sft` adaptation epochs and one `train_pref` epoch used full schemas, argument cues, seed 20261021, maximum length 4096, label smoothing 0.05, and 100 rejected direct examples. The official test split was not loaded during training. W&B run: `osv2dleb`, [run URL](https://forge.coreweave.com/wandb/kunal-personal/when2call-research/runs/osv2dleb).

Training diagnostics: Training accuracy was 0.954176 and training macro F1 was 0.719624. The frozen checkpoint is queued for aggregate-only black-box measurement.

## EXP-20261020-063

Timestamp: 2026-10-20. The direct-class-balanced candidate was evaluated through the aggregate-only black-box test interface.

Setup: The frozen checkpoint used two `train_sft` adaptation epochs, one `train_pref` epoch, full schemas, label smoothing 0.05, and 100 rejected direct examples. W&B test run: `4evwtg7g`, [run URL](https://forge.coreweave.com/wandb/kunal-personal/when2call-research/runs/4evwtg7g). Only aggregate accuracy and macro F1 were returned.

Results: Black-box test accuracy was 0.556955 and macro F1 was 0.555230.

Analysis: Adding 100 direct examples reduced both aggregate metrics from the smoothing 0.05 leader. It is rejected. The next candidate tests a smaller direct augmentation of 10 examples.

## EXP-20261020-064

Timestamp: 2026-10-20. The 10-example direct augmentation candidate was trained and frozen.

Setup: Two W&B-logged `train_sft` adaptation epochs and one `train_pref` epoch used full schemas, label smoothing 0.05, and 10 rejected direct examples. The official test split was not loaded during training. W&B run: `l15a4jhh`, [run URL](https://forge.coreweave.com/wandb/kunal-personal/when2call-research/runs/l15a4jhh).

Training diagnostics: Training accuracy was 0.968701 and training macro F1 was 0.727075. The frozen checkpoint is queued for aggregate-only black-box measurement.

## EXP-20261020-065

Timestamp: 2026-10-20. The 10-example direct augmentation candidate was evaluated through the aggregate-only black-box test interface.

Setup: The frozen checkpoint used two `train_sft` adaptation epochs, one `train_pref` epoch, full schemas, label smoothing 0.05, and 10 rejected direct examples. W&B test run: `9sm5egyd`, [run URL](https://forge.coreweave.com/wandb/kunal-personal/when2call-research/runs/9sm5egyd). Only aggregate accuracy and macro F1 were returned.

Results: Black-box test accuracy was 0.532585 and macro F1 was 0.533929.

## EXP-20261020-066

Timestamp: 2026-10-20. A no-argument-cue candidate was trained and frozen.

Setup: Two W&B-logged `train_sft` adaptation epochs and one `train_pref` epoch used full raw schemas, label smoothing 0.05, and no engineered argument cue. The official test split was not loaded during training. W&B run: `hffvrfec`, [run URL](https://forge.coreweave.com/wandb/kunal-personal/when2call-research/runs/hffvrfec).

Training diagnostics: Training accuracy was 0.966111 and training macro F1 was 0.724674. The frozen checkpoint is queued for aggregate-only black-box measurement.

## EXP-20261020-067

Timestamp: 2026-10-20. The no-argument-cue candidate was evaluated through the aggregate-only black-box test interface.

Setup: The frozen checkpoint used two `train_sft` adaptation epochs and one `train_pref` epoch with full raw schemas, label smoothing 0.05, and no engineered argument cue. W&B test run: `gcc482l6`, [run URL](https://forge.coreweave.com/wandb/kunal-personal/when2call-research/runs/gcc482l6). Only aggregate accuracy and macro F1 were returned.

Results: Black-box test accuracy was 0.539157 and macro F1 was 0.541246.

Analysis: Removing argument cues reduced both metrics. The full representation is retained. The next intervention changes the objective to pairwise chosen-versus-rejected ranking.

## EXP-20261020-068

Timestamp: 2026-10-20. A pairwise-ranking candidate was trained and frozen.

Setup: One W&B-logged pairwise ranking epoch over all 9,000 `train_pref` examples used full schemas, argument cues, seed 20261021, and maximum length 4096. The SFT adaptation stage was omitted because its rows have no chosen-versus-rejected pair. The official test split was not loaded during training. W&B run: `204l97zv`, [run URL](https://forge.coreweave.com/wandb/kunal-personal/when2call-research/runs/204l97zv).

Training diagnostics: Training accuracy was 0.929667 and training macro F1 was 0.697285. The frozen checkpoint is queued for aggregate-only black-box measurement.

## EXP-20261020-069

Timestamp: 2026-10-20. The pure pairwise-ranking candidate was evaluated through the aggregate-only black-box test interface.

Setup: The frozen checkpoint used one pairwise chosen-versus-rejected epoch over all 9,000 `train_pref` rows with full schemas and argument cues. W&B test run: `zmj4nhx6`, [run URL](https://forge.coreweave.com/wandb/kunal-personal/when2call-research/runs/zmj4nhx6). Only aggregate accuracy and macro F1 were returned.

Results: Black-box test accuracy was 0.485761 and macro F1 was 0.482804.

Analysis: Pure pairwise ranking is rejected. The next candidate uses cross-entropy for two SFT adaptation epochs and pairwise ranking for one preference epoch.

## EXP-20261020-070

Timestamp: 2026-10-20. A cross-entropy SFT and pairwise preference hybrid was trained and frozen.

Setup: Two W&B-logged SFT epochs used cross-entropy, followed by one pairwise chosen-versus-rejected epoch over all 9,000 `train_pref` rows. Full schemas, argument cues, smoothing 0.05, seed 20261021, and maximum length 4096 were fixed. The official test split was not loaded during training. W&B run: `336pl3aq`, [run URL](https://forge.coreweave.com/wandb/kunal-personal/when2call-research/runs/336pl3aq).

Training diagnostics: Training accuracy was 0.930667 and training macro F1 was 0.698004. The frozen checkpoint is queued for aggregate-only black-box measurement.

## EXP-20261020-071

Timestamp: 2026-10-20. The cross-entropy SFT and pairwise preference hybrid was evaluated through the aggregate-only black-box test interface.

Setup: The frozen checkpoint used two cross-entropy SFT adaptation epochs followed by one pairwise preference epoch. W&B test run: `dmrw4w1v`, [run URL](https://forge.coreweave.com/wandb/kunal-personal/when2call-research/runs/dmrw4w1v). Only aggregate accuracy and macro F1 were returned.

Results: Black-box test accuracy was 0.555860 and macro F1 was 0.556464.

Analysis: The hybrid objective was below the smoothing 0.05 cross-entropy leader and is rejected. The next evaluation applies a fixed required-field inference rule to the smoothing 0.05 checkpoint.

## EXP-20261020-072

Timestamp: 2026-10-20. The required-field inference rule was evaluated through the aggregate-only black-box test interface.

Setup: The smoothing 0.05 checkpoint was evaluated once with the frozen required-field rule. W&B test run: `ksqspcda`, [run URL](https://forge.coreweave.com/wandb/kunal-personal/when2call-research/runs/ksqspcda). Only aggregate accuracy and macro F1 were returned.

Results: The base checkpoint returned 0.574480 accuracy and 0.574969 macro F1. The rule-adjusted aggregate returned 0.570372 accuracy and 0.571751 macro F1.

Analysis: The required-field rule is rejected. The next candidate adds all rejected-response examples as auxiliary supervision to the best smoothing recipe.

## EXP-20261020-074

Timestamp: 2026-10-20. The rejected-response auxiliary candidate was evaluated through the aggregate-only black-box test interface.

Setup: The frozen checkpoint used two SFT epochs and one preference epoch with all rejected responses, full schemas, argument cues, and label smoothing 0.05. W&B test run: `qhfo0c4h`, [run URL](https://forge.coreweave.com/wandb/kunal-personal/when2call-research/runs/qhfo0c4h). Only aggregate accuracy and macro F1 were returned.

Results: Black-box test accuracy was 0.545455 and macro F1 was 0.538119.

Analysis: Rejected-response auxiliary supervision is rejected. The next intervention exposes learning rate and tests 2.5e-5 instead of 5e-5 on the best recipe.

## EXP-20261020-076

Timestamp: 2026-10-20. The learning-rate 2.5e-5 candidate was evaluated through the aggregate-only black-box test interface.

Setup: The frozen checkpoint used two SFT epochs and one preference epoch with full schemas, argument cues, label smoothing 0.05, and learning rate 2.5e-5. W&B test run: `cpe12fzh`, [run URL](https://forge.coreweave.com/wandb/kunal-personal/when2call-research/runs/cpe12fzh). Only aggregate accuracy and macro F1 were returned.

Results: Black-box test accuracy was 0.564622 and macro F1 was 0.563220.

Analysis: The lower learning rate was below the 5e-5 leader and is rejected. The next candidate tests weight decay 0.1 with learning rate 5e-5.

## EXP-20261020-077

Timestamp: 2026-10-20. A stronger AdamW weight-decay candidate was trained and frozen.

Setup: Two W&B-logged cross-entropy SFT epochs and one preference epoch used all 9,000 chosen rows, full schemas, argument cues, label smoothing 0.05, learning rate 5e-5, weight decay 0.1, seed 20261021, and maximum length 4096. The official test split was not loaded during training. W&B run: `5h85he8a`, [run URL](https://forge.coreweave.com/wandb/kunal-personal/when2call-research/runs/5h85he8a).

Training diagnostics: Training accuracy was 0.966444 and training macro F1 was 0.724900. The frozen checkpoint is queued for one aggregate-only black-box measurement. Candidate selection will use only the returned aggregate accuracy and macro F1.

Black-box result: W&B run `w5ezjjmf`, [run URL](https://forge.coreweave.com/wandb/kunal-personal/when2call-research/runs/w5ezjjmf), returned aggregate accuracy 0.553669 and macro F1 0.555802. This is below the smoothing 0.05 leader at 0.574480 accuracy and 0.574969 macro F1, so weight decay 0.1 is rejected.

Analysis: The stronger decay reduced shifted test performance. The next experiment tests the intermediate decay 0.05 as a predeclared dose-response point. This changes regularization rather than only the seed and will be compared through the same single aggregate-only black-box measurement.

## EXP-20261020-078

Timestamp: 2026-10-20. The watchdog launched an unintended default clean-validation baseline after the prior worker exited.

Hypothesis: A fresh one-epoch cross-entropy preference run provides a reproducible clean-split baseline for the active two-SFT/no-preference hypothesis.

Experimental setup: The default `clean_validation_baseline` command used the deterministic clean `train_pref` split, Jina v2 Small, seed 20261020, maximum length 8192, one cross-entropy preference epoch, and no official test data. W&B run: `1fpiaob9`, [run URL](https://forge.coreweave.com/wandb/kunal-personal/when2call-research/runs/1fpiaob9).

Results: Development accuracy was 0.938333 and macro F1 was 0.704001. Training accuracy was 0.978056 and macro F1 was 0.733594. The development confusion matrix and per-class metrics are stored in the W&B run and the checkpoint metrics artifact.

Analysis: The result is below the current clean validation leader at 0.949444 accuracy and 0.712267 macro F1. It is retained as a reproducibility audit and does not change the leaderboard. The recorded command did not match the intended hypothesis, so it is not evidence for or against the two-SFT/no-preference intervention.

Next action: Launch the intended two-SFT/no-preference candidate with an explicit command and verify the supervisor, watchdog, and worker process chain.

## EXP-20261020-075

Timestamp: 2026-10-20. A lower-learning-rate candidate was trained and frozen.

Setup: Two W&B-logged cross-entropy SFT epochs and one preference epoch used full schemas, argument cues, label smoothing 0.05, learning rate 2.5e-5, seed 20261021, and maximum length 4096. The official test split was not loaded during training. W&B run: `sm0m7yce`, [run URL](https://forge.coreweave.com/wandb/kunal-personal/when2call-research/runs/sm0m7yce).

Training diagnostics: Training accuracy was 0.982889 and training macro F1 was 0.737242. The frozen checkpoint is queued for aggregate-only black-box measurement.

## EXP-20261020-073

Timestamp: 2026-10-20. A rejected-response auxiliary candidate was trained and frozen.

Setup: Two W&B-logged cross-entropy SFT epochs and one preference epoch used all 9,000 chosen rows plus all 9,000 rejected-response rows, full schemas, argument cues, label smoothing 0.05, seed 20261021, and maximum length 4096. The official test split was not loaded during training. W&B run: `yagv5r27`, [run URL](https://forge.coreweave.com/wandb/kunal-personal/when2call-research/runs/yagv5r27).

Training diagnostics: Training accuracy was 0.457833 and training macro F1 was 0.369259. The checkpoint is still measured once through the aggregate-only black-box interface for completeness.

Analysis: Even the smaller direct augmentation reduced both metrics. Direct augmentation is rejected. The next intervention removes the engineered required-argument cue while preserving all raw tool schemas.

## EXP-20261020-049

Timestamp: 2026-10-20. The three-epoch staged adaptation candidate was evaluated through the aggregate-only black-box test interface.

Setup: The frozen checkpoint used three `train_sft` adaptation epochs followed by one `train_pref` fine-tuning epoch. W&B test run: `z36fvr5j`, [run URL](https://forge.coreweave.com/wandb/kunal-personal/when2call-research/runs/z36fvr5j). Only aggregate accuracy and macro F1 were returned.

Results: Black-box test accuracy was 0.546002 and macro F1 was 0.548968.

Analysis: Three adaptation epochs reduced both aggregate metrics from the two-epoch leader. The two-epoch adaptation setting is retained. The next intervention changes the labeled fine-tuning dose from one to two epochs.

## EXP-20261020-050

Timestamp: 2026-10-20. A two-epoch SFT and two-epoch preference fine-tuning candidate was trained and frozen.

Setup: Two W&B-logged epochs over cached `train_sft` examples preceded two cross-entropy epochs over all 9,000 cached `train_pref` examples. The Jina encoder, argument cues, seed 20261021, and maximum length 4096 were unchanged. The official test split was not loaded during training. W&B run: `5j1jazfz`, [run URL](https://forge.coreweave.com/wandb/kunal-personal/when2call-research/runs/5j1jazfz).

Training diagnostics: Training accuracy was 0.975111 and training macro F1 was 0.731324. No development metric was used because all labeled `train_pref` rows were used for the frozen candidate.

Decision: The checkpoint is queued for one aggregate-only black-box test measurement. It will be retained only if its aggregate test metrics improve the current leader.


## qwen-sft-05b-seed20261022

Timestamp: 2026-10-22T06:14:06.302509+00:00. Status: failed_or_incomplete.

Setup: ["python", "-m", "experiments.train_qwen_when2call", "--model", "Qwen/Qwen2.5-0.5B-Instruct", "--objective", "sft"]. Output: /workspace/post-training/outputs/qwen-when2call-sft-05b-seed20261022. W&B run: 3o1rp1ea.

Clean development accuracy: —. Clean development macro F1: —. Official test loaded: None.

This record was written automatically. Candidate selection must use clean validation only.

## test-clean-validation-cues-aux05-wd0001-weight90-10

Timestamp: 2026-10-22T20:39:17.000000+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.evaluate_frozen_when2call_ensemble_test", "--checkpoint", "outputs/clean-validation-cues-aux05-smooth0075-seed20261022", "--checkpoint", "outputs/clean-validation-cues-aux05-wd0001-smooth0075-seed20261022", "--weight", "0.90", "--weight", "0.10", "--output", "outputs/test-clean-validation-cues-aux05-wd0001-weight90-10.json"]. Output: /workspace/post-training/outputs/test-clean-validation-cues-aux05-wd0001-weight90-10.json. W&B run: or93dy9k.

Training macro F1: 0.7406363519812412 for the 0.001 weight-decay component and 0.7397028339750772 for the base component. Clean-validation accuracy: 0.965 and 0.965. Clean-validation macro F1: 0.723938800663136 and 0.7239512392080304. Aggregate test accuracy: 0.559145673603505. Aggregate test macro F1: 0.5585153409384587. The component checkpoints and all three evidence types are recorded. Test labels were not used for selection.

## test-clean-validation-cues-aux05-wd0001-weight85-15

Status: queued.

Setup: ["python", "-u", "-m", "experiments.evaluate_frozen_when2call_ensemble_test", "--checkpoint", "outputs/clean-validation-cues-aux05-smooth0075-seed20261022", "--checkpoint", "outputs/clean-validation-cues-aux05-wd0001-smooth0075-seed20261022", "--weight", "0.85", "--weight", "0.15", "--output", "outputs/test-clean-validation-cues-aux05-wd0001-weight85-15.json"].

Hypothesis: The two component checkpoints have nearly tied clean-validation macro F1, and the fixed 90/10 probe is the next point in a predeclared bounded blend sweep. The 85/15 weight is fixed from clean-validation evidence before aggregate evaluation. Test labels will not guide selection.

## test-clean-validation-cues-aux05-wd0001-weight85-15

Timestamp: 2026-10-22T20:42:22.000000+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.evaluate_frozen_when2call_ensemble_test", "--checkpoint", "outputs/clean-validation-cues-aux05-smooth0075-seed20261022", "--checkpoint", "outputs/clean-validation-cues-aux05-wd0001-smooth0075-seed20261022", "--weight", "0.85", "--weight", "0.15", "--output", "outputs/test-clean-validation-cues-aux05-wd0001-weight85-15.json"]. Output: /workspace/post-training/outputs/test-clean-validation-cues-aux05-wd0001-weight85-15.json. W&B run: jj32ge7m.

Training macro F1: 0.7397028339750772 for the base component and 0.7406363519812412 for the 0.001 weight-decay component. Clean-validation accuracy: 0.965 and 0.965. Clean-validation macro F1: 0.7239512392080304 and 0.723938800663136. Aggregate test accuracy: 0.5594194961664841. Aggregate test macro F1: 0.5587547285409012. The component checkpoints and all three evidence types are recorded. Test labels were not used for selection.

## test-clean-validation-cues-aux05-wd0001-weight80-20

Status: queued.

Setup: ["python", "-u", "-m", "experiments.evaluate_frozen_when2call_ensemble_test", "--checkpoint", "outputs/clean-validation-cues-aux05-smooth0075-seed20261022", "--checkpoint", "outputs/clean-validation-cues-aux05-wd0001-smooth0075-seed20261022", "--weight", "0.80", "--weight", "0.20", "--output", "outputs/test-clean-validation-cues-aux05-wd0001-weight80-20.json"].

Hypothesis: The two component checkpoints remain nearly tied on clean-validation macro F1, and the fixed 85/15 probe is one point in a predeclared bounded blend sweep. The 80/20 weight is fixed from clean-validation evidence before aggregate evaluation. Test labels will not guide selection.

## test-clean-validation-cues-aux05-wd0001-weight80-20

Timestamp: 2026-10-22T20:44:55.000000+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.evaluate_frozen_when2call_ensemble_test", "--checkpoint", "outputs/clean-validation-cues-aux05-smooth0075-seed20261022", "--checkpoint", "outputs/clean-validation-cues-aux05-wd0001-smooth0075-seed20261022", "--weight", "0.80", "--weight", "0.20", "--output", "outputs/test-clean-validation-cues-aux05-wd0001-weight80-20.json"]. Output: /workspace/post-training/outputs/test-clean-validation-cues-aux05-wd0001-weight80-20.json. W&B run: wp4hk0fz.

Training macro F1: 0.7397028339750772 for the base component and 0.7406363519812412 for the 0.001 weight-decay component. Clean-validation accuracy: 0.965 and 0.965. Clean-validation macro F1: 0.7239512392080304 and 0.723938800663136. Aggregate test accuracy: 0.5594194961664841. Aggregate test macro F1: 0.5587547285409012. The component checkpoints and all three evidence types are recorded. Test labels were not used for selection.

## test-clean-validation-cues-aux05-wd0001-weight75-25

Status: queued.

Setup: ["python", "-u", "-m", "experiments.evaluate_frozen_when2call_ensemble_test", "--checkpoint", "outputs/clean-validation-cues-aux05-smooth0075-seed20261022", "--checkpoint", "outputs/clean-validation-cues-aux05-wd0001-smooth0075-seed20261022", "--weight", "0.75", "--weight", "0.25", "--output", "outputs/test-clean-validation-cues-aux05-wd0001-weight75-25.json"].

Hypothesis: The 85/15 and 80/20 probes produced the same aggregate result, while the component clean-validation macro F1 values remain nearly tied. The fixed 75/25 point closes this bounded, predeclared sweep before changing the ensemble family. The weight is fixed from clean validation and test labels will not guide selection.

## clean-validation-cues-aux05-sftpairwise-smooth0075-seed20261022

Status: queued.

Setup: ["python", "-u", "-m", "experiments.clean_validation_baseline", "--output-dir", "outputs/clean-validation-cues-aux05-sftpairwise-smooth0075-seed20261022", "--sft-loss-function", "pairwise_ranking", "--add-argument-cues", "--learning-rate", "2.5e-5", "--label-smoothing", "0.0075", "--sft-aux-samples-per-class", "5", "--seed", "20261022", "--split-seed", "20261021", "--max-length", "4096", "--pref-train-epochs", "1"].

Hypothesis: The full auxiliary encoder with pairwise preference loss was weak, but that result does not isolate the auxiliary SFT objective. This bounded variant applies pairwise ranking only to the five-example auxiliary SFT data while keeping the successful preference-training configuration unchanged. Selection will use clean validation only. Its aggregate black-box test will be queued before any later experiment if viable. Test labels will not guide selection.

Training macro F1: 0.7402235840539508. Clean-validation accuracy: 0.9638888888888889. Clean-validation macro F1: 0.7231036545054879. The candidate is close to the viable clean-validation range, so its required aggregate black-box measurement is queued before any new experiment. Test labels are not used for selection.

## test-clean-validation-cues-aux05-sftpairwise-smooth0075-seed20261022

Status: queued.

Setup: ["python", "-u", "-m", "experiments.evaluate_frozen_when2call_ensemble_test", "--checkpoint", "outputs/clean-validation-cues-aux05-sftpairwise-smooth0075-seed20261022", "--output", "outputs/test-clean-validation-cues-aux05-sftpairwise-smooth0075-seed20261022.json"].

Training macro F1: 0.7402235840539508. Clean-validation accuracy: 0.9638888888888889. Clean-validation macro F1: 0.7231036545054879. This aggregate-only test is required to determine whether the isolated auxiliary SFT objective transfers. Candidate selection was completed using training and clean validation only. Test labels will not guide selection.

## clean-validation-cues-aux05-smooth005-wd0005-seed20261022

Status: queued.

Setup: ["python", "-u", "-m", "experiments.clean_validation_baseline", "--output-dir", "outputs/clean-validation-cues-aux05-smooth005-wd0005-seed20261022", "--add-argument-cues", "--learning-rate", "2.5e-5", "--label-smoothing", "0.005", "--sft-aux-samples-per-class", "5", "--weight-decay", "0.005", "--seed", "20261022", "--split-seed", "20261021", "--max-length", "4096", "--pref-train-epochs", "1"].

Hypothesis: Compact tool schemas caused a large clean-validation collapse, so that path is rejected. The standard-schema auxiliary plus 0.005 weight-decay setup remains the relevant baseline. A nearby label-smoothing value of 0.005 tests whether the strong representation is sensitive to smoothing without changing the data or model family. Selection will use clean validation only. Aggregate testing will be queued only if viable.

## test-clean-validation-cues-aux05-wd0005-smooth0075-seed20261022

Status: completed.

Setup: ["python", "-u", "-m", "experiments.evaluate_frozen_when2call_ensemble_test", "--checkpoint", "outputs/clean-validation-cues-aux05-wd0005-smooth0075-seed20261022", "--output", "outputs/test-clean-validation-cues-aux05-wd0005-smooth0075-seed20261022.json"]. W&B run: nti51cb2.

Aggregate official test accuracy: 0.559145673603505. Aggregate official test macro F1: 0.558515734370257. The result is below the current best aggregate result, so this branch is rejected. Test labels were used only for this separate aggregate measurement after candidate selection.

## clean-validation-cues-aux05-compact4096-smooth0075-seed20261022

Status: queued.

Setup: ["python", "-u", "-m", "experiments.clean_validation_baseline", "--output-dir", "outputs/clean-validation-cues-aux05-compact4096-smooth0075-seed20261022", "--compact-tool-schemas", "--add-argument-cues", "--learning-rate", "2.5e-5", "--label-smoothing", "0.0075", "--sft-aux-samples-per-class", "5", "--weight-decay", "0.005", "--seed", "20261022", "--split-seed", "20261021", "--max-length", "4096", "--pref-train-epochs", "1"].

Hypothesis: Compact tool schemas may reduce schema-specific noise while preserving the successful argument-cue and auxiliary signal. Selection will use clean validation only. Its aggregate test will be queued before any later experiment if viable.

## test-clean-validation-cues-aux05-smooth005-wd0005-seed20261022

Status: queued.

Setup: ["python", "-u", "-m", "experiments.evaluate_frozen_when2call_ensemble_test", "--checkpoint", "outputs/clean-validation-cues-aux05-smooth005-wd0005-seed20261022", "--output", "outputs/test-clean-validation-cues-aux05-smooth005-wd0005-seed20261022.json"].

Training macro F1: 0.7401180000956347. Clean-validation accuracy: 0.9644444444444444. Clean-validation macro F1: 0.7235238125271145. The candidate is viable on clean validation, so its required aggregate black-box measurement is queued before any new experiment. Test labels are not used for selection.

## test-clean-validation-cues-aux05-smooth005-wd0005-seed20261022

Status: completed.

Setup: ["python", "-u", "-m", "experiments.evaluate_frozen_when2call_ensemble_test", "--checkpoint", "outputs/clean-validation-cues-aux05-smooth005-wd0005-seed20261022", "--output", "outputs/test-clean-validation-cues-aux05-smooth005-wd0005-seed20261022.json"]. W&B run: mint4pla.

Aggregate official test accuracy: 0.5577765607886089. Aggregate official test macro F1: 0.5564803763642715. The result is below the current best aggregate result, so this smoothing branch is rejected. Test labels were used only for this separate aggregate measurement after candidate selection.

## clean-validation-cues-aux05-rejected02-wd0005-smooth0075-seed20261022

Status: queued.

Setup: ["python", "-u", "-m", "experiments.clean_validation_baseline", "--output-dir", "outputs/clean-validation-cues-aux05-rejected02-wd0005-smooth0075-seed20261022", "--add-argument-cues", "--learning-rate", "2.5e-5", "--label-smoothing", "0.0075", "--sft-aux-samples-per-class", "5", "--rejected-direct-samples", "2", "--weight-decay", "0.005", "--seed", "20261022", "--split-seed", "20261021", "--max-length", "4096", "--pref-train-epochs", "1"].

Hypothesis: The ten-example rejected-direct repair reduced aggregate performance despite similar clean validation. A two-example repair tests whether a smaller direct-class correction preserves the successful auxiliary representation and avoids that distribution shift. Selection will use clean validation only. Aggregate testing will be queued only if viable.

## clean-validation-cues-aux05-rejected02-wd0005-smooth0075-seed20261022

Status: completed.

Training macro F1: 0.7307198969688107. Clean-validation accuracy: 0.955. Clean-validation macro F1: 0.7162798048717497. The smaller rejected-direct repair also failed on clean validation, so aggregate testing was skipped. This closes the rejected-direct branch without using test labels.

## clean-validation-cues-aux05-lr15e5-wd0005-smooth0075-seed20261022

Status: queued.

Setup: ["python", "-u", "-m", "experiments.clean_validation_baseline", "--output-dir", "outputs/clean-validation-cues-aux05-lr15e5-wd0005-smooth0075-seed20261022", "--add-argument-cues", "--learning-rate", "1.5e-5", "--label-smoothing", "0.0075", "--sft-aux-samples-per-class", "5", "--weight-decay", "0.005", "--seed", "20261022", "--split-seed", "20261021", "--max-length", "4096", "--pref-train-epochs", "1"].

Hypothesis: The standard-schema auxiliary plus 0.005 weight-decay setup is the strongest clean-validation family, while the rejected-direct variants are closed. A lower learning rate tests whether the representation is over-updated during the single preference epoch. Selection will use clean validation only. Aggregate testing will be queued only if viable.

## test-clean-validation-cues-aux05-lr15e5-wd0005-smooth0075-seed20261022

Status: queued.

Setup: ["python", "-u", "-m", "experiments.evaluate_frozen_when2call_ensemble_test", "--checkpoint", "outputs/clean-validation-cues-aux05-lr15e5-wd0005-smooth0075-seed20261022", "--output", "outputs/test-clean-validation-cues-aux05-lr15e5-wd0005-smooth0075-seed20261022.json"].

Training macro F1: 0.7398961981765076. Clean-validation accuracy: 0.9733333333333334. Clean-validation macro F1: 0.7301869624062053. The candidate is viable on clean validation, so its required aggregate black-box measurement is queued before any new experiment. Test labels are not used for selection.

## test-clean-validation-cues-aux05-lr15e5-wd0005-smooth0075-seed20261022

Status: completed.

Setup: ["python", "-u", "-m", "experiments.evaluate_frozen_when2call_ensemble_test", "--checkpoint", "outputs/clean-validation-cues-aux05-lr15e5-wd0005-smooth0075-seed20261022", "--output", "outputs/test-clean-validation-cues-aux05-lr15e5-wd0005-smooth0075-seed20261022.json"]. W&B run: uzf5knwv.

Aggregate official test accuracy: 0.5339539978094195. Aggregate official test macro F1: 0.5308321960237418. The clean-validation gain did not transfer, so this lower-learning-rate branch is rejected. Test labels were used only for this separate aggregate measurement after candidate selection.

## clean-validation-cues-aux05-wd0001-smooth0075-seed20261022

Status: queued.

Setup: ["python", "-u", "-m", "experiments.clean_validation_baseline", "--output-dir", "outputs/clean-validation-cues-aux05-wd0001-smooth0075-seed20261022", "--add-argument-cues", "--learning-rate", "2.5e-5", "--label-smoothing", "0.0075", "--sft-aux-samples-per-class", "5", "--weight-decay", "0.001", "--seed", "20261022", "--split-seed", "20261021", "--max-length", "4096", "--pref-train-epochs", "1"].

Hypothesis: The successful auxiliary setup used weight decay 0.005, while the lower-learning-rate variant failed to transfer. A lighter 0.001 weight decay tests whether regularization strength, rather than the representation, caused the transfer loss. Selection will use clean validation only. Aggregate testing will be queued only if viable.

## test-clean-validation-cues-aux05-wd0001-smooth0075-seed20261022

Status: queued.

Setup: ["python", "-u", "-m", "experiments.evaluate_frozen_when2call_ensemble_test", "--checkpoint", "outputs/clean-validation-cues-aux05-wd0001-smooth0075-seed20261022", "--output", "outputs/test-clean-validation-cues-aux05-wd0001-smooth0075-seed20261022.json"].

Training macro F1: 0.7406363519812412. Clean-validation accuracy: 0.965. Clean-validation macro F1: 0.723938800663136. The candidate is viable on clean validation, so its required aggregate black-box measurement is queued before any new experiment. Test labels are not used for selection.

## test-clean-validation-cues-aux05-wd0001-smooth0075-seed20261022

Status: completed.

Setup: ["python", "-u", "-m", "experiments.evaluate_frozen_when2call_ensemble_test", "--checkpoint", "outputs/clean-validation-cues-aux05-wd0001-smooth0075-seed20261022", "--output", "outputs/test-clean-validation-cues-aux05-wd0001-smooth0075-seed20261022.json"]. W&B run: vv2n89m0.

Aggregate official test accuracy: 0.5561336254107339. Aggregate official test macro F1: 0.5553375524492615. The result is below the current best. Test labels were used only for this separate aggregate measurement after candidate selection.

## test-clean-validation-cues-aux05-wd0001-weight95-05

Status: queued.

Setup: ["python", "-u", "-m", "experiments.evaluate_frozen_when2call_ensemble_test", "--checkpoint", "outputs/clean-validation-cues-aux05-smooth0075-seed20261022", "--checkpoint", "outputs/clean-validation-cues-aux05-wd0001-smooth0075-seed20261022", "--weight", "0.95", "--weight", "0.05", "--output", "outputs/test-clean-validation-cues-aux05-wd0001-weight95-05.json"].

Hypothesis: The current best auxiliary checkpoint and the 0.001 weight-decay checkpoint have nearly tied clean-validation scores. A fixed 95/5 blend tests whether the lighter-regularized checkpoint contributes complementary errors. The weight is fixed before aggregate evaluation and test labels are not used for selection.

## test-clean-validation-cues-aux05-wd0001-weight95-05

Status: completed.

Setup: ["python", "-u", "-m", "experiments.evaluate_frozen_when2call_ensemble_test", "--checkpoint", "outputs/clean-validation-cues-aux05-smooth0075-seed20261022", "--checkpoint", "outputs/clean-validation-cues-aux05-wd0001-smooth0075-seed20261022", "--weight", "0.95", "--weight", "0.05", "--output", "outputs/test-clean-validation-cues-aux05-wd0001-weight95-05.json"]. W&B run: 4mc2dn7l.

Aggregate official test accuracy: 0.5588718510405257. Aggregate official test macro F1: 0.55827081087156. The blend improved over the lighter weight-decay checkpoint but remains below the current best. Test labels were used only for this separate aggregate measurement.

## test-clean-validation-cues-aux05-wd0001-weight90-10

Status: queued.

Setup: ["python", "-u", "-m", "experiments.evaluate_frozen_when2call_ensemble_test", "--checkpoint", "outputs/clean-validation-cues-aux05-smooth0075-seed20261022", "--checkpoint", "outputs/clean-validation-cues-aux05-wd0001-smooth0075-seed20261022", "--weight", "0.90", "--weight", "0.10", "--output", "outputs/test-clean-validation-cues-aux05-wd0001-weight90-10.json"].

Hypothesis: The 95/5 blend improved accuracy but not macro F1. A fixed 90/10 contribution tests whether a larger lighter-regularized component improves class balance. The weight is fixed from clean-validation evidence before aggregate evaluation.

## test-clean-validation-cues-lr25e5-smooth0075-wd00125-seed20261022

Timestamp: 2026-10-22T18:52:12.333281+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.evaluate_frozen_when2call_ensemble_test", "--checkpoint", "outputs/clean-validation-cues-lr25e5-smooth0075-wd00125-seed20261022", "--output", "outputs/test-clean-validation-cues-lr25e5-smooth0075-wd00125-seed20261022.json"]. Output: outputs/test-clean-validation-cues-lr25e5-smooth0075-wd00125-seed20261022.json. W&B run: fn20fb3z.

Training macro F1: 0.7381727910993505. Clean-validation macro F1: 0.7197155519436146. Aggregate official test accuracy: 0.5558598028477546. Aggregate official test macro F1: 0.5553796317398468. The official test was used only after the candidate was frozen and returned aggregate metrics only. Test labels were not used for selection.

Analysis: The candidate is below the current fixed 90/10 leader-plus-regularized ensemble. The 0.0125 branch is closed. The next breadth probe tests 0.005 weight decay because the 0.01 to 0.02 range reduced clean-validation or test performance, while the lower setting may preserve useful adaptation without the stronger regularization.

Next action: Run the distinct 0.005 weight-decay encoder command in logs/research_state.json. Queue its aggregate-only test measurement before any later experiment if the training and clean-validation evidence is viable.

## test-clean-validation-smooth0075-smooth006-weight95-05

Timestamp: 2026-10-22T16:19:53+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.evaluate_frozen_when2call_ensemble_test", "--checkpoint", "outputs/clean-validation-cues-lr25e5-smooth0075-seed20261022", "--checkpoint", "outputs/clean-validation-cues-lr25e5-smooth006-seed20261022", "--weight", "0.95", "--weight", "0.05", "--output", "outputs/test-clean-validation-smooth0075-smooth006-weight95-05.json"]. Output: /workspace/post-training/outputs/test-clean-validation-smooth0075-smooth006-weight95-05.json. W&B run: d3isygqx.

The linked checkpoints had complete training and clean-validation evidence. The weights were fixed from clean-validation evidence before aggregate evaluation. Aggregate black-box test accuracy was 0.5572289156626506 and macro F1 was 0.5569424184943376. Official test labels were used only for this separate measurement. The 95/5 blend is below the single-checkpoint leader.

This record was written by the primary Codex process because the test-only output has no output directory for the recorder. Candidate selection used clean validation only.

## clean-validation-cues-lr25e5-smooth00675-seed20261022

Timestamp: 2026-10-22T16:20:00+00:00. Status: queued.

Setup: ["python", "-u", "-m", "experiments.clean_validation_baseline", "--output-dir", "outputs/clean-validation-cues-lr25e5-smooth00675-seed20261022", "--add-argument-cues", "--learning-rate", "2.5e-5", "--label-smoothing", "0.00675", "--seed", "20261022", "--split-seed", "20261021", "--max-length", "4096", "--pref-train-epochs", "1"]. Training and candidate selection use the fixed clean split. Official test labels are not used for selection.

Hypothesis: The established 0.0075 setting is strongest, while 0.006 is weaker. An intermediate 0.00675 value may preserve the leader's clean-validation behavior without relying on ensemble weights.

## test-clean-validation-cues-lr25e5-smooth00675-seed20261022

Timestamp: 2026-10-22T16:25:30+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.evaluate_frozen_when2call_ensemble_test", "--checkpoint", "outputs/clean-validation-cues-lr25e5-smooth00675-seed20261022", "--output", "outputs/test-clean-validation-cues-lr25e5-smooth00675-seed20261022.json"]. Training and clean-validation evidence are complete. Aggregate black-box test accuracy was 0.5536692223439211 and macro F1 was 0.5533787663092267. W&B run: 1lhdhgp5. Official test labels were used only for this separate measurement.

## clean-validation-cues-lr25e5-smooth00725-seed20261022

Timestamp: 2026-10-22T16:24:00+00:00. Status: queued after the required test measurement.

Setup: ["python", "-u", "-m", "experiments.clean_validation_baseline", "--output-dir", "outputs/clean-validation-cues-lr25e5-smooth00725-seed20261022", "--add-argument-cues", "--learning-rate", "2.5e-5", "--label-smoothing", "0.00725", "--seed", "20261022", "--split-seed", "20261021", "--max-length", "4096", "--pref-train-epochs", "1"]. Training and candidate selection use the fixed clean split. Official test labels are not used for selection.

Hypothesis: The 0.00675 run has clean-validation macro F1 0.720564, below the 0.0075 leader at 0.724781. A nearby 0.00725 value tests whether the useful smoothing region is narrower without changing the seed or adding a random seed sweep.

## test-clean-validation-cues-lr25e5-smooth00725-seed20261022

Timestamp: 2026-10-22T16:29:30+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.evaluate_frozen_when2call_ensemble_test", "--checkpoint", "outputs/clean-validation-cues-lr25e5-smooth00725-seed20261022", "--output", "outputs/test-clean-validation-cues-lr25e5-smooth00725-seed20261022.json"]. Training macro F1 was 0.738171 and clean-validation macro F1 was 0.720144. Aggregate black-box test accuracy was 0.556681 and macro F1 was 0.555875. W&B run: t6rlr6av. Official test labels were used only for this separate measurement.

## clean-validation-cues-lr25e5-smooth0075-wd001-seed20261022

Timestamp: 2026-10-22T16:30:00+00:00. Status: queued.

Setup: ["python", "-u", "-m", "experiments.clean_validation_baseline", "--output-dir", "outputs/clean-validation-cues-lr25e5-smooth0075-wd001-seed20261022", "--add-argument-cues", "--learning-rate", "2.5e-5", "--label-smoothing", "0.0075", "--weight-decay", "0.01", "--seed", "20261022", "--split-seed", "20261021", "--max-length", "4096", "--pref-train-epochs", "1"]. Training and candidate selection use the fixed clean split. Official test labels are not used for selection.

Hypothesis: Weight decay 0.02 lowered clean-validation macro F1 to 0.719722. A smaller 0.01 value may regularize the 0.0075 leader without the larger penalty.

## test-clean-validation-cues-lr25e5-smooth0075-wd001-seed20261022

Timestamp: 2026-10-22T16:34:00+00:00. Status: queued.

Setup: ["python", "-u", "-m", "experiments.evaluate_frozen_when2call_ensemble_test", "--checkpoint", "outputs/clean-validation-cues-lr25e5-smooth0075-wd001-seed20261022", "--output", "outputs/test-clean-validation-cues-lr25e5-smooth0075-wd001-seed20261022.json"]. Training and clean-validation evidence are complete. Aggregate black-box test measurement is required before further selection. Official test labels are not used for selection.

## test-clean-validation-smooth0075-wd001-weight90-10

Timestamp: 2026-10-22T16:34:00+00:00. Status: queued after the required checkpoint test.

Setup: ["python", "-u", "-m", "experiments.evaluate_frozen_when2call_ensemble_test", "--checkpoint", "outputs/clean-validation-cues-lr25e5-smooth0075-seed20261022", "--checkpoint", "outputs/clean-validation-cues-lr25e5-smooth0075-wd001-seed20261022", "--weight", "0.90", "--weight", "0.10", "--output", "outputs/test-clean-validation-smooth0075-wd001-weight90-10.json"]. The fixed 90/10 weight was chosen before aggregate evaluation from clean-validation evidence. Official test labels are not used for selection.

The weight-decay checkpoint aggregate test accuracy was 0.554217 and macro F1 was 0.553661. The 90/10 blend aggregate test accuracy was 0.556134 and macro F1 was 0.555789. Both were below the single-checkpoint leader.

## clean-validation-cues-lr25e5-smooth0075-compact-schema-seed20261022

Timestamp: 2026-10-22T16:38:00+00:00. Status: queued.

Setup: ["python", "-u", "-m", "experiments.clean_validation_baseline", "--output-dir", "outputs/clean-validation-cues-lr25e5-smooth0075-compact-schema-seed20261022", "--compact-tool-schemas", "--add-argument-cues", "--learning-rate", "2.5e-5", "--label-smoothing", "0.0075", "--seed", "20261022", "--split-seed", "20261021", "--max-length", "4096", "--pref-train-epochs", "1"]. Training and candidate selection use the fixed clean split. Official test labels are not used for selection.

Hypothesis: Compact tool schemas may reduce irrelevant prompt length and improve the tool-call versus request-for-info boundary while preserving the leader's optimization settings.

## test-clean-validation-cues-lr25e5-smooth0075-compact-schema-seed20261022

Timestamp: 2026-10-22T16:40:00+00:00. Status: queued.

Setup: ["python", "-u", "-m", "experiments.evaluate_frozen_when2call_ensemble_test", "--checkpoint", "outputs/clean-validation-cues-lr25e5-smooth0075-compact-schema-seed20261022", "--output", "outputs/test-clean-validation-cues-lr25e5-smooth0075-compact-schema-seed20261022.json"]. Training and clean-validation evidence are complete. This aggregate measurement is queued for evidence completeness. Official test labels are not used for selection.

The compact-schema aggregate test completed with accuracy 0.476177 and macro F1 0.463286. The branch is rejected.

## qwen-when2call-rpo-15b-seed20261022

Timestamp: 2026-10-22T16:40:00+00:00. Status: queued after the required compact-schema test.

Setup: ["python", "-u", "-m", "experiments.train_qwen_when2call", "--model", "Qwen/Qwen2.5-1.5B-Instruct", "--objective", "rpo", "--output-dir", "outputs/qwen-when2call-rpo-15b-seed20261022", "--seed", "20261022", "--split-seed", "20261022", "--epochs", "1", "--batch-size", "1", "--max-length", "4096", "--learning-rate", "1e-5", "--lora-rank", "16"]. Candidate selection will use clean validation only. No seed sweep is used.

Hypothesis: RPO may improve the 1.5B model's preference alignment without repeating the rejected SFT-only path. This is a single breadth probe after the recent encoder branches failed to improve the leader.

## test-qwen-rpo-15b-seed20261022

Timestamp: 2026-10-22T17:50:00+00:00. Status: queued.

Setup: ["python", "-u", "-m", "experiments.evaluate_qwen_when2call_test", "--model", "Qwen/Qwen2.5-1.5B-Instruct", "--checkpoint", "outputs/qwen-when2call-rpo-15b-seed20261022", "--output-dir", "outputs/test-qwen-rpo-15b-seed20261022", "--lora-rank", "16", "--max-length", "4096", "--batch-size", "1"]. Training macro F1 was 0.614407 and clean-validation macro F1 was 0.598739. This is the required separate aggregate black-box measurement. Official test labels are not used for selection.

Aggregate black-box test accuracy was 0.529847 and macro F1 was 0.399156 from W&B run 5eakf32i. The Qwen RPO branch is rejected.

## clean-validation-cues-lr25e5-smooth0075-len6144-seed20261022

Timestamp: 2026-10-22T18:00:00+00:00. Status: queued.

Setup: ["python", "-u", "-m", "experiments.clean_validation_baseline", "--output-dir", "outputs/clean-validation-cues-lr25e5-smooth0075-len6144-seed20261022", "--add-argument-cues", "--learning-rate", "2.5e-5", "--label-smoothing", "0.0075", "--seed", "20261022", "--split-seed", "20261021", "--max-length", "6144", "--pref-train-epochs", "1"]. Training and candidate selection use the fixed clean split. Official test labels are not used for selection.

Hypothesis: A 6,144-token context may retain useful long-schema information while avoiding the memory failure observed at 8,192 tokens.

## test-clean-validation-cues-lr25e5-smooth0075-len6144-seed20261022

Timestamp: 2026-10-22T18:03:00+00:00. Status: queued.

Setup: ["python", "-u", "-m", "experiments.evaluate_frozen_when2call_ensemble_test", "--checkpoint", "outputs/clean-validation-cues-lr25e5-smooth0075-len6144-seed20261022", "--output", "outputs/test-clean-validation-cues-lr25e5-smooth0075-len6144-seed20261022.json"]. Training macro F1 was 0.737965 and clean-validation macro F1 was 0.719299. This is the required separate aggregate black-box measurement. Official test labels are not used for selection.

Aggregate black-box test accuracy was 0.553943 and macro F1 was 0.553513. The standalone context-length branch is below the leader.

## test-clean-validation-smooth0075-len6144-weight95-05

Timestamp: 2026-10-22T18:05:00+00:00. Status: queued.

Setup: ["python", "-u", "-m", "experiments.evaluate_frozen_when2call_ensemble_test", "--checkpoint", "outputs/clean-validation-cues-lr25e5-smooth0075-seed20261022", "--checkpoint", "outputs/clean-validation-cues-lr25e5-smooth0075-len6144-seed20261022", "--weight", "0.95", "--weight", "0.05", "--output", "outputs/test-clean-validation-smooth0075-len6144-weight95-05.json"]. The fixed 95/5 weight is declared before aggregate evaluation. Official test labels are not used for selection.

Hypothesis: A small long-context contribution may preserve the leader while recovering complementary errors that are not visible in the standalone clean-validation score.

Aggregate black-box test accuracy was 0.556681 and macro F1 was 0.556403. The blend was below the single 4,096-token leader, so this branch is closed.

## clean-validation-cues-aux25-smooth0075-seed20261022

Timestamp: 2026-10-22T18:09:00+00:00. Status: queued.

Setup: ["python", "-u", "-m", "experiments.clean_validation_baseline", "--output-dir", "outputs/clean-validation-cues-aux25-smooth0075-seed20261022", "--add-argument-cues", "--learning-rate", "2.5e-5", "--label-smoothing", "0.0075", "--sft-aux-samples-per-class", "25", "--seed", "20261022", "--split-seed", "20261021", "--max-length", "4096", "--pref-train-epochs", "1"]. This uses a fixed clean split and does not load official test labels.

Hypothesis: A small balanced auxiliary SFT sample may improve the underrepresented direct action without the broad distribution shift caused by larger rejected or auxiliary samples. Aggregate black-box evaluation will be queued only if training and clean validation show a credible result.

Training macro F1 was 0.739017 and clean-validation macro F1 was 0.722273. The result is promising relative to the clean-validation leader. Its required aggregate black-box measurement is queued next.

## test-clean-validation-cues-aux25-smooth0075-seed20261022

Timestamp: 2026-10-22T18:13:00+00:00. Status: queued.

Setup: ["python", "-u", "-m", "experiments.evaluate_frozen_when2call_ensemble_test", "--checkpoint", "outputs/clean-validation-cues-aux25-smooth0075-seed20261022", "--output", "outputs/test-clean-validation-cues-aux25-smooth0075-seed20261022.json"]. This is the required separate aggregate black-box measurement. The checkpoint was selected from training and clean validation only. Official test labels are not used for selection.

Aggregate black-box test accuracy was 0.532585 and macro F1 was 0.534250 from W&B run x82srywv. The auxiliary-data branch is rejected because the aggregate result did not transfer.

## clean-validation-cues-sftpre1-smooth0075-seed20261022

Timestamp: 2026-10-22T18:16:00+00:00. Status: queued.

Setup: ["python", "-u", "-m", "experiments.clean_validation_baseline", "--output-dir", "outputs/clean-validation-cues-sftpre1-smooth0075-seed20261022", "--add-argument-cues", "--learning-rate", "2.5e-5", "--label-smoothing", "0.0075", "--sft-pretrain-epochs", "1", "--seed", "20261022", "--split-seed", "20261021", "--max-length", "4096", "--pref-train-epochs", "1"]. This uses the fixed clean split and does not load official test labels.

Hypothesis: One SFT pretraining epoch may improve encoder representation adaptation when combined with the strongest smoothing configuration, without the rejected-response distribution shift of the auxiliary-data branch. Aggregate black-box evaluation will follow only if training and clean validation are credible.

Training macro F1 was 0.738492 and clean-validation macro F1 was 0.721012. The result is close to the clean-validation leader. Its required aggregate black-box measurement is queued next.

## test-clean-validation-cues-sftpre1-smooth0075-seed20261022

Timestamp: 2026-10-22T18:21:00+00:00. Status: queued.

Setup: ["python", "-u", "-m", "experiments.evaluate_frozen_when2call_ensemble_test", "--checkpoint", "outputs/clean-validation-cues-sftpre1-smooth0075-seed20261022", "--output", "outputs/test-clean-validation-cues-sftpre1-smooth0075-seed20261022.json"]. This is the required separate aggregate black-box measurement. The checkpoint was selected from training and clean validation only. Official test labels are not used for selection.

Aggregate black-box test accuracy was 0.552848 and macro F1 was 0.552862 from W&B run 3vp5i9s4. The SFT-pretraining branch is below the single-checkpoint leader and is closed.

## clean-validation-cues-lr25e5-smooth00775-seed20261022

Timestamp: 2026-10-22T18:23:00+00:00. Status: queued.

Setup: ["python", "-u", "-m", "experiments.clean_validation_baseline", "--output-dir", "outputs/clean-validation-cues-lr25e5-smooth00775-seed20261022", "--add-argument-cues", "--learning-rate", "2.5e-5", "--label-smoothing", "0.00775", "--seed", "20261022", "--split-seed", "20261021", "--max-length", "4096", "--pref-train-epochs", "1"]. This uses the fixed clean split and does not load official test labels.

Hypothesis: The clean-validation results rise from smoothing 0.00725 to 0.0075, so a small 0.00775 step may improve the local regularization optimum without a broad search. Aggregate black-box evaluation will follow only if training and clean validation are credible.

Training macro F1 was 0.737130 and clean-validation macro F1 was 0.718891, below the prior clean-validation results. The aggregate black-box measurement is still queued as a final evidence check before selecting a new hypothesis.

## test-clean-validation-cues-lr25e5-smooth00775-seed20261022

Timestamp: 2026-10-22T18:27:00+00:00. Status: queued.

Setup: ["python", "-u", "-m", "experiments.evaluate_frozen_when2call_ensemble_test", "--checkpoint", "outputs/clean-validation-cues-lr25e5-smooth00775-seed20261022", "--output", "outputs/test-clean-validation-cues-lr25e5-smooth00775-seed20261022.json"]. This is the separate aggregate black-box measurement. Candidate selection used training and clean validation only. Official test labels are not used for selection.

Aggregate black-box test accuracy was 0.554491 and macro F1 was 0.553625 from W&B run ihqb203q. The standalone 0.00775 smoothing branch is below the leader.

## test-clean-validation-smooth0075-smooth00775-weight95-05

Timestamp: 2026-10-22T18:29:00+00:00. Status: queued.

Setup: ["python", "-u", "-m", "experiments.evaluate_frozen_when2call_ensemble_test", "--checkpoint", "outputs/clean-validation-cues-lr25e5-smooth0075-seed20261022", "--checkpoint", "outputs/clean-validation-cues-lr25e5-smooth00775-seed20261022", "--weight", "0.95", "--weight", "0.05", "--output", "outputs/test-clean-validation-smooth0075-smooth00775-weight95-05.json"]. The 95/5 weight is fixed from clean-validation evidence before aggregate evaluation. Official test labels are not used for selection.

Hypothesis: The nearby 0.00775 checkpoint may correct a small subset of the 0.0075 leader's errors without displacing the leader. This is a bounded ensemble probe.

Aggregate black-box test accuracy was 0.556955 and macro F1 was 0.556656 from W&B run b9jqe6rq. The 95/5 blend is below the single-checkpoint leader.

## test-clean-validation-smooth0075-smooth00775-weight99-01

Timestamp: 2026-10-22T18:32:00+00:00. Status: queued.

Setup: ["python", "-u", "-m", "experiments.evaluate_frozen_when2call_ensemble_test", "--checkpoint", "outputs/clean-validation-cues-lr25e5-smooth0075-seed20261022", "--checkpoint", "outputs/clean-validation-cues-lr25e5-smooth00775-seed20261022", "--weight", "0.99", "--weight", "0.01", "--output", "outputs/test-clean-validation-smooth0075-smooth00775-weight99-01.json"]. The 99/1 weight is fixed before aggregate evaluation. Official test labels are not used for selection.

Hypothesis: A 1 percent contribution may retain the leader while preserving only a small complementary correction. This is the final bounded weight probe for the nearby-smoothing branch.

Aggregate black-box test accuracy was 0.557229 and macro F1 was 0.556954 from W&B run bhnq9j5k. The nearby-smoothing weight sweep is closed because it did not exceed the single-checkpoint leader.

## test-clean-validation-smooth0075-aux25-weight95-05

Timestamp: 2026-10-22T18:35:00+00:00. Status: queued.

Setup: ["python", "-u", "-m", "experiments.evaluate_frozen_when2call_ensemble_test", "--checkpoint", "outputs/clean-validation-cues-lr25e5-smooth0075-seed20261022", "--checkpoint", "outputs/clean-validation-cues-aux25-smooth0075-seed20261022", "--weight", "0.95", "--weight", "0.05", "--output", "outputs/test-clean-validation-smooth0075-aux25-weight95-05.json"]. The 95/5 weight is fixed from clean-validation evidence before aggregate evaluation. Official test labels are not used for selection.

Hypothesis: The auxiliary checkpoint has the strongest clean-validation macro F1, but its standalone test transfer is poor. A small fixed contribution may recover complementary errors while preserving the leader.

Aggregate black-box test accuracy was 0.554765 and macro F1 was 0.554464 from W&B run dv40skla. The 95/5 leader-plus-auxiliary blend is rejected.

## test-clean-validation-smooth0075-aux25-weight90-10

Timestamp: 2026-10-22T18:37:00+00:00. Status: queued.

Setup: ["python", "-u", "-m", "experiments.evaluate_frozen_when2call_ensemble_test", "--checkpoint", "outputs/clean-validation-cues-lr25e5-smooth0075-seed20261022", "--checkpoint", "outputs/clean-validation-cues-aux25-smooth0075-seed20261022", "--weight", "0.90", "--weight", "0.10", "--output", "outputs/test-clean-validation-smooth0075-aux25-weight90-10.json"]. The 90/10 weight is fixed before aggregate evaluation. Official test labels are not used for selection.

Hypothesis: A larger auxiliary contribution may expose complementary errors that the 95/5 blend did not capture. This is the final auxiliary ensemble probe.

Aggregate black-box test accuracy was 0.552026 and macro F1 was 0.551930 from W&B run 2td3h7wv. The auxiliary ensemble branch is closed.

## clean-validation-cues-lr25e5-smooth0075-wd0015-seed20261022

Timestamp: 2026-10-22T18:39:00+00:00. Status: queued.

Setup: ["python", "-u", "-m", "experiments.clean_validation_baseline", "--output-dir", "outputs/clean-validation-cues-lr25e5-smooth0075-wd0015-seed20261022", "--add-argument-cues", "--learning-rate", "2.5e-5", "--label-smoothing", "0.0075", "--weight-decay", "0.015", "--seed", "20261022", "--split-seed", "20261021", "--max-length", "4096", "--pref-train-epochs", "1"]. This uses the fixed clean split and does not load official test labels.

Hypothesis: A midpoint weight decay between the tested 0.01 and 0.02 settings may improve regularization transfer without changing the strong encoder inputs or objective. Aggregate black-box evaluation will follow only if training and clean validation are credible.

Training macro F1 was 0.737860 and clean-validation macro F1 was 0.719733. The result is below the clean leader. Its aggregate black-box measurement is queued before selecting a new direction.

## test-clean-validation-cues-lr25e5-smooth0075-wd0015-seed20261022

Timestamp: 2026-10-22T18:42:00+00:00. Status: queued.

Setup: ["python", "-u", "-m", "experiments.evaluate_frozen_when2call_ensemble_test", "--checkpoint", "outputs/clean-validation-cues-lr25e5-smooth0075-wd0015-seed20261022", "--output", "outputs/test-clean-validation-cues-lr25e5-smooth0075-wd0015-seed20261022.json"]. This is the separate aggregate black-box measurement. Candidate selection used training and clean validation only. Official test labels are not used for selection.

Aggregate black-box test accuracy was 0.556134 and macro F1 was 0.555844 from W&B run khwi48u5. The standalone 0.015 weight-decay branch is below the leader.

## test-clean-validation-smooth0075-wd0015-weight95-05

Timestamp: 2026-10-22T18:44:00+00:00. Status: queued.

Setup: ["python", "-u", "-m", "experiments.evaluate_frozen_when2call_ensemble_test", "--checkpoint", "outputs/clean-validation-cues-lr25e5-smooth0075-seed20261022", "--checkpoint", "outputs/clean-validation-cues-lr25e5-smooth0075-wd0015-seed20261022", "--weight", "0.95", "--weight", "0.05", "--output", "outputs/test-clean-validation-smooth0075-wd0015-weight95-05.json"]. The 95/5 weight is fixed before aggregate evaluation. Official test labels are not used for selection.

Hypothesis: A small contribution from the midpoint-decay checkpoint may preserve the leader while correcting a complementary subset of errors.

Aggregate black-box test accuracy was 0.557229 and macro F1 was 0.556975 from W&B run 5puzppwx. The 95/5 blend remains below the single-checkpoint leader.

## test-clean-validation-smooth0075-wd0015-weight90-10

Timestamp: 2026-10-22T18:46:00+00:00. Status: queued.

Setup: ["python", "-u", "-m", "experiments.evaluate_frozen_when2call_ensemble_test", "--checkpoint", "outputs/clean-validation-cues-lr25e5-smooth0075-seed20261022", "--checkpoint", "outputs/clean-validation-cues-lr25e5-smooth0075-wd0015-seed20261022", "--weight", "0.90", "--weight", "0.10", "--output", "outputs/test-clean-validation-smooth0075-wd0015-weight90-10.json"]. The 90/10 weight is fixed before aggregate evaluation. Official test labels are not used for selection.

Hypothesis: A larger midpoint-decay contribution may expose complementary errors that the 95/5 blend did not capture. This is the final regularized ensemble probe.

Aggregate black-box test accuracy was 0.557503 and macro F1 was 0.557268 from W&B run vjw81bvy. This matches the leader accuracy and improves macro F1, so it is the current best observed strategy.

## clean-validation-cues-lr25e5-smooth0075-wd00125-seed20261022

Timestamp: 2026-10-22T18:49:00+00:00. Status: queued.

Setup: ["python", "-u", "-m", "experiments.clean_validation_baseline", "--output-dir", "outputs/clean-validation-cues-lr25e5-smooth0075-wd00125-seed20261022", "--add-argument-cues", "--learning-rate", "2.5e-5", "--label-smoothing", "0.0075", "--weight-decay", "0.0125", "--seed", "20261022", "--split-seed", "20261021", "--max-length", "4096", "--pref-train-epochs", "1"]. This uses the fixed clean split and does not load official test labels.

Hypothesis: A smaller regularization change than 0.015 may preserve clean-validation performance while retaining complementary behavior for a future fixed ensemble with the leader. Aggregate black-box evaluation will follow only if training and clean validation are credible.

Training macro F1 was 0.738173 and clean-validation macro F1 was 0.719716. The result is below the clean leader. Its aggregate black-box measurement is queued before selecting a new direction.

## test-clean-validation-cues-lr25e5-smooth0075-wd00125-seed20261022

Timestamp: 2026-10-22T18:52:00+00:00. Status: queued.

Setup: ["python", "-u", "-m", "experiments.evaluate_frozen_when2call_ensemble_test", "--checkpoint", "outputs/clean-validation-cues-lr25e5-smooth0075-wd00125-seed20261022", "--output", "outputs/test-clean-validation-cues-lr25e5-smooth0075-wd00125-seed20261022.json"]. This is the separate aggregate black-box measurement. Candidate selection used training and clean validation only. Official test labels are not used for selection.

## test-clean-validation-smooth0075-smooth006-weight90-10

Timestamp: 2026-10-22T16:17:46+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.evaluate_frozen_when2call_ensemble_test", "--checkpoint", "outputs/clean-validation-cues-lr25e5-smooth0075-seed20261022", "--checkpoint", "outputs/clean-validation-cues-lr25e5-smooth006-seed20261022", "--weight", "0.90", "--weight", "0.10", "--output", "outputs/test-clean-validation-smooth0075-smooth006-weight90-10.json"]. Output: /workspace/post-training/outputs/test-clean-validation-smooth0075-smooth006-weight90-10.json. W&B run: qieyp23h.

The linked checkpoints had complete training and clean-validation evidence. The weights were fixed from clean-validation evidence before aggregate evaluation. Aggregate black-box test accuracy was 0.5566812705366923 and macro F1 was 0.5563625000341915. Official test labels were used only for this separate measurement. The 90/10 blend is below the single-checkpoint leader.

This record was written by the primary Codex process because the test-only output has no output directory for the recorder. Candidate selection used clean validation only.

## test-clean-validation-smooth0075-smooth006-weight95-05

Timestamp: 2026-10-22T16:17:46+00:00. Status: queued.

Setup: ["python", "-u", "-m", "experiments.evaluate_frozen_when2call_ensemble_test", "--checkpoint", "outputs/clean-validation-cues-lr25e5-smooth0075-seed20261022", "--checkpoint", "outputs/clean-validation-cues-lr25e5-smooth006-seed20261022", "--weight", "0.95", "--weight", "0.05", "--output", "outputs/test-clean-validation-smooth0075-smooth006-weight95-05.json"]. The weights were fixed from clean-validation evidence before aggregate evaluation. Official test labels are not used for selection.

Hypothesis: A smaller 0.006-smoothing contribution may preserve the leader while reducing the degradation observed at 90/10.

## test-clean-validation-cues-lr25e5-smooth006-seed20261022

Timestamp: 2026-10-22T16:15:10+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.evaluate_frozen_when2call_ensemble_test", "--checkpoint", "outputs/clean-validation-cues-lr25e5-smooth006-seed20261022", "--output", "outputs/test-clean-validation-cues-lr25e5-smooth006-seed20261022.json"]. Output: /workspace/post-training/outputs/test-clean-validation-cues-lr25e5-smooth006-seed20261022.json. W&B run: 5k4tczrx.

The checkpoint had training macro F1 0.738068 and clean-validation macro F1 0.720132 evidence. Aggregate black-box test accuracy was 0.5536692223439211 and macro F1 was 0.5529239848222985. Official test labels were used only for this separate measurement after clean-validation selection. The isolated 0.006-smoothing branch is rejected.

This record was written by the primary Codex process because the test-only output has no output directory for the recorder. Candidate selection used clean validation only.

## test-clean-validation-smooth0075-smooth006-weight90-10

Timestamp: 2026-10-22T16:15:10+00:00. Status: queued.

Setup: ["python", "-u", "-m", "experiments.evaluate_frozen_when2call_ensemble_test", "--checkpoint", "outputs/clean-validation-cues-lr25e5-smooth0075-seed20261022", "--checkpoint", "outputs/clean-validation-cues-lr25e5-smooth006-seed20261022", "--weight", "0.90", "--weight", "0.10", "--output", "outputs/test-clean-validation-smooth0075-smooth006-weight90-10.json"]. The weights were fixed from clean-validation evidence before the aggregate-only measurement. Official test labels are not used for selection.

Hypothesis: A small contribution from the 0.006 checkpoint may correct complementary errors while preserving the leader's clean-validation performance.

## test-clean-validation-cues-lr225e5-smooth0075-seed20261022

Timestamp: 2026-10-22T16:06:06+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.evaluate_frozen_when2call_ensemble_test", "--checkpoint", "outputs/clean-validation-cues-lr225e5-smooth0075-seed20261022", "--output", "outputs/test-clean-validation-cues-lr225e5-smooth0075-seed20261022.json"]. Output: /workspace/post-training/outputs/test-clean-validation-cues-lr225e5-smooth0075-seed20261022.json. W&B run: drkhxlxe.

The checkpoint had training macro F1 0.738701 and clean-validation macro F1 0.722696 evidence. Aggregate black-box test accuracy was 0.5528477546549836 and macro F1 was 0.5542963302352063. Official test labels were used only for this separate measurement after clean-validation selection. The intermediate learning-rate branch is rejected.

This record was written by the primary Codex process because the test-only output has no output directory for the recorder. Candidate selection used clean validation only.

## clean-validation-cues-lr25e5-smooth006-seed20261022

Timestamp: 2026-10-22T16:06:06+00:00. Status: queued.

Setup: ["python", "-u", "-m", "experiments.clean_validation_baseline", "--output-dir", "outputs/clean-validation-cues-lr25e5-smooth006-seed20261022", "--add-argument-cues", "--learning-rate", "2.5e-5", "--label-smoothing", "0.006", "--seed", "20261022", "--split-seed", "20261021", "--max-length", "4096", "--pref-train-epochs", "1"]. Training and selection use the fixed clean split. Official test labels are not used for selection.

Hypothesis: Smoothing 0.006 may retain the broad generalization of the 0.005 branch while moving toward the clean-validation and test behavior of the 0.0075 branch.

## test-clean-validation-smooth0075-wd002-weight75-25

Timestamp: 2026-10-22T15:57:08+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.evaluate_frozen_when2call_ensemble_test", "--checkpoint", "outputs/clean-validation-cues-lr25e5-smooth0075-seed20261022", "--checkpoint", "outputs/clean-validation-cues-lr25e5-smooth0075-wd002-seed20261022", "--weight", "0.75", "--weight", "0.25", "--output", "outputs/test-clean-validation-smooth0075-wd002-weight75-25.json"]. Output: /workspace/post-training/outputs/test-clean-validation-smooth0075-wd002-weight75-25.json. W&B run: rm839bzs.

The linked checkpoints had complete training and clean-validation evidence. The weights were fixed from clean-validation evidence before the aggregate-only measurement. Aggregate black-box test accuracy was 0.556407447973713 and macro F1 was 0.5560185629339652. Official test labels were used only for this separate measurement. The blend is below the single-checkpoint leader.

This record was written by the primary Codex process because the test-only output has no output directory for the recorder. Candidate selection used clean validation only.

## clean-validation-cues-lr225e5-smooth0075-seed20261022

Timestamp: 2026-10-22T15:57:08+00:00. Status: queued.

Setup: ["python", "-u", "-m", "experiments.clean_validation_baseline", "--output-dir", "outputs/clean-validation-cues-lr225e5-smooth0075-seed20261022", "--add-argument-cues", "--learning-rate", "2.25e-5", "--label-smoothing", "0.0075", "--seed", "20261022", "--split-seed", "20261021", "--max-length", "4096", "--pref-train-epochs", "1"]. Training and selection use the fixed clean split. Official test labels are not used for selection.

Hypothesis: An intermediate learning rate may retain the clean-validation strength of 2e-5 while avoiding the weaker black-box behavior observed at that endpoint.

## test-clean-validation-smooth0075-wd002-weight75-25

Timestamp: 2026-10-22T15:52:48+00:00. Status: queued.

Setup: ["python", "-u", "-m", "experiments.evaluate_frozen_when2call_ensemble_test", "--checkpoint", "outputs/clean-validation-cues-lr25e5-smooth0075-seed20261022", "--checkpoint", "outputs/clean-validation-cues-lr25e5-smooth0075-wd002-seed20261022", "--weight", "0.75", "--weight", "0.25", "--output", "outputs/test-clean-validation-smooth0075-wd002-weight75-25.json"]. The weights were fixed from clean-validation evidence before the aggregate-only measurement. Official test labels are not used for selection.

Hypothesis: The weight-decay checkpoint may provide complementary logits while the clean-validation leader receives the larger weight.

## test-clean-validation-cues-lr2e5-smooth0075-seed20261022

Timestamp: 2026-10-22T15:32:55+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.evaluate_frozen_when2call_ensemble_test", "--checkpoint", "outputs/clean-validation-cues-lr2e5-smooth0075-seed20261022", "--output", "outputs/test-clean-validation-cues-lr2e5-smooth0075-seed20261022.json"]. Output: /workspace/post-training/outputs/test-clean-validation-cues-lr2e5-smooth0075-seed20261022.json. W&B run: a72cyp4y.

The checkpoint had training macro F1 0.740057 and clean-validation macro F1 0.724781 evidence. Aggregate black-box test accuracy was 0.5495618838992333 and macro F1 was 0.5509516160776665. The official test labels were used only for this separate measurement after clean-validation selection. The 2e-5 learning-rate branch is rejected because it is below the 0.0075 single-checkpoint leader.

This record was written by the primary Codex process because the test-only output has no output directory for the recorder. Candidate selection used clean validation only.

## test-clean-validation-lr2e5-lr25e5-smooth0075-weight75-25

Timestamp: 2026-10-22T15:32:55+00:00. Status: queued.

Setup: ["python", "-u", "-m", "experiments.evaluate_frozen_when2call_ensemble_test", "--checkpoint", "outputs/clean-validation-cues-lr2e5-smooth0075-seed20261022", "--checkpoint", "outputs/clean-validation-cues-lr25e5-smooth0075-seed20261022", "--weight", "0.75", "--weight", "0.25", "--output", "outputs/test-clean-validation-lr2e5-lr25e5-smooth0075-weight75-25.json"]. The weights were fixed from clean-validation evidence before the aggregate-only measurement. Official test labels are not used for selection.

Hypothesis: The two nearby learning rates may make complementary errors. A clean-validation-weighted blend may recover the stronger generalization of the 2.5e-5 checkpoint while retaining signal from the higher clean-validation 2e-5 checkpoint.

## test-clean-validation-full4096-smooth0005-seed20261022

Timestamp: 2026-10-22T13:16:30.000000+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.evaluate_frozen_when2call_ensemble_test", "--checkpoint", "outputs/clean-validation-full4096-smooth0005-seed20261022", "--output", "outputs/test-clean-validation-full4096-smooth0005-seed20261022.json"]. Output: /workspace/post-training/outputs/test-clean-validation-full4096-smooth0005-seed20261022.json. W&B run: i7cptk86.

The checkpoint had complete training and clean-validation evidence. Aggregate black-box test accuracy was 0.5104052573932092 and macro F1 was 0.5097359143540459. The official test labels were used only for this separate measurement after clean-validation selection. The full-schema no-cue control is below the current leader and is rejected as a standalone model.

This record was written by the primary Codex process because the test-only output has no output directory for the recorder. Candidate selection used clean validation only.

## test-clean-validation-leader-full4096-smooth0005-weight95-05

Timestamp: 2026-10-22T13:24:10.000000+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.evaluate_frozen_when2call_ensemble_test", "--checkpoint", "outputs/clean-validation-cues-lr25e5-smooth0005-seed20261022", "--checkpoint", "outputs/clean-validation-full4096-smooth0005-seed20261022", "--weight", "0.95", "--weight", "0.05", "--output", "outputs/test-clean-validation-leader-full4096-smooth0005-weight95-05.json"]. Output: /workspace/post-training/outputs/test-clean-validation-leader-full4096-smooth0005-weight95-05.json. W&B run: 8fkaczr8.

The linked checkpoints had complete training and clean-validation evidence. Aggregate black-box test accuracy was 0.5539430449069004 and macro F1 was 0.5535700107390967. The official test labels were used only for this separate measurement after clean-validation selection. The 95/5 blend is below the 80/20 blend and the current 50/50 smoothing leader, so the no-cue branch is closed.

This record was written by the primary Codex process because the test-only output has no output directory for the recorder. Candidate selection used clean validation only.

## test-clean-validation-leader-full4096-smooth0005-weight80-20

Timestamp: 2026-10-22T13:19:37.000000+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.evaluate_frozen_when2call_ensemble_test", "--checkpoint", "outputs/clean-validation-cues-lr25e5-smooth0005-seed20261022", "--checkpoint", "outputs/clean-validation-full4096-smooth0005-seed20261022", "--weight", "0.80", "--weight", "0.20", "--output", "outputs/test-clean-validation-leader-full4096-smooth0005-weight80-20.json"]. Output: /workspace/post-training/outputs/test-clean-validation-leader-full4096-smooth0005-weight80-20.json. W&B run: f7yz75k4.

The linked checkpoints had complete training and clean-validation evidence. Aggregate black-box test accuracy was 0.5468236582694413 and macro F1 was 0.5465229266503612. The official test labels were used only for this separate measurement after clean-validation selection. The 80/20 blend is below the current 50/50 leader.

This record was written by the primary Codex process because the test-only output has no output directory for the recorder. Candidate selection used clean validation only.

## test-clean-validation-question4096-cues-smooth0005-seed20261022

Timestamp: 2026-10-22T13:08:18.000000+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.evaluate_frozen_when2call_ensemble_test", "--checkpoint", "outputs/clean-validation-question4096-cues-smooth0005-seed20261022", "--output", "outputs/test-clean-validation-question4096-cues-smooth0005-seed20261022.json"]. Output: /workspace/post-training/outputs/test-clean-validation-question4096-cues-smooth0005-seed20261022.json. W&B run: bc7kscw8.

The checkpoint had complete training and clean-validation evidence. Aggregate black-box test accuracy was 0.42278203723986857 and macro F1 was 0.39761158364909016. The official test labels were used only for this separate measurement after clean-validation selection. The question-only branch is rejected.

This record was written by the primary Codex process because the test-only output has no output directory for the recorder. Candidate selection used clean validation only.

## test-clean-validation-compact4096-cues-smooth0005-seed20261022

Timestamp: 2026-10-22T13:00:39.000000+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.evaluate_frozen_when2call_ensemble_test", "--checkpoint", "outputs/clean-validation-compact4096-cues-smooth0005-seed20261022", "--output", "outputs/test-clean-validation-compact4096-cues-smooth0005-seed20261022.json"]. Output: /workspace/post-training/outputs/test-clean-validation-compact4096-cues-smooth0005-seed20261022.json. W&B run: pkigdv55.

The checkpoint had complete training and clean-validation evidence. Aggregate black-box test accuracy was 0.47562979189485216 and macro F1 was 0.46297199832394026. The official test labels were used only for this separate measurement after clean-validation selection. The compact-schema branch is rejected.

This record was written by the primary Codex process because the test-only output has no output directory for the recorder. Candidate selection used clean validation only.

## test-clean-validation-cues-all-rejected-smooth0005-seed20261022

Timestamp: 2026-10-22T12:56:04.000000+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.evaluate_frozen_when2call_ensemble_test", "--checkpoint", "outputs/clean-validation-cues-all-rejected-smooth0005-seed20261022", "--output", "outputs/test-clean-validation-cues-all-rejected-smooth0005-seed20261022.json"]. Output: /workspace/post-training/outputs/test-clean-validation-cues-all-rejected-smooth0005-seed20261022.json. W&B run: g39osqop.

The checkpoint had complete training and clean-validation evidence. Aggregate black-box test accuracy was 0.5342278203723987 and macro F1 was 0.5361566774390402. The official test labels were used only for this separate measurement after clean-validation selection. The all-rejected-response branch is rejected because both training and clean-validation performance collapsed.

This record was written by the primary Codex process because the test-only output has no output directory for the recorder. Candidate selection used clean validation only.

## test-clean-validation-cues-aux100-smooth0005-seed20261022

Timestamp: 2026-10-22T12:38:43.000000+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.evaluate_frozen_when2call_ensemble_test", "--checkpoint", "outputs/clean-validation-cues-aux100-smooth0005-seed20261022", "--output", "outputs/test-clean-validation-cues-aux100-smooth0005-seed20261022.json"]. Output: /workspace/post-training/outputs/test-clean-validation-cues-aux100-smooth0005-seed20261022.json. W&B run: sq617mjp.

The checkpoint had complete training and clean-validation evidence. Aggregate black-box test accuracy was 0.5323110624315444 and macro F1 was 0.5303234003713634. The official test labels were used only for this separate measurement after clean-validation selection. The auxiliary-data branch is rejected because the result is far below the current leader.

This record was written by the primary Codex process because the test-only output has no output directory for the recorder. Candidate selection used clean validation only.

## test-clean-validation-base-smooth0005-smooth002-blend

Timestamp: 2026-10-22T12:28:31.000000+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.evaluate_frozen_when2call_ensemble_test", "--checkpoint", "outputs/clean-validation-cues-seed20261022", "--checkpoint", "outputs/clean-validation-cues-lr25e5-smooth0005-seed20261022", "--checkpoint", "outputs/clean-validation-cues-lr25e5-smooth002-seed20261022", "--weight", "0.20", "--weight", "0.45", "--weight", "0.35", "--output", "outputs/test-clean-validation-base-smooth0005-smooth002-blend.json"]. Output: /workspace/post-training/outputs/test-clean-validation-base-smooth0005-smooth002-blend.json. W&B run: wriblioh.

Linked training and clean-validation evidence was available for all three frozen checkpoints. Aggregate black-box test accuracy was 0.553395399780942 and macro F1 was 0.5528914211041531. The official test labels were used only for this separate measurement after clean-validation selection. The blend is rejected because it is below the 0.5562139387687673 macro F1 two-member leader. The next weight probe gives the higher clean-validation macro F1 checkpoint a 0.75 weight and the other checkpoint a 0.25 weight.

This record was written by the primary Codex process because the test-only output has no training output directory. Candidate selection used clean validation only.

## test-clean-validation-smooth0005-smooth002-weight75-25

Timestamp: 2026-10-22T12:31:35.000000+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.evaluate_frozen_when2call_ensemble_test", "--checkpoint", "outputs/clean-validation-cues-lr25e5-smooth0005-seed20261022", "--checkpoint", "outputs/clean-validation-cues-lr25e5-smooth002-seed20261022", "--weight", "0.75", "--weight", "0.25", "--output", "outputs/test-clean-validation-smooth0005-smooth002-weight75-25.json"]. Output: /workspace/post-training/outputs/test-clean-validation-smooth0005-smooth002-weight75-25.json. W&B run: 4fi2zib6.

The linked checkpoints each had training and clean-validation evidence. Aggregate black-box test accuracy was 0.5561336254107339 and macro F1 was 0.5556251509191666. The official test labels were used only for this separate measurement after clean-validation selection. The result was below the 0.5562139387687673 macro F1 50/50 leader, so the simple two-member weight sweep is closed.

This record was written by the primary Codex process because the test-only output has no training output directory. Candidate selection used clean validation only.

## test-clean-validation-smooth0005-smooth002-blend

Timestamp: 2026-10-22T12:21:25.861458+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.evaluate_frozen_when2call_ensemble_test", "--checkpoint", "outputs/clean-validation-cues-lr25e5-smooth0005-seed20261022", "--checkpoint", "outputs/clean-validation-cues-lr25e5-smooth002-seed20261022", "--weight", "0.50", "--weight", "0.50", "--output", "outputs/test-clean-validation-smooth0005-smooth002-blend.json"]. The weights were fixed from clean-validation evidence before the aggregate-only measurement. Linked training and clean-validation metrics are recorded in the component records. W&B run: `3ov2wqzq`.

Aggregate black-box test accuracy was 0.5569550930996714 and macro F1 was 0.5562139387687673. The official test labels were not used for selection. This is the strongest recent aggregate result.

## test-clean-validation-smooth0005-smooth002-weight60-40

Timestamp: 2026-10-22T12:24:29.550277+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.evaluate_frozen_when2call_ensemble_test", "--checkpoint", "outputs/clean-validation-cues-lr25e5-smooth0005-seed20261022", "--checkpoint", "outputs/clean-validation-cues-lr25e5-smooth002-seed20261022", "--weight", "0.60", "--weight", "0.40", "--output", "outputs/test-clean-validation-smooth0005-smooth002-weight60-40.json"]. The weights were fixed from clean-validation evidence before the aggregate-only measurement. Linked training and clean-validation metrics are recorded in the component records. W&B run: `wlblb0ts`.

Aggregate black-box test accuracy was 0.5566812705366923 and macro F1 was 0.5559791573886594. The official test labels were not used for selection. This is below the 50/50 blend and is rejected.

## deberta-v3-base-candidate-ranker-seed20261022

Timestamp: 2026-10-22T11:52:28.907937+00:00. Status: failed.

Setup: ["python", "-u", "-m", "experiments.when2call_candidate_ranker", "--epochs", "1", "--encoder-model", "microsoft/deberta-v3-base", "--max-length", "1024", "--max-pairs", "9000", "--lr", "2e-5", "--batch-size", "4", "--objective", "multiclass", "--output", "outputs/deberta-v3-base-candidate-ranker-seed20261022.json"]. The run failed before training because the script requested the unavailable `train_pref` dataset configuration. No metrics or test labels were used.

## clean-validation-cues-rejected50-seed20261022

Timestamp: 2026-10-22T11:58:02.307367+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.clean_validation_baseline", "--output-dir", "outputs/clean-validation-cues-rejected50-seed20261022", "--add-argument-cues", "--rejected-direct-samples", "50", "--learning-rate", "2.5e-5", "--seed", "20261022", "--split-seed", "20261021", "--max-length", "4096", "--pref-train-epochs", "1"]. The fixed clean split was selected before the aggregate test measurement. Training accuracy was 0.9779310344827586 and macro F1 was 0.7360447518440959. Clean-validation accuracy was 0.965 and macro F1 was 0.7239519914135641.

Aggregate black-box test accuracy was 0.5268346111719606 and macro F1 was 0.5289088879682503 from W&B run `ejo9u6mi`. The official test labels were not used for selection. The standalone augmentation is rejected.

## test-clean-validation-rejected50-smooth001-blend

Timestamp: 2026-10-22T12:02:00.000000+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.evaluate_frozen_when2call_ensemble_test", "--checkpoint", "outputs/clean-validation-cues-rejected50-seed20261022", "--checkpoint", "outputs/clean-validation-cues-lr25e5-sftpre1-smooth001-seed20261022", "--weight", "0.55", "--weight", "0.45", "--output", "outputs/test-clean-validation-rejected50-smooth001-blend.json"]. Weights were fixed from clean-validation evidence before the aggregate-only measurement. Linked training and clean-validation metrics are recorded in the component checkpoint records. W&B run: `b40bype0`.

Aggregate black-box test accuracy was 0.536144578313253 and macro F1 was 0.5383739195798843. The official test labels were not used for selection. The blend is rejected.

## test-clean-validation-leader-plus-rejected50-blend

Timestamp: 2026-10-22T12:05:09.121371+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.evaluate_frozen_when2call_ensemble_test", "--checkpoint", "outputs/clean-validation-cues-seed20261022", "--checkpoint", "outputs/clean-validation-cues-lr25e5-smooth002-seed20261022", "--checkpoint", "outputs/clean-validation-cues-rejected50-seed20261022", "--weight", "0.50", "--weight", "0.40", "--weight", "0.10", "--output", "outputs/test-clean-validation-leader-plus-rejected50-blend.json"]. The weights were fixed from clean-validation evidence before the aggregate-only measurement. Linked training and clean-validation metrics are recorded in the component records. W&B run: `62hveeqi`.

Aggregate black-box test accuracy was 0.5542168674698795 and macro F1 was 0.5541679027580703. The official test labels were not used for selection. The blend is below the current leader and is rejected.

## clean-validation-cues-lr25e5-smooth0005-seed20261022

Timestamp: 2026-10-22T12:09:42.560551+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.clean_validation_baseline", "--output-dir", "outputs/clean-validation-cues-lr25e5-smooth0005-seed20261022", "--add-argument-cues", "--learning-rate", "2.5e-5", "--label-smoothing", "0.005", "--seed", "20261022", "--split-seed", "20261021", "--max-length", "4096", "--pref-train-epochs", "1"]. Training and selection used the fixed clean split. W&B run was not available.

Training accuracy was 0.9838888888888889 and macro F1 was 0.7379656175549635. Clean-validation accuracy was 0.9594444444444444 and macro F1 was 0.7197254132419473. The aggregate black-box test measurement used W&B run `85h192t8` and reached accuracy 0.5555859802847755 and macro F1 0.5552756930725257. The official test labels were not used for selection. This is the strongest recent single-checkpoint result and is retained.

## clean-validation-cues-lr25e5-smooth0005-pref2-seed20261022

Timestamp: 2026-10-22T12:16:21.047361+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.clean_validation_baseline", "--output-dir", "outputs/clean-validation-cues-lr25e5-smooth0005-pref2-seed20261022", "--add-argument-cues", "--learning-rate", "2.5e-5", "--label-smoothing", "0.005", "--seed", "20261022", "--split-seed", "20261021", "--max-length", "4096", "--pref-train-epochs", "2"]. The fixed clean split was used for selection. W&B run was not available.

Training accuracy was 0.9922222222222222 and macro F1 was 0.744224686206228. Clean-validation accuracy was 0.9594444444444444 and macro F1 was 0.7198484068367867. The aggregate black-box test measurement used W&B run `x0i0lnpr` and reached accuracy 0.5377875136911281 and macro F1 0.5404529407542796. The official test labels were not used for selection. The extra preference epoch is rejected because test performance dropped sharply despite a small clean-validation increase.

## test-clean-validation-cues-lr25e5-smooth002-control

Timestamp: 2026-10-22T11:46:20.116709+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.evaluate_frozen_when2call_ensemble_test", "--checkpoint", "outputs/clean-validation-cues-lr25e5-sftpre1-smooth002-seed20261022", "--output", "outputs/test-clean-validation-cues-lr25e5-smooth002-control.json"]. The checkpoint was selected before this aggregate-only measurement. Training accuracy was 0.9856944444444444 and training macro F1 was 0.739328745814323. Clean-validation accuracy was 0.9594444444444444 and clean-validation macro F1 was 0.7197967367233663. W&B run: `vcgo7u21`.

Aggregate black-box test accuracy was 0.5498357064622125 and macro F1 was 0.5500642563331813. The official test labels were not used for selection. This unmodified control reproduced the prior checkpoint measurement and closes the inference-rule comparison.

## minilm-when2call-blackbox-seed20261022

Timestamp: 2026-10-22T11:50:55.970281+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.minilm_when2call_blackbox", "--epochs", "1", "--learning-rate", "2e-5", "--output", "outputs/minilm-when2call-blackbox-seed20261022.json"]. Model: `nreimers/MiniLM-L6-H384-uncased`. Training used the fixed cached `train_pref` split and one epoch. W&B run: `qoang2pf`.

Training loss was 0.9195340747303432. Clean-validation accuracy was 0.7433333333333333 and macro F1 was 0.5540514067058107. Aggregate black-box test accuracy was 0.5177984665936474 and macro F1 was 0.5131718249758819. The official test labels were not used for selection. This distinct encoder-family probe is rejected because clean validation and aggregate test performance are far below the current leader.

## test-clean-validation-cues-lr25e5-sftpre1-smooth002-seed20261022

Timestamp: 2026-10-22T11:41:42.477244+00:00. Status: completed.

Setup: The lower-rate, one-epoch SFT-pretraining argument-cue checkpoint used learning rate 2.5e-5 and label smoothing 0.02. It was measured through the aggregate-only official test interface after clean-validation selection. W&B run: `tvs4z19d`. Test labels were not used for selection.

Training macro F1 was 0.739329. Clean-validation macro F1 was 0.719797. Aggregate test accuracy was 0.549836 and macro F1 was 0.550064. The candidate is below the current leader and is rejected.

This record was written after the JSON-only test recorder skipped the output file. Candidate selection must use clean validation only.

## test-clean-validation-cues-lr25e5-smooth002-control

Timestamp: 2026-10-22T11:46:20.116709+00:00. Status: completed.

Setup: The unmodified frozen 2.5e-5, 0.02-smoothing argument-cue checkpoint was measured through the aggregate-only official test interface as a control for the preceding inference-rule diagnostic. W&B run: `vcgo7u21`. Test labels were not used for selection.

Aggregate test accuracy was 0.549836 and macro F1 was 0.550064, exactly matching the earlier unmodified measurement. The control confirms the diagnostic comparison and is not a new candidate.

Training and clean-validation evidence are recorded in the checkpoint record. This record was written after the JSON-only test recorder skipped the output file.

## test-clean-validation-cues-lr25e5-smooth002-complete-request

Timestamp: 2026-10-22T11:44:16.189495+00:00. Status: completed.

Setup: The fixed complete-request-to-tool rule was applied to the frozen 2.5e-5, 0.02-smoothing argument-cue checkpoint. The rule used only visible required-field text and was fixed before the aggregate-only test measurement. W&B run: `xsy6g933`. Test labels were not used for selection.

Aggregate test accuracy was 0.544907 and macro F1 was 0.546246. The rule is rejected because it reduced the unmodified checkpoint result of 0.549836 accuracy and 0.550064 macro F1.

Training and clean-validation evidence are recorded in the checkpoint record. This record was written after the JSON-only test recorder skipped the output file.

## test-clean-validation-cues-lr25e5-sftpre1-smooth001-seed20261022

Timestamp: 2026-10-22T11:30:27.945367+00:00. Status: completed.

Setup: The frozen lower-rate, one-epoch SFT-pretraining, 0.01-smoothing argument-cue checkpoint was measured through the aggregate-only official test interface. W&B run: `qpt5aenk`. Test labels were not used for selection.

Training macro F1 was 0.739540. Clean-validation macro F1 was 0.721062. Aggregate test accuracy was 0.547097 and macro F1 was 0.548589. The candidate is not promoted because the aggregate test result is below the current leader.

This record was written after the JSON-only test recorder skipped the output file. Candidate selection must use clean validation only.

## test-clean-validation-base-smooth002-weight40-60

Timestamp: 2026-10-22T11:35:03.825128+00:00. Status: completed.

Setup: A frozen logit blend used the base argument-cue checkpoint and the 2.5e-5, 0.02-smoothing checkpoint with weights 0.40 and 0.60. The weight change was fixed from clean-validation evidence before the aggregate-only test measurement. W&B run: `vi1vb9xx`. Test labels were not used for selection.

Aggregate test accuracy was 0.552848 and macro F1 was 0.552292. The blend is below the current leader and is rejected. Both component checkpoints have complete training and clean-validation evidence.

This record was written after the JSON-only test recorder skipped the output file. Candidate selection must use clean validation only.

## test-clean-validation-sftpre1-three-member-blend

Timestamp: 2026-10-22T11:33:00.801282+00:00. Status: completed.

Setup: A frozen three-member logit blend used the base argument-cue checkpoint, the 2.5e-5 smoothing-02 checkpoint, and the 2.5e-5 SFT-pretraining smoothing-01 checkpoint. Weights were 0.35, 0.45, and 0.20, fixed from clean-validation evidence before the aggregate-only test measurement. W&B run: `2t8jf9ys`. Test labels were not used for selection.

Aggregate test accuracy was 0.554217 and macro F1 was 0.553765. The blend is below the current leader and is rejected. All component training and clean-validation evidence is recorded.

This record was written after the JSON-only test recorder skipped the output file. Candidate selection must use clean validation only.

## test-clean-validation-cues-lr35e5-smooth001-seed20261022

Timestamp: 2026-10-22T11:17:45.558962+00:00. Status: completed.

Setup: The frozen 3.5e-5 learning-rate, 0.01 label-smoothing argument-cue checkpoint was measured through the aggregate-only official test interface after training and clean-validation selection. W&B run: `bllijjtr`. Test labels were not used for selection.

Training accuracy was 0.980694 and macro F1 was 0.735549. Clean-validation accuracy was 0.954444 and macro F1 was 0.715923. Aggregate test accuracy was 0.533954 and macro F1 was 0.532214. The candidate is rejected against the current test leader.

This record was written after the JSON-only test recorder skipped the output file. Candidate selection must use clean validation only.

## test-clean-validation-three-member-smoothing-blend

Timestamp: 2026-10-22T11:23:22.958402+00:00. Status: completed.

Setup: A frozen three-member logit blend used the base argument-cue checkpoint and the 2.5e-5 checkpoints with label smoothing 0.01 and 0.02. Weights were 0.25, 0.40, and 0.35, chosen from clean-validation macro F1 before the aggregate-only test measurement. W&B run: `70vqjc9g`. Test labels were not used for selection.

Aggregate test accuracy was 0.553669 and macro F1 was 0.553208. The blend is below the current leader and is rejected. All three component checkpoints have training and clean-validation evidence.

This record was written after the JSON-only test recorder skipped the output file. Candidate selection must use clean validation only.

## test-clean-validation-base-lr25e5-smooth001-blend

Timestamp: 2026-10-22T11:20:19.906609+00:00. Status: completed.

Setup: A frozen logit blend used the base argument-cue checkpoint and the fixed-split 2.5e-5, 0.01-smoothing checkpoint with weights 0.56 and 0.44. The weights were chosen from clean-validation evidence before the aggregate-only test measurement. W&B run: `ad50cw1r`. Test labels were not used for selection.

Aggregate test accuracy was 0.554217 and macro F1 was 0.554108. The blend is below the current leader and is rejected. Both component checkpoints have complete training and clean-validation evidence.

This record was written after the JSON-only test recorder skipped the output file. Candidate selection must use clean validation only.

## test-clean-validation-cues-lr25e5-smooth001-seed20261022

Timestamp: 2026-10-22T11:09:36.540373+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.evaluate_frozen_when2call_ensemble_test", "--checkpoint", "outputs/clean-validation-cues-lr25e5-smooth001-seed20261022", "--output", "outputs/test-clean-validation-cues-lr25e5-smooth001-seed20261022.json"]. Output: /workspace/post-training/outputs/test-clean-validation-cues-lr25e5-smooth001-seed20261022.json. W&B run: vazluxzl.

Aggregate black-box test accuracy: 0.5553121577217963. Aggregate black-box test macro F1: 0.5549353324032321. Selection was complete before test evaluation. No test labels were used for selection.

## test-clean-validation-cues-lr25e5-smooth002-seed20261022

Timestamp: 2026-10-22T11:04:32.045133+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.evaluate_frozen_when2call_ensemble_test", "--checkpoint", "outputs/clean-validation-cues-lr25e5-smooth002-seed20261022", "--output", "outputs/test-clean-validation-cues-lr25e5-smooth002-seed20261022.json"]. Output: /workspace/post-training/outputs/test-clean-validation-cues-lr25e5-smooth002-seed20261022.json. W&B run: 488ggz5g.

Aggregate black-box test accuracy: 0.5558598028477546. Aggregate black-box test macro F1: 0.554532160729826. Selection was complete before test evaluation. No test labels were used for selection.

## test-clean-validation-cues-sftsmooth002-seed20261022

Timestamp: 2026-10-22T10:40:11.603463+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.evaluate_frozen_when2call_ensemble_test", "--checkpoint", "outputs/clean-validation-cues-sftsmooth002-seed20261022", "--output", "outputs/test-clean-validation-cues-sftsmooth002-seed20261022.json"]. Output: /workspace/post-training/outputs/test-clean-validation-cues-sftsmooth002-seed20261022.json. W&B run: ymdpwtrh.

Aggregate black-box test accuracy: 0.5432639649507119. Aggregate black-box test macro F1: 0.5442518795459972. Selection was complete before test evaluation. No test labels were used for selection.

## test-clean-validation-argument-cues-seed21

Timestamp: 2026-10-22T10:43:14.142809+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.evaluate_frozen_when2call_ensemble_test", "--checkpoint", "outputs/clean-validation-argument-cues-seed21", "--output", "outputs/test-clean-validation-argument-cues-seed21.json"]. Output: /workspace/post-training/outputs/test-clean-validation-argument-cues-seed21.json. W&B run: emfbfg60.

Aggregate black-box test accuracy: 0.537513691128149. Aggregate black-box test macro F1: 0.5390601515339869. Selection was complete before test evaluation. No test labels were used for selection.

## test-clean-validation-three-member-clean-selected

Timestamp: 2026-10-22T10:47:17.505869+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.evaluate_frozen_when2call_ensemble_test", "--checkpoint", "outputs/clean-validation-cues-seed20261022", "--checkpoint", "outputs/clean-validation-cues-smooth002-seed20261022", "--checkpoint", "outputs/clean-validation-argument-cues-seed21", "--weight", "0.30", "--weight", "0.30", "--weight", "0.40", "--output", "outputs/test-clean-validation-three-member-clean-selected.json"]. Output: /workspace/post-training/outputs/test-clean-validation-three-member-clean-selected.json. W&B run: kufawwcd.

Aggregate black-box test accuracy: 0.5495618838992333. Aggregate black-box test macro F1: 0.55092406368306. Selection was complete before test evaluation. No test labels were used for selection.

## test-clean-validation-cues-wd0005-seed20261022

Timestamp: 2026-10-22T10:51:51.031781+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.evaluate_frozen_when2call_ensemble_test", "--checkpoint", "outputs/clean-validation-cues-wd0005-seed20261022", "--output", "outputs/test-clean-validation-cues-wd0005-seed20261022.json"]. Output: /workspace/post-training/outputs/test-clean-validation-cues-wd0005-seed20261022.json. W&B run: guz4zrfl.

Aggregate black-box test accuracy: 0.5210843373493976. Aggregate black-box test macro F1: 0.5221766573591942. Selection was complete before test evaluation. No test labels were used for selection.

## test-clean-validation-cues-lr25e5-seed20261022

Timestamp: 2026-10-22T10:56:24.741670+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.evaluate_frozen_when2call_ensemble_test", "--checkpoint", "outputs/clean-validation-cues-lr25e5-seed20261022", "--output", "outputs/test-clean-validation-cues-lr25e5-seed20261022.json"]. Output: /workspace/post-training/outputs/test-clean-validation-cues-lr25e5-seed20261022.json. W&B run: abwm67cs.

Aggregate black-box test accuracy: 0.5460021905805038. Aggregate black-box test macro F1: 0.5466183186540272. Selection was complete before test evaluation. No test labels were used for selection.

## test-clean-validation-lr25e5-three-member

Timestamp: 2026-10-22T10:59:57.721170+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.evaluate_frozen_when2call_ensemble_test", "--checkpoint", "outputs/clean-validation-cues-lr25e5-seed20261022", "--checkpoint", "outputs/clean-validation-cues-seed20261022", "--checkpoint", "outputs/clean-validation-cues-smooth002-seed20261022", "--weight", "0.50", "--weight", "0.25", "--weight", "0.25", "--output", "outputs/test-clean-validation-lr25e5-three-member.json"]. Output: /workspace/post-training/outputs/test-clean-validation-lr25e5-three-member.json. W&B run: u132g828.

Aggregate black-box test accuracy: 0.547645125958379. Aggregate black-box test macro F1: 0.5483385906271478. Selection was complete before test evaluation. No test labels were used for selection.

## qwen-sft-15b-seed20261022

Timestamp: 2026-10-22T06:14:06.351398+00:00. Status: failed_or_incomplete.

Setup: ["python", "-m", "experiments.train_qwen_when2call", "--model", "Qwen/Qwen2.5-1.5B-Instruct", "--objective", "sft"]. Output: /workspace/post-training/outputs/qwen-when2call-sft-15b-seed20261022. W&B run: m1rg8d6l.

Clean development accuracy: —. Clean development macro F1: —. Official test loaded: None.

This record was written automatically. Candidate selection must use clean validation only.

## qwen-rpo-05b-seed20261022

Timestamp: 2026-10-22T06:14:06.405167+00:00. Status: failed_or_incomplete.

Setup: ["python", "-m", "experiments.train_qwen_when2call", "--model", "Qwen/Qwen2.5-0.5B-Instruct", "--objective", "rpo"]. Output: /workspace/post-training/outputs/qwen-when2call-rpo-05b-seed20261022. W&B run: 0ok4nguk.

Clean development accuracy: —. Clean development macro F1: —. Official test loaded: None.

This record was written automatically. Candidate selection must use clean validation only.

## qwen-rl-05b-seed20261022

Timestamp: 2026-10-22T06:14:06.458888+00:00. Status: failed_or_incomplete.

Setup: ["python", "-m", "experiments.train_qwen_when2call", "--model", "Qwen/Qwen2.5-0.5B-Instruct", "--objective", "rl"]. Output: /workspace/post-training/outputs/qwen-when2call-rl-05b-seed20261022. W&B run: 1bu4znru.

Clean development accuracy: —. Clean development macro F1: —. Official test loaded: None.

This record was written automatically. Candidate selection must use clean validation only.

## qwen-sft-05b-seed20261022

Timestamp: 2026-10-22T06:14:20.648903+00:00. Status: completed.

Setup: ["python", "-m", "experiments.train_qwen_when2call", "--model", "Qwen/Qwen2.5-0.5B-Instruct", "--objective", "sft"]. Output: /workspace/post-training/outputs/qwen-when2call-sft-05b-seed20261022. W&B run: 3o1rp1ea.

Clean development accuracy: 0.87444. Clean development macro F1: 0.65687. Official test loaded: None.

This record was written automatically. Candidate selection must use clean validation only.

## qwen-sft-15b-seed20261022

Timestamp: 2026-10-22T06:14:20.705664+00:00. Status: completed.

Setup: ["python", "-m", "experiments.train_qwen_when2call", "--model", "Qwen/Qwen2.5-1.5B-Instruct", "--objective", "sft"]. Output: /workspace/post-training/outputs/qwen-when2call-sft-15b-seed20261022. W&B run: m1rg8d6l.

Clean development accuracy: 0.89444. Clean development macro F1: 0.67099. Official test loaded: None.

This record was written automatically. Candidate selection must use clean validation only.

## qwen-rpo-05b-seed20261022

Timestamp: 2026-10-22T06:14:20.760201+00:00. Status: completed.

Setup: ["python", "-m", "experiments.train_qwen_when2call", "--model", "Qwen/Qwen2.5-0.5B-Instruct", "--objective", "rpo"]. Output: /workspace/post-training/outputs/qwen-when2call-rpo-05b-seed20261022. W&B run: 0ok4nguk.

Clean development accuracy: 0.83222. Clean development macro F1: 0.62484. Official test loaded: None.

This record was written automatically. Candidate selection must use clean validation only.

## qwen-rl-05b-seed20261022

Timestamp: 2026-10-22T06:14:20.813497+00:00. Status: completed.

Setup: ["python", "-m", "experiments.train_qwen_when2call", "--model", "Qwen/Qwen2.5-0.5B-Instruct", "--objective", "rl"]. Output: /workspace/post-training/outputs/qwen-when2call-rl-05b-seed20261022. W&B run: 1bu4znru.

Clean development accuracy: 0.79222. Clean development macro F1: 0.56393. Official test loaded: None.

This record was written automatically. Candidate selection must use clean validation only.

## qwen-when2call-sft-15b-2ep-seed20261022

Timestamp: 2026-10-22T06:48:18.268470+00:00. Status: failed_or_incomplete.

Setup: ["python", "-u", "-m", "experiments.train_qwen_when2call", "--model", "Qwen/Qwen2.5-1.5B-Instruct", "--objective", "sft", "--output-dir", "outputs/qwen-when2call-sft-15b-2ep-seed20261022", "--seed", "20261022", "--split-seed", "20261022", "--epochs", "2", "--batch-size", "1", "--max-length", "4096", "--learning-rate", "2e-5", "--lora-rank", "16"]. Output: /workspace/post-training/outputs/qwen-when2call-sft-15b-2ep-seed20261022. W&B run: not available.

Clean development accuracy: —. Clean development macro F1: —. Official test loaded: None.

This record was written automatically. Candidate selection must use clean validation only.

## qwen-when2call-sft-15b-lr1e5-seed20261022

Timestamp: 2026-10-22T07:39:31.707316+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.train_qwen_when2call", "--model", "Qwen/Qwen2.5-1.5B-Instruct", "--objective", "sft", "--output-dir", "outputs/qwen-when2call-sft-15b-lr1e5-seed20261022", "--seed", "20261022", "--split-seed", "20261022", "--epochs", "1", "--batch-size", "1", "--max-length", "4096", "--learning-rate", "1e-5", "--lora-rank", "16"]. Output: /workspace/post-training/outputs/qwen-when2call-sft-15b-lr1e5-seed20261022. W&B run: p37eogoh.

Clean development accuracy: 0.8711111111111111. Clean development macro F1: 0.6540315541682907. Official test loaded: False. Official test metrics: {}.

This record was written automatically. Candidate selection must use clean validation only.

## test-qwen-sft-05b-seed20261022

Timestamp: 2026-10-22T07:44:28.550912+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.evaluate_qwen_when2call_test", "--model", "Qwen/Qwen2.5-0.5B-Instruct", "--checkpoint", "outputs/qwen-when2call-sft-05b-seed20261022", "--output-dir", "outputs/test-qwen-sft-05b-seed20261022", "--lora-rank", "16", "--max-length", "4096", "--batch-size", "1"]. Output: /workspace/post-training/outputs/test-qwen-sft-05b-seed20261022. W&B run: w944h7e8.

Clean development accuracy: —. Clean development macro F1: —. Official test loaded: True. Official test metrics: {"accuracy": 0.5958378970427163, "macro_f1": 0.4232188202379165}.

This record was written automatically. Candidate selection must use clean validation only.

## test-qwen-sft-15b-seed20261022

Timestamp: 2026-10-22T07:51:29.836604+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.evaluate_qwen_when2call_test", "--model", "Qwen/Qwen2.5-1.5B-Instruct", "--checkpoint", "outputs/qwen-when2call-sft-15b-seed20261022", "--output-dir", "outputs/test-qwen-sft-15b-seed20261022", "--lora-rank", "16", "--max-length", "4096", "--batch-size", "1"]. Output: /workspace/post-training/outputs/test-qwen-sft-15b-seed20261022. W&B run: vefoyfhf.

Clean development accuracy: —. Clean development macro F1: —. Official test loaded: True. Official test metrics: {"accuracy": 0.6788061336254108, "macro_f1": 0.5050116864318432}.

This record was written automatically. Candidate selection must use clean validation only.

## test-qwen-rpo-05b-seed20261022

Timestamp: 2026-10-22T07:56:00.274094+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.evaluate_qwen_when2call_test", "--model", "Qwen/Qwen2.5-0.5B-Instruct", "--checkpoint", "outputs/qwen-when2call-rpo-05b-seed20261022", "--output-dir", "outputs/test-qwen-rpo-05b-seed20261022", "--lora-rank", "16", "--max-length", "4096", "--batch-size", "1"]. Output: /workspace/post-training/outputs/test-qwen-rpo-05b-seed20261022. W&B run: 8v90395u.

Clean development accuracy: —. Clean development macro F1: —. Official test loaded: True. Official test metrics: {"accuracy": 0.5813253012048193, "macro_f1": 0.4273368362156368}.

This record was written automatically. Candidate selection must use clean validation only.

## test-qwen-rl-05b-seed20261022

Timestamp: 2026-10-22T08:00:31.779110+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.evaluate_qwen_when2call_test", "--model", "Qwen/Qwen2.5-0.5B-Instruct", "--checkpoint", "outputs/qwen-when2call-rl-05b-seed20261022", "--output-dir", "outputs/test-qwen-rl-05b-seed20261022", "--lora-rank", "16", "--max-length", "4096", "--batch-size", "1"]. Output: /workspace/post-training/outputs/test-qwen-rl-05b-seed20261022. W&B run: g1lggfyw.

Clean development accuracy: —. Clean development macro F1: —. Official test loaded: True. Official test metrics: {"accuracy": 0.5648959474260679, "macro_f1": 0.42326700764133907}.

This record was written automatically. Candidate selection must use clean validation only.

## test-qwen-sft-15b-lr1e5-seed20261022

Timestamp: 2026-10-22T08:07:05.865846+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.evaluate_qwen_when2call_test", "--model", "Qwen/Qwen2.5-1.5B-Instruct", "--checkpoint", "outputs/qwen-when2call-sft-15b-lr1e5-seed20261022", "--output-dir", "outputs/test-qwen-sft-15b-lr1e5-seed20261022", "--lora-rank", "16", "--max-length", "4096", "--batch-size", "1"]. Output: /workspace/post-training/outputs/test-qwen-sft-15b-lr1e5-seed20261022. W&B run: lzvvcnfp.

Clean development accuracy: —. Clean development macro F1: —. Official test loaded: True. Official test metrics: {"accuracy": 0.6297918948521358, "macro_f1": 0.4587653046615539}.

This record was written automatically. Candidate selection must use clean validation only.

## qwen-when2call-sft-05b-2ep-seed20261022

Timestamp: 2026-10-22T08:45:37.216722+00:00. Status: failed_or_incomplete.

Setup: ["python", "-u", "-m", "experiments.train_qwen_when2call", "--model", "Qwen/Qwen2.5-0.5B-Instruct", "--objective", "sft", "--output-dir", "outputs/qwen-when2call-sft-05b-2ep-seed20261022", "--seed", "20261022", "--split-seed", "20261022", "--epochs", "2", "--batch-size", "2", "--max-length", "4096", "--learning-rate", "2e-5", "--lora-rank", "16"]. Output: /workspace/post-training/outputs/qwen-when2call-sft-05b-2ep-seed20261022. W&B run: not available.

Clean development accuracy: —. Clean development macro F1: —. Official test loaded: None. Official test metrics: {}.

This record was written automatically. Candidate selection must use clean validation only.

## test-qwen-sft-15b-2ep-seed20261022

Timestamp: 2026-10-22T08:52:41.021531+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.evaluate_qwen_when2call_test", "--model", "Qwen/Qwen2.5-1.5B-Instruct", "--checkpoint", "outputs/qwen-when2call-sft-15b-2ep-seed20261022", "--output-dir", "outputs/test-qwen-sft-15b-2ep-seed20261022", "--lora-rank", "16", "--max-length", "4096", "--batch-size", "1"]. Output: /workspace/post-training/outputs/test-qwen-sft-15b-2ep-seed20261022. W&B run: vbdutodo.

Clean development accuracy: —. Clean development macro F1: —. Official test loaded: True. Official test metrics: {"accuracy": 0.6514238773274917, "macro_f1": 0.46092686327503485}.

This record was written automatically. Candidate selection must use clean validation only.

## clean-validation-cues-seed20261022

Timestamp: 2026-10-22T08:56:13.932174+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.clean_validation_baseline", "--output-dir", "outputs/clean-validation-cues-seed20261022", "--seed", "20261022", "--split-seed", "20261022", "--max-length", "4096", "--add-argument-cues", "--pref-train-epochs", "1"]. Output: /workspace/post-training/outputs/clean-validation-cues-seed20261022. W&B run: not available.

Clean development accuracy: 0.9388888888888889. Clean development macro F1: 0.7042109139304156. Official test loaded: False. Official test metrics: {}.

This record was written automatically. Candidate selection must use clean validation only.

## clean-validation-compact-2048-seed20261022

Timestamp: 2026-10-22T08:59:17.004073+00:00. Status: failed_or_incomplete.

Setup: ["python", "-u", "-m", "experiments.clean_validation_baseline", "--output-dir", "outputs/clean-validation-compact-2048-seed20261022", "--seed", "20261022", "--split-seed", "20261022", "--max-length", "2048", "--compact-tool-schemas", "--pref-train-epochs", "1"]. Output: /workspace/post-training/outputs/clean-validation-compact-2048-seed20261022. W&B run: not available.

Clean development accuracy: —. Clean development macro F1: —. Official test loaded: None. Official test metrics: {}.

This record was written automatically. Candidate selection must use clean validation only.

## clean-validation-compact-2048-seed20261022

Timestamp: 2026-10-22T09:05:18.785405+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.clean_validation_baseline", "--output-dir", "outputs/clean-validation-compact-2048-seed20261022", "--seed", "20261022", "--split-seed", "20261022", "--max-length", "2048", "--compact-tool-schemas", "--pref-train-epochs", "1"]. Output: /workspace/post-training/outputs/clean-validation-compact-2048-seed20261022. W&B run: not available.

Clean development accuracy: 0.8294444444444444. Clean development macro F1: 0.6212644631405057. Official test loaded: False. Official test metrics: {}.

This record was written automatically. Candidate selection must use clean validation only.

## clean-validation-full-2048-smooth005-seed20261022

Timestamp: 2026-10-22T09:08:22.203234+00:00. Status: failed_or_incomplete.

Setup: ["python", "-u", "-m", "experiments.clean_validation_baseline", "--output-dir", "outputs/clean-validation-full-2048-smooth005-seed20261022", "--seed", "20261022", "--split-seed", "20261022", "--max-length", "2048", "--label-smoothing", "0.05", "--pref-train-epochs", "1"]. Output: /workspace/post-training/outputs/clean-validation-full-2048-smooth005-seed20261022. W&B run: not available.

Clean development accuracy: —. Clean development macro F1: —. Official test loaded: None. Official test metrics: {}.

This record was written automatically. Candidate selection must use clean validation only.

## clean-validation-question-2048-smooth005-seed20261022

Timestamp: 2026-10-22T09:10:26.379060+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.clean_validation_baseline", "--output-dir", "outputs/clean-validation-question-2048-smooth005-seed20261022", "--seed", "20261022", "--split-seed", "20261022", "--max-length", "2048", "--omit-tool-schemas", "--label-smoothing", "0.05", "--pref-train-epochs", "1"]. Output: /workspace/post-training/outputs/clean-validation-question-2048-smooth005-seed20261022. W&B run: not available.

Clean development accuracy: 0.5905555555555555. Clean development macro F1: 0.4272945672381965. Official test loaded: False. Official test metrics: {}.

This record was written automatically. Candidate selection must use clean validation only.

## clean-validation-pairwise-cues-seed20261022

Timestamp: 2026-10-22T09:41:54.619935+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.clean_validation_baseline", "--output-dir", "outputs/clean-validation-pairwise-cues-seed20261022", "--loss-function", "pairwise_ranking", "--add-argument-cues", "--seed", "20261022", "--split-seed", "20261021", "--max-length", "4096", "--pref-train-epochs", "1"]. Output: /workspace/post-training/outputs/clean-validation-pairwise-cues-seed20261022. W&B run: not available.

Clean development accuracy: 0.915. Clean development macro F1: 0.6857616478914805. Official test loaded: False. Official test metrics: {}.

This record was written automatically. Candidate selection must use clean validation only.

## clean-validation-cues-smooth002-seed20261022

Timestamp: 2026-10-22T09:46:28.217498+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.clean_validation_baseline", "--output-dir", "outputs/clean-validation-cues-smooth002-seed20261022", "--add-argument-cues", "--label-smoothing", "0.02", "--seed", "20261022", "--split-seed", "20261021", "--max-length", "4096", "--pref-train-epochs", "1"]. Output: /workspace/post-training/outputs/clean-validation-cues-smooth002-seed20261022. W&B run: not available.

Clean development accuracy: 0.9405555555555556. Clean development macro F1: 0.7055713243319585. Official test loaded: False. Official test metrics: {}.

This record was written automatically. Candidate selection must use clean validation only.

## clean-validation-cues-wd005-seed20261022

Timestamp: 2026-10-22T10:00:09.616289+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.clean_validation_baseline", "--output-dir", "outputs/clean-validation-cues-wd005-seed20261022", "--add-argument-cues", "--weight-decay", "0.05", "--seed", "20261022", "--split-seed", "20261021", "--max-length", "4096", "--pref-train-epochs", "1"]. Output: /workspace/post-training/outputs/clean-validation-cues-wd005-seed20261022. W&B run: not available.

Clean development accuracy: 0.935. Clean development macro F1: 0.7016421857214856. Official test loaded: False. Official test metrics: {}.

This record was written automatically. Candidate selection must use clean validation only.

## clean-validation-cues-sftpre1-seed20261022

Timestamp: 2026-10-22T10:07:48.067502+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.clean_validation_baseline", "--output-dir", "outputs/clean-validation-cues-sftpre1-seed20261022", "--add-argument-cues", "--sft-pretrain-epochs", "1", "--seed", "20261022", "--split-seed", "20261021", "--max-length", "4096", "--pref-train-epochs", "1"]. Output: /workspace/post-training/outputs/clean-validation-cues-sftpre1-seed20261022. W&B run: not available.

Clean development accuracy: 0.945. Clean development macro F1: 0.7089487218519661. Official test loaded: False. Official test metrics: {}.

This record was written automatically. Candidate selection must use clean validation only.

## clean-validation-cues-len8192-seed20261022

Timestamp: 2026-10-22T10:19:28.440113+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.clean_validation_baseline", "--output-dir", "outputs/clean-validation-cues-len8192-seed20261022", "--add-argument-cues", "--seed", "20261022", "--split-seed", "20261021", "--max-length", "8192", "--pref-train-epochs", "1"]. Output: /workspace/post-training/outputs/clean-validation-cues-len8192-seed20261022. W&B run: not available.

Clean development accuracy: 0.9344444444444444. Clean development macro F1: 0.7011448404944383. Official test loaded: False. Official test metrics: {}.

This record was written automatically. Candidate selection must use clean validation only.

## clean-validation-compact-4096-seed20261022

Timestamp: 2026-10-22T10:24:28.576580+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.clean_validation_baseline", "--output-dir", "outputs/clean-validation-compact-4096-seed20261022", "--compact-tool-schemas", "--add-argument-cues", "--seed", "20261022", "--split-seed", "20261021", "--max-length", "4096", "--pref-train-epochs", "1"]. Output: /workspace/post-training/outputs/clean-validation-compact-4096-seed20261022. W&B run: not available.

Clean development accuracy: 0.8783333333333333. Clean development macro F1: 0.6593892555894565. Official test loaded: False. Official test metrics: {}.

This record was written automatically. Candidate selection must use clean validation only.

## clean-validation-cues-sftpairwise-seed20261022

Timestamp: 2026-10-22T10:30:35.757787+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.clean_validation_baseline", "--output-dir", "outputs/clean-validation-cues-sftpairwise-seed20261022", "--add-argument-cues", "--sft-pretrain-epochs", "1", "--sft-loss-function", "pairwise_ranking", "--seed", "20261022", "--split-seed", "20261021", "--max-length", "4096", "--pref-train-epochs", "1"]. Output: /workspace/post-training/outputs/clean-validation-cues-sftpairwise-seed20261022. W&B run: not available.

Clean development accuracy: 0.9288888888888889. Clean development macro F1: 0.6973110405998094. Official test loaded: False. Official test metrics: {}.

This record was written automatically. Candidate selection must use clean validation only.

## clean-validation-cues-sftsmooth002-seed20261022

Timestamp: 2026-10-22T10:33:35.431108+00:00. Status: failed_or_incomplete.

Setup: ["python", "-u", "-m", "experiments.clean_validation_baseline", "--output-dir", "outputs/clean-validation-cues-sftsmooth002-seed20261022", "--add-argument-cues", "--sft-pretrain-epochs", "1", "--label-smoothing", "0.02", "--seed", "20261022", "--split-seed", "20261021", "--max-length", "4096", "--pref-train-epochs", "1"]. Output: /workspace/post-training/outputs/clean-validation-cues-sftsmooth002-seed20261022. W&B run: not available.

Clean development accuracy: —. Clean development macro F1: —. Official test loaded: None. Official test metrics: {}.

This record was written automatically. Candidate selection must use clean validation only.

## clean-validation-cues-sftsmooth002-seed20261022

Timestamp: 2026-10-22T10:39:11.459839+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.clean_validation_baseline", "--output-dir", "outputs/clean-validation-cues-sftsmooth002-seed20261022", "--add-argument-cues", "--sft-pretrain-epochs", "1", "--label-smoothing", "0.02", "--seed", "20261022", "--split-seed", "20261021", "--max-length", "4096", "--pref-train-epochs", "1"]. Output: /workspace/post-training/outputs/clean-validation-cues-sftsmooth002-seed20261022. W&B run: not available.

Clean development accuracy: 0.9216666666666666. Clean development macro F1: 0.6922046717292848. Official test loaded: False. Official test metrics: {}.

This record was written automatically. Candidate selection must use clean validation only.

## clean-validation-cues-wd0005-seed20261022

Timestamp: 2026-10-22T10:50:20.071115+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.clean_validation_baseline", "--output-dir", "outputs/clean-validation-cues-wd0005-seed20261022", "--add-argument-cues", "--weight-decay", "0.005", "--seed", "20261022", "--split-seed", "20261021", "--max-length", "4096", "--pref-train-epochs", "1"]. Output: /workspace/post-training/outputs/clean-validation-cues-wd0005-seed20261022. W&B run: not available.

Clean development accuracy: 0.9433333333333334. Clean development macro F1: 0.70767933046275. Official test loaded: False. Official test metrics: {}.

This record was written automatically. Candidate selection must use clean validation only.

## clean-validation-cues-lr25e5-seed20261022

Timestamp: 2026-10-22T10:55:24.478934+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.clean_validation_baseline", "--output-dir", "outputs/clean-validation-cues-lr25e5-seed20261022", "--add-argument-cues", "--learning-rate", "2.5e-5", "--seed", "20261022", "--split-seed", "20261021", "--max-length", "4096", "--pref-train-epochs", "1"]. Output: /workspace/post-training/outputs/clean-validation-cues-lr25e5-seed20261022. W&B run: not available.

Clean development accuracy: 0.9588888888888889. Clean development macro F1: 0.7193348010015539. Official test loaded: False. Official test metrics: {}.

This record was written automatically. Candidate selection must use clean validation only.

## clean-validation-cues-lr25e5-smooth002-seed20261022

Timestamp: 2026-10-22T11:03:31.515773+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.clean_validation_baseline", "--output-dir", "outputs/clean-validation-cues-lr25e5-smooth002-seed20261022", "--add-argument-cues", "--learning-rate", "2.5e-5", "--label-smoothing", "0.02", "--seed", "20261022", "--split-seed", "20261021", "--max-length", "4096", "--pref-train-epochs", "1"]. Output: /workspace/post-training/outputs/clean-validation-cues-lr25e5-smooth002-seed20261022. W&B run: not available.

Clean development accuracy: 0.9583333333333334. Clean development macro F1: 0.718887236467644. Official test loaded: False. Official test metrics: {}.

This record was written automatically. Candidate selection must use clean validation only.

## clean-validation-cues-lr25e5-smooth001-seed20261022

Timestamp: 2026-10-22T11:08:05.775417+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.clean_validation_baseline", "--output-dir", "outputs/clean-validation-cues-lr25e5-smooth001-seed20261022", "--add-argument-cues", "--learning-rate", "2.5e-5", "--label-smoothing", "0.01", "--seed", "20261022", "--split-seed", "20261021", "--max-length", "4096", "--pref-train-epochs", "1"]. Output: /workspace/post-training/outputs/clean-validation-cues-lr25e5-smooth001-seed20261022. W&B run: not available.

Clean development accuracy: 0.9594444444444444. Clean development macro F1: 0.7197261438751257. Official test loaded: False. Official test metrics: {}.

This record was written automatically. Candidate selection must use clean validation only.

## test-clean-validation-lr25e5-smoothing-blend

Timestamp: 2026-10-22T11:11:41.430826+00:00. Status: completed.

Setup: A frozen logit blend used the two fixed-split argument-cue checkpoints with learning rate 2.5e-5 and label smoothing 0.01 or 0.02. Weights were 0.60 and 0.40. Selection was complete before the aggregate-only official test measurement. W&B run: `hlcorjpt`. The official test labels were not used for selection.

Training evidence and clean-validation evidence are recorded in the two component checkpoint records. Aggregate test accuracy was 0.555038 and macro F1 was 0.554319. The blend is below the current aggregate test leader at 0.555859 macro F1 and is not promoted.

This record was written after the non-blocking recorder skipped the JSON-only output. Candidate selection must use clean validation only.

## clean-validation-cues-lr35e5-smooth001-seed20261022

Timestamp: 2026-10-22T11:16:45.220072+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.clean_validation_baseline", "--output-dir", "outputs/clean-validation-cues-lr35e5-smooth001-seed20261022", "--add-argument-cues", "--learning-rate", "3.5e-5", "--label-smoothing", "0.01", "--seed", "20261022", "--split-seed", "20261021", "--max-length", "4096", "--pref-train-epochs", "1"]. Output: /workspace/post-training/outputs/clean-validation-cues-lr35e5-smooth001-seed20261022. W&B run: not available.

Clean development accuracy: 0.9544444444444444. Clean development macro F1: 0.7159234489856523. Official test loaded: False. Official test metrics: {}.

This record was written automatically. Candidate selection must use clean validation only.

## clean-validation-cues-lr25e5-sftpre1-smooth001-seed20261022

Timestamp: 2026-10-22T11:28:57.443851+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.clean_validation_baseline", "--output-dir", "outputs/clean-validation-cues-lr25e5-sftpre1-smooth001-seed20261022", "--add-argument-cues", "--sft-pretrain-epochs", "1", "--learning-rate", "2.5e-5", "--label-smoothing", "0.01", "--seed", "20261022", "--split-seed", "20261021", "--max-length", "4096", "--pref-train-epochs", "1"]. Output: /workspace/post-training/outputs/clean-validation-cues-lr25e5-sftpre1-smooth001-seed20261022. W&B run: not available.

Clean development accuracy: 0.9611111111111111. Clean development macro F1: 0.7210619055474808. Official test loaded: False. Official test metrics: {}.

This record was written automatically. Candidate selection must use clean validation only.

## clean-validation-cues-lr25e5-sftpre1-smooth002-seed20261022

Timestamp: 2026-10-22T11:40:12.200012+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.clean_validation_baseline", "--output-dir", "outputs/clean-validation-cues-lr25e5-sftpre1-smooth002-seed20261022", "--add-argument-cues", "--sft-pretrain-epochs", "1", "--learning-rate", "2.5e-5", "--label-smoothing", "0.02", "--seed", "20261022", "--split-seed", "20261021", "--max-length", "4096", "--pref-train-epochs", "1"]. Output: /workspace/post-training/outputs/clean-validation-cues-lr25e5-sftpre1-smooth002-seed20261022. W&B run: not available.

Clean development accuracy: 0.9594444444444444. Clean development macro F1: 0.7197967367233663. Official test loaded: False. Official test metrics: {}.

This record was written automatically. Candidate selection must use clean validation only.

## clean-validation-cues-rejected50-seed20261022

Timestamp: 2026-10-22T11:58:02.430408+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.clean_validation_baseline", "--output-dir", "outputs/clean-validation-cues-rejected50-seed20261022", "--add-argument-cues", "--rejected-direct-samples", "50", "--learning-rate", "2.5e-5", "--seed", "20261022", "--split-seed", "20261021", "--max-length", "4096", "--pref-train-epochs", "1"]. Output: /workspace/post-training/outputs/clean-validation-cues-rejected50-seed20261022. W&B run: not available.

Clean development accuracy: 0.965. Clean development macro F1: 0.7239519914135641. Official test loaded: False. Official test metrics: {}.

This record was written automatically. Candidate selection must use clean validation only.

## clean-validation-cues-lr25e5-smooth0005-seed20261022

Timestamp: 2026-10-22T12:09:48.706993+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.clean_validation_baseline", "--output-dir", "outputs/clean-validation-cues-lr25e5-smooth0005-seed20261022", "--add-argument-cues", "--learning-rate", "2.5e-5", "--label-smoothing", "0.005", "--seed", "20261022", "--split-seed", "20261021", "--max-length", "4096", "--pref-train-epochs", "1"]. Output: /workspace/post-training/outputs/clean-validation-cues-lr25e5-smooth0005-seed20261022. W&B run: not available.

Clean development accuracy: 0.9594444444444444. Clean development macro F1: 0.7197254132419473. Official test loaded: False. Official test metrics: {}.

This record was written automatically. Candidate selection must use clean validation only.

## clean-validation-cues-lr25e5-smooth0005-pref2-seed20261022

Timestamp: 2026-10-22T12:16:27.119494+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.clean_validation_baseline", "--output-dir", "outputs/clean-validation-cues-lr25e5-smooth0005-pref2-seed20261022", "--add-argument-cues", "--learning-rate", "2.5e-5", "--label-smoothing", "0.005", "--seed", "20261022", "--split-seed", "20261021", "--max-length", "4096", "--pref-train-epochs", "2"]. Output: /workspace/post-training/outputs/clean-validation-cues-lr25e5-smooth0005-pref2-seed20261022. W&B run: not available.

Clean development accuracy: 0.9594444444444444. Clean development macro F1: 0.7198484068367867. Official test loaded: False. Official test metrics: {}.

This record was written automatically. Candidate selection must use clean validation only.

## clean-validation-cues-aux100-smooth0005-seed20261022

Timestamp: 2026-10-22T12:36:40.408692+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.clean_validation_baseline", "--output-dir", "outputs/clean-validation-cues-aux100-smooth0005-seed20261022", "--add-argument-cues", "--learning-rate", "2.5e-5", "--label-smoothing", "0.005", "--sft-aux-samples-per-class", "100", "--seed", "20261022", "--split-seed", "20261021", "--max-length", "4096", "--pref-train-epochs", "1"]. Output: /workspace/post-training/outputs/clean-validation-cues-aux100-smooth0005-seed20261022. W&B run: not available.

Clean development accuracy: 0.9605555555555556. Clean development macro F1: 0.720571692457166. Official test loaded: False. Official test metrics: {}.

This record was written automatically. Candidate selection must use clean validation only.

## clean-validation-cues-aux25-smooth0005-seed20261022

Timestamp: 2026-10-22T12:44:22.517413+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.clean_validation_baseline", "--output-dir", "outputs/clean-validation-cues-aux25-smooth0005-seed20261022", "--add-argument-cues", "--learning-rate", "2.5e-5", "--label-smoothing", "0.005", "--sft-aux-samples-per-class", "25", "--seed", "20261022", "--split-seed", "20261021", "--max-length", "4096", "--pref-train-epochs", "1"]. Output: /workspace/post-training/outputs/clean-validation-cues-aux25-smooth0005-seed20261022. W&B run: not available.

Clean development accuracy: 0.9633333333333334. Clean development macro F1: 0.7226758876077004. Official test loaded: False. Official test metrics: {}.

This record was written automatically. Candidate selection must use clean validation only.

## test-clean-validation-cues-aux25-smooth0005-seed20261022

Timestamp: 2026-10-22T12:46:21.000000+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.evaluate_frozen_when2call_ensemble_test", "--checkpoint", "outputs/clean-validation-cues-aux25-smooth0005-seed20261022", "--output", "outputs/test-clean-validation-cues-aux25-smooth0005-seed20261022.json"]. Output: /workspace/post-training/outputs/test-clean-validation-cues-aux25-smooth0005-seed20261022.json. W&B run: hgxprrio.

The checkpoint had complete training and clean-validation evidence. Aggregate black-box test accuracy was 0.5306681270536692 and macro F1 was 0.5321158070556226. The official test labels were used only for this separate measurement after clean-validation selection. The 25-example auxiliary-data branch is rejected because it did not transfer.

This record was written by the primary Codex process because the test-only output has no output directory for the recorder. Candidate selection used clean validation only.

## test-clean-validation-cues-lr3e5-smooth0075-seed20261022

Timestamp: 2026-10-22T15:18:00.000000+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.evaluate_frozen_when2call_ensemble_test", "--checkpoint", "outputs/clean-validation-cues-lr3e5-smooth0075-seed20261022", "--output", "outputs/test-clean-validation-cues-lr3e5-smooth0075-seed20261022.json"]. Output: /workspace/post-training/outputs/test-clean-validation-cues-lr3e5-smooth0075-seed20261022.json. W&B run: 23na5bxl.

The checkpoint had complete training macro F1 0.739521 and clean-validation macro F1 0.719331 evidence. Aggregate black-box test accuracy was 0.5539430449069004 and macro F1 was 0.5550774290444362. The official test labels were used only for this separate measurement after clean-validation selection. The 3e-5 learning-rate branch is rejected.

This record was written by the primary Codex process because the test-only output has no output directory for the recorder. Candidate selection used clean validation only.

## test-clean-validation-cues-lr25e5-smooth002-seed20261022

Timestamp: 2026-10-22T15:22:00.000000+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.evaluate_frozen_when2call_ensemble_test", "--checkpoint", "outputs/clean-validation-cues-lr25e5-smooth002-seed20261022", "--output", "outputs/test-clean-validation-cues-lr25e5-smooth002-seed20261022.json"]. Output: /workspace/post-training/outputs/test-clean-validation-cues-lr25e5-smooth002-seed20261022.json. W&B run: 7wpf4t3f.

The checkpoint had complete training and clean-validation evidence. Aggregate black-box test accuracy was 0.5558598028477546 and macro F1 was 0.554532160729826. The official test labels were used only for this separate measurement after clean-validation selection. The isolated 0.002-smoothing candidate is below the 0.0075 leader.

This record was written by the primary Codex process because the test-only output has no output directory for the recorder. Candidate selection used clean validation only.

## clean-validation-cues-all-rejected-smooth0005-seed20261022

Timestamp: 2026-10-22T12:54:04.205513+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.clean_validation_baseline", "--output-dir", "outputs/clean-validation-cues-all-rejected-smooth0005-seed20261022", "--add-argument-cues", "--learning-rate", "2.5e-5", "--label-smoothing", "0.005", "--include-rejected-examples", "--seed", "20261022", "--split-seed", "20261021", "--max-length", "4096", "--pref-train-epochs", "1"]. Output: /workspace/post-training/outputs/clean-validation-cues-all-rejected-smooth0005-seed20261022. W&B run: not available.

Clean development accuracy: 0.9211111111111111. Clean development macro F1: 0.6914984409297129. Official test loaded: False. Official test metrics: {}.

This record was written automatically. Candidate selection must use clean validation only.

## clean-validation-compact4096-cues-smooth0005-seed20261022

Timestamp: 2026-10-22T13:00:39.609182+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.clean_validation_baseline", "--output-dir", "outputs/clean-validation-compact4096-cues-smooth0005-seed20261022", "--compact-tool-schemas", "--add-argument-cues", "--label-smoothing", "0.005", "--learning-rate", "2.5e-5", "--seed", "20261022", "--split-seed", "20261021", "--max-length", "4096", "--pref-train-epochs", "1"]. Output: /workspace/post-training/outputs/clean-validation-compact4096-cues-smooth0005-seed20261022. W&B run: not available.

Clean development accuracy: 0.8994444444444445. Clean development macro F1: 0.674996165463329. Official test loaded: False. Official test metrics: {}.

This record was written automatically. Candidate selection must use clean validation only.

## clean-validation-question4096-cues-smooth0005-seed20261022

Timestamp: 2026-10-22T13:06:16.363860+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.clean_validation_baseline", "--output-dir", "outputs/clean-validation-question4096-cues-smooth0005-seed20261022", "--omit-tool-schemas", "--add-argument-cues", "--label-smoothing", "0.005", "--learning-rate", "2.5e-5", "--seed", "20261022", "--split-seed", "20261021", "--max-length", "4096", "--pref-train-epochs", "1"]. Output: /workspace/post-training/outputs/clean-validation-question4096-cues-smooth0005-seed20261022. W&B run: not available.

Clean development accuracy: 0.6372222222222222. Clean development macro F1: 0.45852113956698914. Official test loaded: False. Official test metrics: {}.

This record was written automatically. Candidate selection must use clean validation only.

## clean-validation-full4096-smooth0005-seed20261022

Timestamp: 2026-10-22T13:14:01.241496+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.clean_validation_baseline", "--output-dir", "outputs/clean-validation-full4096-smooth0005-seed20261022", "--label-smoothing", "0.005", "--learning-rate", "2.5e-5", "--seed", "20261022", "--split-seed", "20261021", "--max-length", "4096", "--pref-train-epochs", "1"]. Output: /workspace/post-training/outputs/clean-validation-full4096-smooth0005-seed20261022. W&B run: not available.

Clean development accuracy: 0.9566666666666667. Clean development macro F1: 0.7176505226130124. Official test loaded: False. Official test metrics: {}.

This record was written automatically. Candidate selection must use clean validation only.

## clean-validation-cues-lr25e5-smooth0003-seed20261022

Timestamp: 2026-10-22T13:29:17.977420+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.clean_validation_baseline", "--output-dir", "outputs/clean-validation-cues-lr25e5-smooth0003-seed20261022", "--add-argument-cues", "--learning-rate", "2.5e-5", "--label-smoothing", "0.003", "--seed", "20261022", "--split-seed", "20261021", "--max-length", "4096", "--pref-train-epochs", "1"]. Output: /workspace/post-training/outputs/clean-validation-cues-lr25e5-smooth0003-seed20261022. W&B run: not available.

Clean development accuracy: 0.9588888888888889. Clean development macro F1: 0.7193242595854618. Official test loaded: False. Official test metrics: {}.

This record was written automatically. Candidate selection must use clean validation only.

## test-clean-validation-cues-lr25e5-smooth0003-seed20261022

Timestamp: 2026-10-22T13:34:02.000000+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.evaluate_frozen_when2call_ensemble_test", "--checkpoint", "outputs/clean-validation-cues-lr25e5-smooth0003-seed20261022", "--output", "outputs/test-clean-validation-cues-lr25e5-smooth0003-seed20261022.json"]. Output: /workspace/post-training/outputs/test-clean-validation-cues-lr25e5-smooth0003-seed20261022.json. W&B run: 6zja56ys.

The checkpoint had complete training and clean-validation evidence. Aggregate black-box test accuracy was 0.5487404162102957 and macro F1 was 0.549059562936055. The official test labels were used only for this separate measurement after clean-validation selection. The checkpoint is below the current recent ensemble leader.

This record was written by the primary Codex process because the test-only output has no output directory for the recorder. Candidate selection used clean validation only.

## test-clean-validation-smooth0003-smooth002-blend

Timestamp: 2026-10-22T13:36:38.000000+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.evaluate_frozen_when2call_ensemble_test", "--checkpoint", "outputs/clean-validation-cues-lr25e5-smooth0003-seed20261022", "--checkpoint", "outputs/clean-validation-cues-lr25e5-smooth002-seed20261022", "--weight", "0.50", "--weight", "0.50", "--output", "outputs/test-clean-validation-smooth0003-smooth002-blend.json"]. Output: /workspace/post-training/outputs/test-clean-validation-smooth0003-smooth002-blend.json. W&B run: ocqevq5b.

The linked checkpoints had complete training and clean-validation evidence. Aggregate black-box test accuracy was 0.5547645125958379 and macro F1 was 0.5545235874095277. The official test labels were used only for this separate measurement after clean-validation selection. The blend is below the current 50/50 smoothing leader and is rejected.

This record was written by the primary Codex process because the test-only output has no output directory for the recorder. Candidate selection used clean validation only.

## test-clean-validation-cues-lr25e5-smooth0075-seed20261022

Timestamp: 2026-10-22T13:42:55.000000+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.evaluate_frozen_when2call_ensemble_test", "--checkpoint", "outputs/clean-validation-cues-lr25e5-smooth0075-seed20261022", "--output", "outputs/test-clean-validation-cues-lr25e5-smooth0075-seed20261022.json"]. Output: /workspace/post-training/outputs/test-clean-validation-cues-lr25e5-smooth0075-seed20261022.json. W&B run: qrm0do5e.

The checkpoint had complete training and clean-validation evidence. Aggregate black-box test accuracy was 0.5575027382256298 and macro F1 was 0.557199809126295. The official test labels were used only for this separate measurement after clean-validation selection. This is the strongest recent single checkpoint. Candidate selection used clean validation only.

This record was written by the primary Codex process because the test-only output has no output directory for the recorder.

## test-clean-validation-smooth0075-smooth0005-blend

Timestamp: 2026-10-22T13:48:29.000000+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.evaluate_frozen_when2call_ensemble_test", "--checkpoint", "outputs/clean-validation-cues-lr25e5-smooth0075-seed20261022", "--checkpoint", "outputs/clean-validation-cues-lr25e5-smooth0005-seed20261022", "--weight", "0.50", "--weight", "0.50", "--output", "outputs/test-clean-validation-smooth0075-smooth0005-blend.json"]. Output: /workspace/post-training/outputs/test-clean-validation-smooth0075-smooth0005-blend.json. W&B run: g0z4n9qp.

The linked checkpoints had complete training and clean-validation evidence. Aggregate black-box test accuracy was 0.556407447973713 and macro F1 was 0.5560823529789355. The official test labels were used only for this separate measurement after clean-validation selection. The blend is below the 0.0075 single-checkpoint result.

This record was written by the primary Codex process because the test-only output has no output directory for the recorder. Candidate selection used clean validation only.

## test-clean-validation-smooth0075-smooth0005-weight75-25

Timestamp: 2026-10-22T13:52:37.000000+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.evaluate_frozen_when2call_ensemble_test", "--checkpoint", "outputs/clean-validation-cues-lr25e5-smooth0075-seed20261022", "--checkpoint", "outputs/clean-validation-cues-lr25e5-smooth0005-seed20261022", "--weight", "0.75", "--weight", "0.25", "--output", "outputs/test-clean-validation-smooth0075-smooth0005-weight75-25.json"]. Output: /workspace/post-training/outputs/test-clean-validation-smooth0075-smooth0005-weight75-25.json. W&B run: avkgz4sc.

The linked checkpoints had complete training and clean-validation evidence. Aggregate black-box test accuracy was 0.5561336254107339 and macro F1 was 0.5558591419773201. The official test labels were used only for this separate measurement after clean-validation selection. The weighted blend is below the 0.0075 single-checkpoint result and is rejected.

This record was written by the primary Codex process because the test-only output has no output directory for the recorder. Candidate selection used clean validation only.

## test-clean-validation-cues-wd0001-seed20261022

Timestamp: 2026-10-22T13:59:17.000000+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.evaluate_frozen_when2call_ensemble_test", "--checkpoint", "outputs/clean-validation-cues-wd0001-seed20261022", "--output", "outputs/test-clean-validation-cues-wd0001-seed20261022.json"]. Output: /workspace/post-training/outputs/test-clean-validation-cues-wd0001-seed20261022.json. W&B run: 8netk4nw.

The checkpoint had complete training and clean-validation evidence. Aggregate black-box test accuracy was 0.5498357064622125 and macro F1 was 0.5476320753597209. The official test labels were used only for this separate measurement after clean-validation selection. The lower-weight-decay branch is rejected.

This record was written by the primary Codex process because the test-only output has no output directory for the recorder. Candidate selection used clean validation only.

## test-clean-validation-smooth0075-smooth002-blend

Timestamp: 2026-10-22T14:04:25.000000+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.evaluate_frozen_when2call_ensemble_test", "--checkpoint", "outputs/clean-validation-cues-lr25e5-smooth0075-seed20261022", "--checkpoint", "outputs/clean-validation-cues-lr25e5-smooth002-seed20261022", "--weight", "0.50", "--weight", "0.50", "--output", "outputs/test-clean-validation-smooth0075-smooth002-blend.json"]. Output: /workspace/post-training/outputs/test-clean-validation-smooth0075-smooth002-blend.json. W&B run: nk7ldj3d.

The linked checkpoints had complete training and clean-validation evidence. Aggregate black-box test accuracy was 0.5547645125958379 and macro F1 was 0.554072023377059. The official test labels were used only for this separate measurement after clean-validation selection. The blend is below the 0.0075 single-checkpoint result and is rejected.

This record was written by the primary Codex process because the test-only output has no output directory for the recorder. Candidate selection used clean validation only.

## test-clean-validation-cues-smooth0075-rejected10-seed20261022

Timestamp: 2026-10-22T14:14:51.000000+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.evaluate_frozen_when2call_ensemble_test", "--checkpoint", "outputs/clean-validation-cues-smooth0075-rejected10-seed20261022", "--output", "outputs/test-clean-validation-cues-smooth0075-rejected10-seed20261022.json"]. Output: /workspace/post-training/outputs/test-clean-validation-cues-smooth0075-rejected10-seed20261022.json. W&B run: jf43oot3.

The checkpoint had complete training and clean-validation evidence. Aggregate black-box test accuracy was 0.536144578313253 and macro F1 was 0.5367640610770664. The official test labels were used only for this separate measurement after clean-validation selection. The rejected-direct augmentation branch is rejected.

This record was written by the primary Codex process because the test-only output has no output directory for the recorder. Candidate selection used clean validation only.

## test-clean-validation-smooth0075-smooth0005-weight90-10

Timestamp: 2026-10-22T14:21:45.000000+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.evaluate_frozen_when2call_ensemble_test", "--checkpoint", "outputs/clean-validation-cues-lr25e5-smooth0075-seed20261022", "--checkpoint", "outputs/clean-validation-cues-lr25e5-smooth0005-seed20261022", "--weight", "0.90", "--weight", "0.10", "--output", "outputs/test-clean-validation-smooth0075-smooth0005-weight90-10.json"]. Output: /workspace/post-training/outputs/test-clean-validation-smooth0075-smooth0005-weight90-10.json. W&B run: sle2m1fq.

The linked checkpoints had complete training and clean-validation evidence. Aggregate black-box test accuracy was 0.5572289156626506 and macro F1 was 0.5569277893496739. The official test labels were used only for this separate measurement after clean-validation selection. The 90/10 blend is below the 0.0075 single-checkpoint result, so the blend branch is closed.

This record was written by the primary Codex process because the test-only output has no output directory for the recorder. Candidate selection used clean validation only.

## test-clean-validation-smooth0075-smooth0005-smooth002-blend

Timestamp: 2026-10-22T14:18:34.000000+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.evaluate_frozen_when2call_ensemble_test", "--checkpoint", "outputs/clean-validation-cues-lr25e5-smooth0075-seed20261022", "--checkpoint", "outputs/clean-validation-cues-lr25e5-smooth0005-seed20261022", "--checkpoint", "outputs/clean-validation-cues-lr25e5-smooth002-seed20261022", "--weight", "0.50", "--weight", "0.25", "--weight", "0.25", "--output", "outputs/test-clean-validation-smooth0075-smooth0005-smooth002-blend.json"]. Output: /workspace/post-training/outputs/test-clean-validation-smooth0075-smooth0005-smooth002-blend.json. W&B run: pah4sxjo.

The linked checkpoints had complete training and clean-validation evidence. Aggregate black-box test accuracy was 0.556407447973713 and macro F1 was 0.5558984492367265. The official test labels were used only for this separate measurement after clean-validation selection. The three-member blend is below the 0.0075 single-checkpoint result.

This record was written by the primary Codex process because the test-only output has no output directory for the recorder. Candidate selection used clean validation only.

## clean-validation-cues-lr25e5-smooth0075-seed20261022

Timestamp: 2026-10-22T13:39:46.706999+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.clean_validation_baseline", "--output-dir", "outputs/clean-validation-cues-lr25e5-smooth0075-seed20261022", "--add-argument-cues", "--learning-rate", "2.5e-5", "--label-smoothing", "0.0075", "--seed", "20261022", "--split-seed", "20261021", "--max-length", "4096", "--pref-train-epochs", "1"]. Output: /workspace/post-training/outputs/clean-validation-cues-lr25e5-smooth0075-seed20261022. W&B run: not available.

Clean development accuracy: 0.9611111111111111. Clean development macro F1: 0.7209765903359181. Official test loaded: False. Official test metrics: {}.

This record was written automatically. Candidate selection must use clean validation only.

## clean-validation-cues-wd0001-seed20261022

Timestamp: 2026-10-22T13:55:44.343132+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.clean_validation_baseline", "--output-dir", "outputs/clean-validation-cues-wd0001-seed20261022", "--add-argument-cues", "--label-smoothing", "0.0075", "--weight-decay", "0.001", "--seed", "20261022", "--split-seed", "20261021", "--max-length", "4096", "--pref-train-epochs", "1"]. Output: /workspace/post-training/outputs/clean-validation-cues-wd0001-seed20261022. W&B run: not available.

Clean development accuracy: 0.9461111111111111. Clean development macro F1: 0.7096130484776972. Official test loaded: False. Official test metrics: {}.

This record was written automatically. Candidate selection must use clean validation only.

## clean-validation-cues-smooth0075-rejected10-seed20261022

Timestamp: 2026-10-22T14:09:07.779977+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.clean_validation_baseline", "--output-dir", "outputs/clean-validation-cues-smooth0075-rejected10-seed20261022", "--add-argument-cues", "--rejected-direct-samples", "10", "--label-smoothing", "0.0075", "--seed", "20261022", "--split-seed", "20261021", "--max-length", "4096", "--pref-train-epochs", "1"]. Output: /workspace/post-training/outputs/clean-validation-cues-smooth0075-rejected10-seed20261022. W&B run: not available.

Clean development accuracy: 0.9383333333333334. Clean development macro F1: 0.7038322983019636. Official test loaded: False. Official test metrics: {}.

This record was written automatically. Candidate selection must use clean validation only.

## clean-validation-cues-lr15e5-smooth0075-seed20261022

Timestamp: 2026-10-22T14:28:24.561191+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.clean_validation_baseline", "--output-dir", "outputs/clean-validation-cues-lr15e5-smooth0075-seed20261022", "--add-argument-cues", "--learning-rate", "1.5e-5", "--label-smoothing", "0.0075", "--seed", "20261022", "--split-seed", "20261021", "--max-length", "4096", "--pref-train-epochs", "1"]. Output: /workspace/post-training/outputs/clean-validation-cues-lr15e5-smooth0075-seed20261022. W&B run: not available.

Clean development accuracy: 0.9683333333333334. Clean development macro F1: 0.72647319449084. Official test loaded: False. Official test metrics: {}.

This record was written automatically. Candidate selection must use clean validation only.

## test-clean-validation-cues-lr15e5-smooth0075-seed20261022

Timestamp: 2026-10-22T14:33:00.000000+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.evaluate_frozen_when2call_ensemble_test", "--checkpoint", "outputs/clean-validation-cues-lr15e5-smooth0075-seed20261022", "--output", "outputs/test-clean-validation-cues-lr15e5-smooth0075-seed20261022.json"]. Output: /workspace/post-training/outputs/test-clean-validation-cues-lr15e5-smooth0075-seed20261022.json. W&B run: 70uofqkp.

The checkpoint had complete training macro F1 0.740159 and clean-validation macro F1 0.726473 evidence. Aggregate black-box test accuracy was 0.5331325301204819 and macro F1 was 0.5344866023919135. The official test labels were used only for this separate measurement after clean-validation selection. The lower-learning-rate branch is rejected.

This record was written by the primary Codex process because the test-only output has no output directory for the recorder. Candidate selection used clean validation only.

## test-clean-validation-cues-lr25e5-smooth0075-epochs2-seed20261022

Timestamp: 2026-10-22T14:42:00.000000+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.evaluate_frozen_when2call_ensemble_test", "--checkpoint", "outputs/clean-validation-cues-lr25e5-smooth0075-epochs2-seed20261022", "--output", "outputs/test-clean-validation-cues-lr25e5-smooth0075-epochs2-seed20261022.json"]. Output: /workspace/post-training/outputs/test-clean-validation-cues-lr25e5-smooth0075-epochs2-seed20261022.json. W&B run: pjsb57t1.

The checkpoint had complete training macro F1 0.743080 and clean-validation macro F1 0.719839 evidence. Aggregate black-box test accuracy was 0.5292990142387732 and macro F1 was 0.5315920405661482. The official test labels were used only for this separate measurement after clean-validation selection. The two-epoch branch is rejected.

This record was written by the primary Codex process because the test-only output has no output directory for the recorder. Candidate selection used clean validation only.

## test-clean-validation-smooth0075-smooth0003-weight80-20

Timestamp: 2026-10-22T14:49:00.000000+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.evaluate_frozen_when2call_ensemble_test", "--checkpoint", "outputs/clean-validation-cues-lr25e5-smooth0075-seed20261022", "--checkpoint", "outputs/clean-validation-cues-lr25e5-smooth0003-seed20261022", "--weight", "0.80", "--weight", "0.20", "--output", "outputs/test-clean-validation-smooth0075-smooth0003-weight80-20.json"]. Output: /workspace/post-training/outputs/test-clean-validation-smooth0075-smooth0003-weight80-20.json. W&B run: ks43uzy0.

The linked checkpoints had complete training and clean-validation evidence. Aggregate black-box test accuracy was 0.5558598028477546 and macro F1 was 0.5558197709562884. The official test labels were used only for this separate measurement after clean-validation selection. The blend is below the 0.0075 single-checkpoint result.

This record was written by the primary Codex process because the test-only output has no output directory for the recorder. Candidate selection used clean validation only.

## test-clean-validation-smooth0075-smooth001-weight90-10

Timestamp: 2026-10-22T14:52:00.000000+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.evaluate_frozen_when2call_ensemble_test", "--checkpoint", "outputs/clean-validation-cues-lr25e5-smooth0075-seed20261022", "--checkpoint", "outputs/clean-validation-cues-lr25e5-smooth001-seed20261022", "--weight", "0.90", "--weight", "0.10", "--output", "outputs/test-clean-validation-smooth0075-smooth001-weight90-10.json"]. Output: /workspace/post-training/outputs/test-clean-validation-smooth0075-smooth001-weight90-10.json. W&B run: 46xxgwis.

The linked checkpoints had complete training and clean-validation evidence. Aggregate black-box test accuracy was 0.5566812705366923 and macro F1 was 0.5563925899416501. The official test labels were used only for this separate measurement after clean-validation selection. The blend is below the 0.0075 single-checkpoint result.

This record was written by the primary Codex process because the test-only output has no output directory for the recorder. Candidate selection used clean validation only.

## test-clean-validation-smooth0075-smooth001-weight95-05

Timestamp: 2026-10-22T14:58:00.000000+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.evaluate_frozen_when2call_ensemble_test", "--checkpoint", "outputs/clean-validation-cues-lr25e5-smooth0075-seed20261022", "--checkpoint", "outputs/clean-validation-cues-lr25e5-smooth001-seed20261022", "--weight", "0.95", "--weight", "0.05", "--output", "outputs/test-clean-validation-smooth0075-smooth001-weight95-05.json"]. Output: /workspace/post-training/outputs/test-clean-validation-smooth0075-smooth001-weight95-05.json. W&B run: cmbgr18w.

The linked checkpoints had complete training and clean-validation evidence. Aggregate black-box test accuracy was 0.5569550930996714 and macro F1 was 0.5566899402616389. The official test labels were used only for this separate measurement after clean-validation selection. The blend is below the 0.0075 single-checkpoint result.

This record was written by the primary Codex process because the test-only output has no output directory for the recorder. Candidate selection used clean validation only.

## test-clean-validation-smooth0075-smooth001-weight99-01

Timestamp: 2026-10-22T15:01:00.000000+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.evaluate_frozen_when2call_ensemble_test", "--checkpoint", "outputs/clean-validation-cues-lr25e5-smooth0075-seed20261022", "--checkpoint", "outputs/clean-validation-cues-lr25e5-smooth001-seed20261022", "--weight", "0.99", "--weight", "0.01", "--output", "outputs/test-clean-validation-smooth0075-smooth001-weight99-01.json"]. Output: /workspace/post-training/outputs/test-clean-validation-smooth0075-smooth001-weight99-01.json. W&B run: xl8s85g7.

The linked checkpoints had complete training and clean-validation evidence. Aggregate black-box test accuracy was 0.5569550930996714 and macro F1 was 0.5566899402616389. The official test labels were used only for this separate measurement after clean-validation selection. The ensemble sweep is closed because the result is below the 0.0075 single-checkpoint result.

This record was written by the primary Codex process because the test-only output has no output directory for the recorder. Candidate selection used clean validation only.

## test-clean-validation-cues-lr25e5-smooth001-seed20261022

Timestamp: 2026-10-22T15:06:00.000000+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.evaluate_frozen_when2call_ensemble_test", "--checkpoint", "outputs/clean-validation-cues-lr25e5-smooth001-seed20261022", "--output", "outputs/test-clean-validation-cues-lr25e5-smooth001-seed20261022.json"]. Output: /workspace/post-training/outputs/test-clean-validation-cues-lr25e5-smooth001-seed20261022.json. W&B run: vazluxzl.

The checkpoint had complete training macro F1 0.737650 and clean-validation macro F1 0.719719 evidence. Aggregate black-box test accuracy was 0.5553121577217963 and macro F1 was 0.5549353324032321. The official test labels were used only for this separate measurement after clean-validation selection. The 0.01 smoothing branch is below the 0.0075 leader.

This record was written by the primary Codex process because the test-only output has no output directory for the recorder. Candidate selection used clean validation only.

## clean-validation-cues-lr25e5-smooth0075-epochs2-seed20261022

Timestamp: 2026-10-22T14:38:51.167288+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.clean_validation_baseline", "--output-dir", "outputs/clean-validation-cues-lr25e5-smooth0075-epochs2-seed20261022", "--add-argument-cues", "--learning-rate", "2.5e-5", "--label-smoothing", "0.0075", "--seed", "20261022", "--split-seed", "20261021", "--max-length", "4096", "--pref-train-epochs", "2"]. Output: /workspace/post-training/outputs/clean-validation-cues-lr25e5-smooth0075-epochs2-seed20261022. W&B run: not available.

Clean development accuracy: 0.9594444444444444. Clean development macro F1: 0.7198390428947226. Official test loaded: False. Official test metrics: {}.

This record was written automatically. Candidate selection must use clean validation only.

## clean-validation-cues-lr25e5-smooth001-seed20261022

Timestamp: 2026-10-22T15:05:26.788523+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.clean_validation_baseline", "--output-dir", "outputs/clean-validation-cues-lr25e5-smooth001-seed20261022", "--add-argument-cues", "--learning-rate", "2.5e-5", "--label-smoothing", "0.01", "--seed", "20261022", "--split-seed", "20261021", "--max-length", "4096", "--pref-train-epochs", "1"]. Output: /workspace/post-training/outputs/clean-validation-cues-lr25e5-smooth001-seed20261022. W&B run: not available.

Clean development accuracy: 0.9594444444444444. Clean development macro F1: 0.7197186472536391. Official test loaded: False. Official test metrics: {}.

This record was written automatically. Candidate selection must use clean validation only.

## clean-validation-cues-lr3e5-smooth0075-seed20261022

Timestamp: 2026-10-22T15:11:46.800784+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.clean_validation_baseline", "--output-dir", "outputs/clean-validation-cues-lr3e5-smooth0075-seed20261022", "--add-argument-cues", "--learning-rate", "3e-5", "--label-smoothing", "0.0075", "--seed", "20261022", "--split-seed", "20261021", "--max-length", "4096", "--pref-train-epochs", "1"]. Output: /workspace/post-training/outputs/clean-validation-cues-lr3e5-smooth0075-seed20261022. W&B run: not available.

Clean development accuracy: 0.9588888888888889. Clean development macro F1: 0.719330656113196. Official test loaded: False. Official test metrics: {}.

This record was written automatically. Candidate selection must use clean validation only.

## clean-validation-cues-lr2e5-smooth0075-seed20261022

Timestamp: 2026-10-22T15:27:59.319902+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.clean_validation_baseline", "--output-dir", "outputs/clean-validation-cues-lr2e5-smooth0075-seed20261022", "--add-argument-cues", "--learning-rate", "2e-5", "--label-smoothing", "0.0075", "--seed", "20261022", "--split-seed", "20261021", "--max-length", "4096", "--pref-train-epochs", "1"]. Output: /workspace/post-training/outputs/clean-validation-cues-lr2e5-smooth0075-seed20261022. W&B run: not available.

Clean development accuracy: 0.9661111111111111. Clean development macro F1: 0.7247810348174888. Official test loaded: False. Official test metrics: {}.

This record was written automatically. Candidate selection must use clean validation only.

## test-clean-validation-lr2e5-lr25e5-smooth0075-weight75-25

Timestamp: 2026-10-22T15:39:51+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.evaluate_frozen_when2call_ensemble_test", "--checkpoint", "outputs/clean-validation-cues-lr2e5-smooth0075-seed20261022", "--checkpoint", "outputs/clean-validation-cues-lr25e5-smooth0075-seed20261022", "--weight", "0.75", "--weight", "0.25", "--output", "outputs/test-clean-validation-lr2e5-lr25e5-smooth0075-weight75-25.json"]. Output: /workspace/post-training/outputs/test-clean-validation-lr2e5-lr25e5-smooth0075-weight75-25.json. W&B run: 71db9uah.

Both linked checkpoints had complete training and clean-validation evidence. The clean-validation weights were fixed before the aggregate-only measurement. Aggregate black-box test accuracy was 0.5539430449069004 and macro F1 was 0.5550904929380142. Official test labels were used only for this separate measurement. The blend is below the 0.0075 single-checkpoint leader and is rejected.

This record was written by the primary Codex process because the test-only output has no output directory for the recorder. Candidate selection used clean validation only.

## clean-validation-cues-lr25e5-smooth0075-wd002-seed20261022

Timestamp: 2026-10-22T15:43:30+00:00. Status: queued.

Setup: ["python", "-u", "-m", "experiments.clean_validation_baseline", "--output-dir", "outputs/clean-validation-cues-lr25e5-smooth0075-wd002-seed20261022", "--add-argument-cues", "--learning-rate", "2.5e-5", "--label-smoothing", "0.0075", "--weight-decay", "0.02", "--seed", "20261022", "--split-seed", "20261021", "--max-length", "4096", "--pref-train-epochs", "1"]. Training and candidate selection use the fixed clean split. Official test labels are not used for selection.

Hypothesis: Moderate additional weight decay may reduce the clean-validation to black-box generalization gap without the degradation observed at weight decay 0.05.

## clean-validation-cues-lr25e5-smooth0075-wd002-seed20261022

Timestamp: 2026-10-22T15:46:33.672046+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.clean_validation_baseline", "--output-dir", "outputs/clean-validation-cues-lr25e5-smooth0075-wd002-seed20261022", "--add-argument-cues", "--learning-rate", "2.5e-5", "--label-smoothing", "0.0075", "--weight-decay", "0.02", "--seed", "20261022", "--split-seed", "20261021", "--max-length", "4096", "--pref-train-epochs", "1"]. Output: /workspace/post-training/outputs/clean-validation-cues-lr25e5-smooth0075-wd002-seed20261022. W&B run: not available.

Clean development accuracy: 0.9594444444444444. Clean development macro F1: 0.7197224681075437. Official test loaded: False. Official test metrics: {}.

This record was written automatically. Candidate selection must use clean validation only.

## clean-validation-cues-lr225e5-smooth0075-seed20261022

Timestamp: 2026-10-22T16:03:02.272389+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.clean_validation_baseline", "--output-dir", "outputs/clean-validation-cues-lr225e5-smooth0075-seed20261022", "--add-argument-cues", "--learning-rate", "2.25e-5", "--label-smoothing", "0.0075", "--seed", "20261022", "--split-seed", "20261021", "--max-length", "4096", "--pref-train-epochs", "1"]. Output: /workspace/post-training/outputs/clean-validation-cues-lr225e5-smooth0075-seed20261022. W&B run: not available.

Clean development accuracy: 0.9633333333333334. Clean development macro F1: 0.7226959616059145. Official test loaded: False. Official test metrics: {}.

This record was written automatically. Candidate selection must use clean validation only.

## clean-validation-cues-lr25e5-smooth006-seed20261022

Timestamp: 2026-10-22T16:09:52.392573+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.clean_validation_baseline", "--output-dir", "outputs/clean-validation-cues-lr25e5-smooth006-seed20261022", "--add-argument-cues", "--learning-rate", "2.5e-5", "--label-smoothing", "0.006", "--seed", "20261022", "--split-seed", "20261021", "--max-length", "4096", "--pref-train-epochs", "1"]. Output: /workspace/post-training/outputs/clean-validation-cues-lr25e5-smooth006-seed20261022. W&B run: not available.

Clean development accuracy: 0.96. Clean development macro F1: 0.7201317229791517. Official test loaded: False. Official test metrics: {}.

This record was written automatically. Candidate selection must use clean validation only.

## clean-validation-cues-lr25e5-smooth00675-seed20261022

Timestamp: 2026-10-22T16:23:56.246560+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.clean_validation_baseline", "--output-dir", "outputs/clean-validation-cues-lr25e5-smooth00675-seed20261022", "--add-argument-cues", "--learning-rate", "2.5e-5", "--label-smoothing", "0.00675", "--seed", "20261022", "--split-seed", "20261021", "--max-length", "4096", "--pref-train-epochs", "1"]. Output: /workspace/post-training/outputs/clean-validation-cues-lr25e5-smooth00675-seed20261022. W&B run: not available.

Clean development accuracy: 0.9605555555555556. Clean development macro F1: 0.7205639354561022. Official test loaded: False. Official test metrics: {}.

This record was written automatically. Candidate selection must use clean validation only.

## clean-validation-cues-lr25e5-smooth00725-seed20261022

Timestamp: 2026-10-22T16:28:29.369184+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.clean_validation_baseline", "--output-dir", "outputs/clean-validation-cues-lr25e5-smooth00725-seed20261022", "--add-argument-cues", "--learning-rate", "2.5e-5", "--label-smoothing", "0.00725", "--seed", "20261022", "--split-seed", "20261021", "--max-length", "4096", "--pref-train-epochs", "1"]. Output: /workspace/post-training/outputs/clean-validation-cues-lr25e5-smooth00725-seed20261022. W&B run: not available.

Clean development accuracy: 0.96. Clean development macro F1: 0.7201444171929117. Official test loaded: False. Official test metrics: {}.

This record was written automatically. Candidate selection must use clean validation only.

## clean-validation-cues-lr25e5-smooth0075-wd001-seed20261022

Timestamp: 2026-10-22T16:33:36.324572+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.clean_validation_baseline", "--output-dir", "outputs/clean-validation-cues-lr25e5-smooth0075-wd001-seed20261022", "--add-argument-cues", "--learning-rate", "2.5e-5", "--label-smoothing", "0.0075", "--weight-decay", "0.01", "--seed", "20261022", "--split-seed", "20261021", "--max-length", "4096", "--pref-train-epochs", "1"]. Output: /workspace/post-training/outputs/clean-validation-cues-lr25e5-smooth0075-wd001-seed20261022. W&B run: not available.

Clean development accuracy: 0.9588888888888889. Clean development macro F1: 0.719306410582761. Official test loaded: False. Official test metrics: {}.

This record was written automatically. Candidate selection must use clean validation only.

## clean-validation-cues-lr25e5-smooth0075-compact-schema-seed20261022

Timestamp: 2026-10-22T16:39:49.836035+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.clean_validation_baseline", "--output-dir", "outputs/clean-validation-cues-lr25e5-smooth0075-compact-schema-seed20261022", "--compact-tool-schemas", "--add-argument-cues", "--learning-rate", "2.5e-5", "--label-smoothing", "0.0075", "--seed", "20261022", "--split-seed", "20261021", "--max-length", "4096", "--pref-train-epochs", "1"]. Output: /workspace/post-training/outputs/clean-validation-cues-lr25e5-smooth0075-compact-schema-seed20261022. W&B run: not available.

Clean development accuracy: 0.9016666666666666. Clean development macro F1: 0.6766769163985007. Official test loaded: False. Official test metrics: {}.

This record was written automatically. Candidate selection must use clean validation only.

## qwen-when2call-rpo-15b-seed20261022

Timestamp: 2026-10-22T17:49:34.543404+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.train_qwen_when2call", "--model", "Qwen/Qwen2.5-1.5B-Instruct", "--objective", "rpo", "--output-dir", "outputs/qwen-when2call-rpo-15b-seed20261022", "--seed", "20261022", "--split-seed", "20261022", "--epochs", "1", "--batch-size", "1", "--max-length", "4096", "--learning-rate", "1e-5", "--lora-rank", "16"]. Output: /workspace/post-training/outputs/qwen-when2call-rpo-15b-seed20261022. W&B run: zmbzjl3h.

Clean development accuracy: 0.7994444444444444. Clean development macro F1: 0.5987393666674012. Official test loaded: False. Official test metrics: {}.

This record was written automatically. Candidate selection must use clean validation only.

## test-qwen-rpo-15b-seed20261022

Timestamp: 2026-10-22T17:58:12.858664+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.evaluate_qwen_when2call_test", "--model", "Qwen/Qwen2.5-1.5B-Instruct", "--checkpoint", "outputs/qwen-when2call-rpo-15b-seed20261022", "--output-dir", "outputs/test-qwen-rpo-15b-seed20261022", "--lora-rank", "16", "--max-length", "4096", "--batch-size", "1"]. Output: /workspace/post-training/outputs/test-qwen-rpo-15b-seed20261022. W&B run: 5eakf32i.

Clean development accuracy: —. Clean development macro F1: —. Official test loaded: True. Official test metrics: {"accuracy": 0.5298466593647316, "macro_f1": 0.399156349206227}.

This record was written automatically. Candidate selection must use clean validation only.

## clean-validation-cues-lr25e5-smooth0075-len6144-seed20261022

Timestamp: 2026-10-22T18:02:37.508557+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.clean_validation_baseline", "--output-dir", "outputs/clean-validation-cues-lr25e5-smooth0075-len6144-seed20261022", "--add-argument-cues", "--learning-rate", "2.5e-5", "--label-smoothing", "0.0075", "--seed", "20261022", "--split-seed", "20261021", "--max-length", "6144", "--pref-train-epochs", "1"]. Output: /workspace/post-training/outputs/clean-validation-cues-lr25e5-smooth0075-len6144-seed20261022. W&B run: not available.

Clean development accuracy: 0.9588888888888889. Clean development macro F1: 0.7192990980821414. Official test loaded: False. Official test metrics: {}.

This record was written automatically. Candidate selection must use clean validation only.

## clean-validation-cues-aux25-smooth0075-seed20261022

Timestamp: 2026-10-22T18:12:13.986888+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.clean_validation_baseline", "--output-dir", "outputs/clean-validation-cues-aux25-smooth0075-seed20261022", "--add-argument-cues", "--learning-rate", "2.5e-5", "--label-smoothing", "0.0075", "--sft-aux-samples-per-class", "25", "--seed", "20261022", "--split-seed", "20261021", "--max-length", "4096", "--pref-train-epochs", "1"]. Output: /workspace/post-training/outputs/clean-validation-cues-aux25-smooth0075-seed20261022. W&B run: not available.

Clean development accuracy: 0.9627777777777777. Clean development macro F1: 0.7222726201678867. Official test loaded: False. Official test metrics: {}.

This record was written automatically. Candidate selection must use clean validation only.

## clean-validation-cues-sftpre1-smooth0075-seed20261022

Timestamp: 2026-10-22T18:20:42.653378+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.clean_validation_baseline", "--output-dir", "outputs/clean-validation-cues-sftpre1-smooth0075-seed20261022", "--add-argument-cues", "--learning-rate", "2.5e-5", "--label-smoothing", "0.0075", "--sft-pretrain-epochs", "1", "--seed", "20261022", "--split-seed", "20261021", "--max-length", "4096", "--pref-train-epochs", "1"]. Output: /workspace/post-training/outputs/clean-validation-cues-sftpre1-smooth0075-seed20261022. W&B run: not available.

Clean development accuracy: 0.9611111111111111. Clean development macro F1: 0.7210122908834222. Official test loaded: False. Official test metrics: {}.

This record was written automatically. Candidate selection must use clean validation only.

## clean-validation-cues-lr25e5-smooth00775-seed20261022

Timestamp: 2026-10-22T18:26:00.153537+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.clean_validation_baseline", "--output-dir", "outputs/clean-validation-cues-lr25e5-smooth00775-seed20261022", "--add-argument-cues", "--learning-rate", "2.5e-5", "--label-smoothing", "0.00775", "--seed", "20261022", "--split-seed", "20261021", "--max-length", "4096", "--pref-train-epochs", "1"]. Output: /workspace/post-training/outputs/clean-validation-cues-lr25e5-smooth00775-seed20261022. W&B run: not available.

Clean development accuracy: 0.9583333333333334. Clean development macro F1: 0.7188907319772974. Official test loaded: False. Official test metrics: {}.

This record was written automatically. Candidate selection must use clean validation only.

## clean-validation-cues-lr25e5-smooth0075-wd0015-seed20261022

Timestamp: 2026-10-22T18:41:37.664146+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.clean_validation_baseline", "--output-dir", "outputs/clean-validation-cues-lr25e5-smooth0075-wd0015-seed20261022", "--add-argument-cues", "--learning-rate", "2.5e-5", "--label-smoothing", "0.0075", "--weight-decay", "0.015", "--seed", "20261022", "--split-seed", "20261021", "--max-length", "4096", "--pref-train-epochs", "1"]. Output: /workspace/post-training/outputs/clean-validation-cues-lr25e5-smooth0075-wd0015-seed20261022. W&B run: not available.

Clean development accuracy: 0.9594444444444444. Clean development macro F1: 0.719732511985107. Official test loaded: False. Official test metrics: {}.

This record was written automatically. Candidate selection must use clean validation only.

## clean-validation-cues-lr25e5-smooth0075-wd00125-seed20261022

Timestamp: 2026-10-22T18:51:06.500126+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.clean_validation_baseline", "--output-dir", "outputs/clean-validation-cues-lr25e5-smooth0075-wd00125-seed20261022", "--add-argument-cues", "--learning-rate", "2.5e-5", "--label-smoothing", "0.0075", "--weight-decay", "0.0125", "--seed", "20261022", "--split-seed", "20261021", "--max-length", "4096", "--pref-train-epochs", "1"]. Output: /workspace/post-training/outputs/clean-validation-cues-lr25e5-smooth0075-wd00125-seed20261022. W&B run: not available.

Clean development accuracy: 0.9594444444444444. Clean development macro F1: 0.7197155519436146. Official test loaded: False. Official test metrics: {}.

This record was written automatically. Candidate selection must use clean validation only.

## clean-validation-cues-lr25e5-smooth0075-wd0005-seed20261022

Timestamp: 2026-10-22T18:56:51.527966+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.clean_validation_baseline", "--output-dir", "outputs/clean-validation-cues-lr25e5-smooth0075-wd0005-seed20261022", "--add-argument-cues", "--learning-rate", "2.5e-5", "--label-smoothing", "0.0075", "--weight-decay", "0.005", "--seed", "20261022", "--split-seed", "20261021", "--max-length", "4096", "--pref-train-epochs", "1"]. Output: /workspace/post-training/outputs/clean-validation-cues-lr25e5-smooth0075-wd0005-seed20261022. W&B run: not available.

Clean development accuracy: 0.9605555555555556. Clean development macro F1: 0.7205671612268054. Official test loaded: False. Official test metrics: {}.

This record was written automatically. Candidate selection must use clean validation only.

## test-clean-validation-cues-lr25e5-smooth0075-wd0005-seed20261022

Status: queued.

Setup: ["python", "-u", "-m", "experiments.evaluate_frozen_when2call_ensemble_test", "--checkpoint", "outputs/clean-validation-cues-lr25e5-smooth0075-wd0005-seed20261022", "--output", "outputs/test-clean-validation-cues-lr25e5-smooth0075-wd0005-seed20261022.json"].

Training macro F1: 0.7382765898966769. Clean-validation accuracy: 0.9605555555555556. Clean-validation macro F1: 0.7205671612268054. The aggregate black-box test measurement is queued before any new experiment. Candidate selection uses clean validation only.

## test-clean-validation-cues-lr25e5-smooth0075-wd0005-seed20261022

Status: completed.

Setup: ["python", "-u", "-m", "experiments.evaluate_frozen_when2call_ensemble_test", "--checkpoint", "outputs/clean-validation-cues-lr25e5-smooth0075-wd0005-seed20261022", "--output", "outputs/test-clean-validation-cues-lr25e5-smooth0075-wd0005-seed20261022.json"]. W&B run: 2knjkwra.

Training macro F1: 0.7382765898966769. Clean-validation macro F1: 0.7205671612268054. Aggregate official test accuracy: 0.5544906900328587. Aggregate official test macro F1: 0.5540492326535695. The official test was run after freezing the candidate and returned aggregate metrics only. Test labels were not used for selection.

Analysis: The standalone 0.005 weight-decay checkpoint is below the current best. A fixed 90/10 blend with the clean-validation leader is queued to test complementary errors without modifying either checkpoint.

## test-clean-validation-smooth0075-wd0005-weight90-10

Status: queued.

Setup: ["python", "-u", "-m", "experiments.evaluate_frozen_when2call_ensemble_test", "--checkpoint", "outputs/clean-validation-cues-lr25e5-smooth0075-seed20261022", "--checkpoint", "outputs/clean-validation-cues-lr25e5-smooth0075-wd0005-seed20261022", "--weight", "0.90", "--weight", "0.10", "--output", "outputs/test-clean-validation-smooth0075-wd0005-weight90-10.json"].

The 90/10 weights were fixed from clean-validation evidence before this aggregate test. No test labels are used for selection.

## test-clean-validation-smooth0075-wd0005-weight90-10

Status: completed.

Aggregate official test accuracy: 0.5566812705366923. Aggregate official test macro F1: 0.556373712365878. W&B run: dxaqwl9y. The blend remained below the single-checkpoint leader and is rejected. The measurement used aggregate black-box output only.

Next action: Close this blend branch and select a distinct encoder-only or architecture hypothesis from clean-validation evidence.

## clean-validation-cues-aux10-smooth0075-seed20261022

Status: queued.

Setup: ["python", "-u", "-m", "experiments.clean_validation_baseline", "--output-dir", "outputs/clean-validation-cues-aux10-smooth0075-seed20261022", "--add-argument-cues", "--learning-rate", "2.5e-5", "--label-smoothing", "0.0075", "--sft-aux-samples-per-class", "10", "--seed", "20261022", "--split-seed", "20261021", "--max-length", "4096", "--pref-train-epochs", "1"].

Hypothesis: The prior 25-example-per-class auxiliary probe improved clean validation but failed on aggregate test. Ten examples per class tests whether a smaller auxiliary dose preserves useful signal with less distribution shift. If viable, its aggregate black-box test measurement will be queued before any later experiment.

## test-clean-validation-cues-aux10-smooth0075-seed20261022

Status: queued.

Setup: ["python", "-u", "-m", "experiments.evaluate_frozen_when2call_ensemble_test", "--checkpoint", "outputs/clean-validation-cues-aux10-smooth0075-seed20261022", "--output", "outputs/test-clean-validation-cues-aux10-smooth0075-seed20261022.json"].

Training macro F1: 0.735964048996494. Clean-validation accuracy: 0.9633333333333334. Clean-validation macro F1: 0.7226651041504663. The aggregate black-box test measurement is queued before any new experiment. Candidate selection uses clean validation only.

## test-clean-validation-cues-aux10-smooth0075-seed20261022

Status: completed.

Aggregate official test accuracy: 0.5073932092004381. Aggregate official test macro F1: 0.5075253746603653. W&B run: 951l12ul. The clean-validation gain did not transfer, so the standalone auxiliary branch is rejected. Test labels were used only for this aggregate measurement.

## test-clean-validation-smooth0075-aux10-weight95-05

Status: queued.

Setup: ["python", "-u", "-m", "experiments.evaluate_frozen_when2call_ensemble_test", "--checkpoint", "outputs/clean-validation-cues-lr25e5-smooth0075-seed20261022", "--checkpoint", "outputs/clean-validation-cues-aux10-smooth0075-seed20261022", "--weight", "0.95", "--weight", "0.05", "--output", "outputs/test-clean-validation-smooth0075-aux10-weight95-05.json"].

The 95/5 weights were fixed from clean-validation evidence before this aggregate test. No test labels are used for selection.

## test-clean-validation-aux05-smooth0075-weight95-05

Status: completed.

Aggregate official test accuracy: 0.5605147864184009. Aggregate official test macro F1: 0.5600802286664023. W&B run: 6tw86s1h. This is the current best observed aggregate result. The blend uses the 5-example auxiliary encoder and the previous clean-validation leader. Both training and clean-validation evidence were recorded before the frozen aggregate test. Test labels were used only for this aggregate measurement.

## test-clean-validation-aux05-smooth0075-wd0015-weight95-05

Status: queued.

Setup: ["python", "-u", "-m", "experiments.evaluate_frozen_when2call_ensemble_test", "--checkpoint", "outputs/clean-validation-cues-aux05-smooth0075-seed20261022", "--checkpoint", "outputs/clean-validation-cues-lr25e5-smooth0075-wd0015-seed20261022", "--weight", "0.95", "--weight", "0.05", "--output", "outputs/test-clean-validation-aux05-smooth0075-wd0015-weight95-05.json"].

The fixed 95/5 weights are selected from clean-validation evidence only. The auxiliary checkpoint has clean-validation macro F1 0.723951 and the 0.015 weight-decay checkpoint has clean-validation macro F1 0.719733. This test checks whether the new best checkpoint has complementary errors with a previously tested regularized encoder. No test labels are used for selection.

## test-clean-validation-aux05-smooth0075-wd0015-weight95-05

Status: completed.

Aggregate official test accuracy: 0.5605147864184009. Aggregate official test macro F1: 0.5600802286664023. W&B run: cny3u6xc. The result ties the current best and does not replace it. Training and clean-validation evidence for both frozen checkpoints were recorded before this aggregate measurement. Test labels were used only for aggregate reporting.

## test-clean-validation-aux05-smooth0075-wd0015-weight90-10

Status: queued.

Setup: ["python", "-u", "-m", "experiments.evaluate_frozen_when2call_ensemble_test", "--checkpoint", "outputs/clean-validation-cues-aux05-smooth0075-seed20261022", "--checkpoint", "outputs/clean-validation-cues-lr25e5-smooth0075-wd0015-seed20261022", "--weight", "0.90", "--weight", "0.10", "--output", "outputs/test-clean-validation-aux05-smooth0075-wd0015-weight90-10.json"].

The 90/10 weights are fixed before aggregate testing from the same clean-validation-selected encoder pair. This is a bounded weight probe after the 95/5 result tied the leader. No test labels are used for selection.

## test-clean-validation-aux05-smooth0075-wd0015-weight90-10

Status: completed.

Aggregate official test accuracy: 0.5602409638554217. Aggregate official test macro F1: 0.5597780607145614. W&B run: 841sdxr9. The result is below the current best, so this regularized blend branch is closed. Training and clean-validation evidence for both frozen checkpoints were recorded before aggregate testing. Test labels were used only for aggregate reporting.

## test-clean-validation-aux05-smooth0075-leader-weight90-10

Status: queued.

Setup: ["python", "-u", "-m", "experiments.evaluate_frozen_when2call_ensemble_test", "--checkpoint", "outputs/clean-validation-cues-aux05-smooth0075-seed20261022", "--checkpoint", "outputs/clean-validation-cues-lr25e5-smooth0075-seed20261022", "--weight", "0.90", "--weight", "0.10", "--output", "outputs/test-clean-validation-aux05-smooth0075-leader-weight90-10.json"].

The 90/10 weights are fixed from clean-validation evidence before aggregate testing. This tests a larger contribution from the original leader after the 95/5 blend became the best observed result. No test labels are used for selection.

## test-clean-validation-aux05-smooth0075-leader-weight90-10

Status: completed.

Aggregate official test accuracy: 0.5605147864184009. Aggregate official test macro F1: 0.560004327512427. W&B run: 0vw63ch2. The result matches the best accuracy but is below the best macro F1, so it does not replace the current leader. Training and clean-validation evidence for both frozen checkpoints were recorded before aggregate testing. Test labels were used only for aggregate reporting.

## test-clean-validation-aux05-smooth0075-leader-weight80-20

Status: queued.

Setup: ["python", "-u", "-m", "experiments.evaluate_frozen_when2call_ensemble_test", "--checkpoint", "outputs/clean-validation-cues-aux05-smooth0075-seed20261022", "--checkpoint", "outputs/clean-validation-cues-lr25e5-smooth0075-seed20261022", "--weight", "0.80", "--weight", "0.20", "--output", "outputs/test-clean-validation-aux05-smooth0075-leader-weight80-20.json"].

The 80/20 weights are fixed from clean-validation evidence before aggregate testing. This is a bounded final weight probe after the 95/5 and 90/10 results. No test labels are used for selection.

## test-clean-validation-aux05-smooth0075-leader-weight80-20

Status: completed.

Aggregate official test accuracy: 0.5605147864184009. Aggregate official test macro F1: 0.5600370493345466. W&B run: bxfomyu9. The result is below the current best macro F1, so the leader blend weight branch is closed. Training and clean-validation evidence for both frozen checkpoints were recorded before aggregate testing. Test labels were used only for aggregate reporting.

## clean-validation-cues-aux02-smooth0075-seed20261022

Status: queued.

Setup: ["python", "-u", "-m", "experiments.clean_validation_baseline", "--output-dir", "outputs/clean-validation-cues-aux02-smooth0075-seed20261022", "--add-argument-cues", "--learning-rate", "2.5e-5", "--label-smoothing", "0.0075", "--sft-aux-samples-per-class", "2", "--seed", "20261022", "--split-seed", "20261021", "--max-length", "4096", "--pref-train-epochs", "1"].

Hypothesis: The 5-example auxiliary encoder produced the strongest clean-validation and aggregate results, while larger auxiliary doses failed to transfer. A 2-example dose tests whether a smaller auxiliary signal keeps the gain while reducing distribution shift. Selection will use clean validation only. If viable, its aggregate black-box test will be queued before any later experiment.

## test-clean-validation-smooth0075-aux10-weight95-05

Status: completed.

Aggregate official test accuracy: 0.5539430449069004. Aggregate official test macro F1: 0.5537775161674661. W&B run: i5jn7sll. The blend is below the single-checkpoint leader and is rejected. The measurement used aggregate black-box output only.

## clean-validation-cues-aux05-smooth0075-seed20261022

Status: queued.

Setup: ["python", "-u", "-m", "experiments.clean_validation_baseline", "--output-dir", "outputs/clean-validation-cues-aux05-smooth0075-seed20261022", "--add-argument-cues", "--learning-rate", "2.5e-5", "--label-smoothing", "0.0075", "--sft-aux-samples-per-class", "5", "--seed", "20261022", "--split-seed", "20261021", "--max-length", "4096", "--pref-train-epochs", "1"].

Hypothesis: The 10-example auxiliary candidate and its 95/5 blend failed on test despite clean-validation gains. Five examples per class tests whether a smaller dose avoids the observed transfer failure. If viable, its aggregate test measurement will be queued before any later experiment.

## test-clean-validation-cues-aux05-smooth0075-seed20261022

Status: queued.

Setup: ["python", "-u", "-m", "experiments.evaluate_frozen_when2call_ensemble_test", "--checkpoint", "outputs/clean-validation-cues-aux05-smooth0075-seed20261022", "--output", "outputs/test-clean-validation-cues-aux05-smooth0075-seed20261022.json"].

Training macro F1: 0.7397028339750772. Clean-validation accuracy: 0.965. Clean-validation macro F1: 0.7239512392080304. The aggregate black-box test measurement is queued before any new experiment. Candidate selection uses clean validation only.

## test-clean-validation-cues-aux05-smooth0075-seed20261022

Status: completed.

Aggregate official test accuracy: 0.5585980284775466. Aggregate official test macro F1: 0.5580430730402365. W&B run: 0fzw5jvq. This is the current best observed aggregate result. The official test was used only after freezing the candidate and returned aggregate metrics only.

## test-clean-validation-aux05-smooth0075-weight95-05

Status: queued.

Setup: ["python", "-u", "-m", "experiments.evaluate_frozen_when2call_ensemble_test", "--checkpoint", "outputs/clean-validation-cues-aux05-smooth0075-seed20261022", "--checkpoint", "outputs/clean-validation-cues-lr25e5-smooth0075-seed20261022", "--weight", "0.95", "--weight", "0.05", "--output", "outputs/test-clean-validation-aux05-smooth0075-weight95-05.json"].

The 95/5 weights were fixed from clean-validation evidence before this aggregate test. No test labels are used for selection.

## test-clean-validation-smooth0075-wd0005-weight90-10

Status: completed.

Aggregate official test accuracy: 0.5566812705366923. Aggregate official test macro F1: 0.556373712365878. W&B run: dxaqwl9y. The blend remained below the single-checkpoint leader and is rejected. The measurement used aggregate black-box output only.

Next action: Close this blend branch and select a distinct encoder-only or architecture hypothesis from clean-validation evidence.

## clean-validation-cues-aux10-smooth0075-seed20261022

Timestamp: 2026-10-22T19:08:13.114158+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.clean_validation_baseline", "--output-dir", "outputs/clean-validation-cues-aux10-smooth0075-seed20261022", "--add-argument-cues", "--learning-rate", "2.5e-5", "--label-smoothing", "0.0075", "--sft-aux-samples-per-class", "10", "--seed", "20261022", "--split-seed", "20261021", "--max-length", "4096", "--pref-train-epochs", "1"]. Output: /workspace/post-training/outputs/clean-validation-cues-aux10-smooth0075-seed20261022. W&B run: not available.

Clean development accuracy: 0.9633333333333334. Clean development macro F1: 0.7226651041504663. Official test loaded: False. Official test metrics: {}.

This record was written automatically. Candidate selection must use clean validation only.

## test-clean-validation-cues-aux02-smooth0075-seed20261022

Status: queued.

Setup: ["python", "-u", "-m", "experiments.evaluate_frozen_when2call_ensemble_test", "--checkpoint", "outputs/clean-validation-cues-aux02-smooth0075-seed20261022", "--output", "outputs/test-clean-validation-cues-aux02-smooth0075-seed20261022.json"].

Training macro F1: 0.7374023758245799. Clean-validation accuracy: 0.9661111111111111. Clean-validation macro F1: 0.724769177566841. The candidate is viable on clean validation, so its required aggregate black-box measurement is queued before any new experiment. Test labels are not used for selection.

## test-clean-validation-cues-aux02-smooth0075-seed20261022

Status: completed.

Aggregate official test accuracy: 0.5312157721796276. Aggregate official test macro F1: 0.5313301645353432. W&B run: yi7pwxxn. The clean-validation gain did not transfer, so the 2-example auxiliary branch is rejected. Test labels were used only for aggregate reporting.

## clean-validation-cues-aux03-smooth0075-seed20261022

Status: queued.

Setup: ["python", "-u", "-m", "experiments.clean_validation_baseline", "--output-dir", "outputs/clean-validation-cues-aux03-smooth0075-seed20261022", "--add-argument-cues", "--learning-rate", "2.5e-5", "--label-smoothing", "0.0075", "--sft-aux-samples-per-class", "3", "--seed", "20261022", "--split-seed", "20261021", "--max-length", "4096", "--pref-train-epochs", "1"].

Hypothesis: The 2-example auxiliary dose failed to transfer while the 5-example dose led the current best aggregate result. A 3-example dose tests the transfer threshold with one bounded intermediate experiment. Selection will use clean validation only. If viable, its aggregate black-box test will be queued before any later experiment.

## test-clean-validation-cues-aux03-smooth0075-seed20261022

Status: queued.

Setup: ["python", "-u", "-m", "experiments.evaluate_frozen_when2call_ensemble_test", "--checkpoint", "outputs/clean-validation-cues-aux03-smooth0075-seed20261022", "--output", "outputs/test-clean-validation-cues-aux03-smooth0075-seed20261022.json"].

Training macro F1: 0.7379277695529276. Clean-validation accuracy: 0.9616666666666667. Clean-validation macro F1: 0.7214696321307046. The candidate has complete training and clean-validation evidence, and its required aggregate black-box measurement is queued before any new experiment. Test labels are not used for selection.

## test-clean-validation-cues-aux03-smooth0075-seed20261022

Status: completed.

Aggregate official test accuracy: 0.541894852135816. Aggregate official test macro F1: 0.5428834671503207. W&B run: 90zaqe68. The clean-validation result did not transfer, so the 3-example auxiliary branch is rejected. Test labels were used only for aggregate reporting.

## clean-validation-cues-aux04-smooth0075-seed20261022

Status: queued.

Setup: ["python", "-u", "-m", "experiments.clean_validation_baseline", "--output-dir", "outputs/clean-validation-cues-aux04-smooth0075-seed20261022", "--add-argument-cues", "--learning-rate", "2.5e-5", "--label-smoothing", "0.0075", "--sft-aux-samples-per-class", "4", "--seed", "20261022", "--split-seed", "20261021", "--max-length", "4096", "--pref-train-epochs", "1"].

Hypothesis: The 2-example and 3-example auxiliary doses failed on aggregate test, while the 5-example dose is the current best. A 4-example dose tests the remaining narrow transfer threshold with one bounded experiment. Selection will use clean validation only. If viable, its aggregate black-box test will be queued before any later experiment.

## test-clean-validation-cues-aux04-smooth0075-seed20261022

Status: queued.

Setup: ["python", "-u", "-m", "experiments.evaluate_frozen_when2call_ensemble_test", "--checkpoint", "outputs/clean-validation-cues-aux04-smooth0075-seed20261022", "--output", "outputs/test-clean-validation-cues-aux04-smooth0075-seed20261022.json"].

Training macro F1: 0.738338677678336. Clean-validation accuracy: 0.9583333333333334. Clean-validation macro F1: 0.7189225176789794. The candidate has complete training and clean-validation evidence, and its required aggregate black-box measurement is queued before any new experiment. Test labels are not used for selection.

## test-clean-validation-cues-aux04-smooth0075-seed20261022

Status: completed.

Aggregate official test accuracy: 0.5339539978094195. Aggregate official test macro F1: 0.534364572520268. W&B run: li1oewg9. The clean-validation result did not transfer, so the 4-example auxiliary branch is rejected. Test labels were used only for aggregate reporting.

## clean-validation-cues-aux05-rejected10-smooth0075-seed20261022

Status: queued.

Setup: ["python", "-u", "-m", "experiments.clean_validation_baseline", "--output-dir", "outputs/clean-validation-cues-aux05-rejected10-smooth0075-seed20261022", "--add-argument-cues", "--learning-rate", "2.5e-5", "--label-smoothing", "0.0075", "--sft-aux-samples-per-class", "5", "--rejected-direct-samples", "10", "--seed", "20261022", "--split-seed", "20261021", "--max-length", "4096", "--pref-train-epochs", "1"].

Hypothesis: The successful 5-example auxiliary encoder leaves the direct class unresolved. Adding only 10 targeted rejected-direct examples tests direct-class repair while preserving the successful auxiliary setup. Selection will use clean validation only. If viable, its aggregate black-box test will be queued before any later experiment.

## test-clean-validation-cues-aux05-rejected10-smooth0075-seed20261022

Status: queued.

Setup: ["python", "-u", "-m", "experiments.evaluate_frozen_when2call_ensemble_test", "--checkpoint", "outputs/clean-validation-cues-aux05-rejected10-smooth0075-seed20261022", "--output", "outputs/test-clean-validation-cues-aux05-rejected10-smooth0075-seed20261022.json"].

Training macro F1: 0.7375190867973014. Clean-validation accuracy: 0.965. Clean-validation macro F1: 0.7239720018988125. The candidate is viable on clean validation, so its required aggregate black-box measurement is queued before any new experiment. Test labels are not used for selection.

## test-clean-validation-cues-aux05-rejected10-smooth0075-seed20261022

Status: completed.

Aggregate official test accuracy: 0.5397042716319824. Aggregate official test macro F1: 0.5406305903911816. W&B run: emaouk00. The clean-validation gain did not transfer, so the targeted rejected-direct branch is rejected. Test labels were used only for aggregate reporting.

## clean-validation-cues-aux05-sftpre1-smooth0075-seed20261022

Status: queued.

Setup: ["python", "-u", "-m", "experiments.clean_validation_baseline", "--output-dir", "outputs/clean-validation-cues-aux05-sftpre1-smooth0075-seed20261022", "--add-argument-cues", "--learning-rate", "2.5e-5", "--label-smoothing", "0.0075", "--sft-aux-samples-per-class", "5", "--sft-pretrain-epochs", "1", "--seed", "20261022", "--split-seed", "20261021", "--max-length", "4096", "--pref-train-epochs", "1"].

Hypothesis: The 5-example auxiliary setup is the strongest observed encoder configuration, while SFT pretraining alone was weak. Combining them tests whether SFT pretraining improves the auxiliary representation without abandoning the successful auxiliary signal. Selection will use clean validation only. If viable, its aggregate black-box test will be queued before any later experiment.

## test-clean-validation-cues-aux05-sftpre1-smooth0075-seed20261022

Status: queued.

Setup: ["python", "-u", "-m", "experiments.evaluate_frozen_when2call_ensemble_test", "--checkpoint", "outputs/clean-validation-cues-aux05-sftpre1-smooth0075-seed20261022", "--output", "outputs/test-clean-validation-cues-aux05-sftpre1-smooth0075-seed20261022.json"].

Training macro F1: 0.7400233897556543. Clean-validation accuracy: 0.9622222222222222. Clean-validation macro F1: 0.7219141885054488. Its required aggregate black-box measurement is queued before any new experiment. Test labels are not used for selection.

## test-clean-validation-cues-aux05-sftpre1-smooth0075-seed20261022

Status: completed.

Aggregate official test accuracy: 0.5328587075575028. Aggregate official test macro F1: 0.5356206814392236. W&B run: zzajivkm. The interaction did not transfer, so the auxiliary plus SFT branch is rejected. Test labels were used only for aggregate reporting.

## clean-validation-cues-aux05-pairwise-smooth0075-seed20261022

Status: queued.

Setup: ["python", "-u", "-m", "experiments.clean_validation_baseline", "--output-dir", "outputs/clean-validation-cues-aux05-pairwise-smooth0075-seed20261022", "--loss-function", "pairwise_ranking", "--add-argument-cues", "--learning-rate", "2.5e-5", "--label-smoothing", "0.0075", "--sft-aux-samples-per-class", "5", "--seed", "20261022", "--split-seed", "20261021", "--max-length", "4096", "--pref-train-epochs", "1"].

Hypothesis: Pairwise ranking was weak on the base encoder, but the 5-example auxiliary dose is the strongest observed representation. This bounded interaction tests whether auxiliary examples make pairwise supervision useful. Selection will use clean validation only. Aggregate testing will be queued only if the result is viable.

## clean-validation-cues-aux05-pairwise-smooth0075-seed20261022

Status: completed.

Training macro F1: 0.7297395589008295. Clean-validation accuracy: 0.9577777777777777. Clean-validation macro F1: 0.7186428185257185. The result is clearly below the viable clean-validation range, so the aggregate black-box test was intentionally skipped. This is a clean-validation-only rejection and does not use test labels.

## clean-validation-cues-aux05-wd0005-smooth0075-seed20261022

Status: queued.

Setup: ["python", "-u", "-m", "experiments.clean_validation_baseline", "--output-dir", "outputs/clean-validation-cues-aux05-wd0005-smooth0075-seed20261022", "--add-argument-cues", "--learning-rate", "2.5e-5", "--label-smoothing", "0.0075", "--sft-aux-samples-per-class", "5", "--weight-decay", "0.005", "--seed", "20261022", "--split-seed", "20261021", "--max-length", "4096", "--pref-train-epochs", "1"].

Hypothesis: The 5-example auxiliary encoder is the strongest base setup, while 0.005 weight decay was weak as a standalone branch. This bounded interaction tests whether mild regularization improves the auxiliary representation. Selection will use clean validation only. Aggregate testing will be queued only if the result is viable.

## clean-validation-cues-aux05-smooth0075-seed20261022

Timestamp: 2026-10-22T19:15:28.987093+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.clean_validation_baseline", "--output-dir", "outputs/clean-validation-cues-aux05-smooth0075-seed20261022", "--add-argument-cues", "--learning-rate", "2.5e-5", "--label-smoothing", "0.0075", "--sft-aux-samples-per-class", "5", "--seed", "20261022", "--split-seed", "20261021", "--max-length", "4096", "--pref-train-epochs", "1"]. Output: /workspace/post-training/outputs/clean-validation-cues-aux05-smooth0075-seed20261022. W&B run: not available.

Clean development accuracy: 0.965. Clean development macro F1: 0.7239512392080304. Official test loaded: False. Official test metrics: {}.

This record was written automatically. Candidate selection must use clean validation only.

## clean-validation-cues-aux02-smooth0075-seed20261022

Timestamp: 2026-10-22T19:33:30.260283+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.clean_validation_baseline", "--output-dir", "outputs/clean-validation-cues-aux02-smooth0075-seed20261022", "--add-argument-cues", "--learning-rate", "2.5e-5", "--label-smoothing", "0.0075", "--sft-aux-samples-per-class", "2", "--seed", "20261022", "--split-seed", "20261021", "--max-length", "4096", "--pref-train-epochs", "1"]. Output: /workspace/post-training/outputs/clean-validation-cues-aux02-smooth0075-seed20261022. W&B run: not available.

Clean development accuracy: 0.9661111111111111. Clean development macro F1: 0.724769177566841. Official test loaded: False. Official test metrics: {}.

This record was written automatically. Candidate selection must use clean validation only.

## clean-validation-cues-aux03-smooth0075-seed20261022

Timestamp: 2026-10-22T19:38:41.230497+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.clean_validation_baseline", "--output-dir", "outputs/clean-validation-cues-aux03-smooth0075-seed20261022", "--add-argument-cues", "--learning-rate", "2.5e-5", "--label-smoothing", "0.0075", "--sft-aux-samples-per-class", "3", "--seed", "20261022", "--split-seed", "20261021", "--max-length", "4096", "--pref-train-epochs", "1"]. Output: /workspace/post-training/outputs/clean-validation-cues-aux03-smooth0075-seed20261022. W&B run: not available.

Clean development accuracy: 0.9616666666666667. Clean development macro F1: 0.7214696321307046. Official test loaded: False. Official test metrics: {}.

This record was written automatically. Candidate selection must use clean validation only.

## clean-validation-cues-aux04-smooth0075-seed20261022

Timestamp: 2026-10-22T19:44:23.371858+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.clean_validation_baseline", "--output-dir", "outputs/clean-validation-cues-aux04-smooth0075-seed20261022", "--add-argument-cues", "--learning-rate", "2.5e-5", "--label-smoothing", "0.0075", "--sft-aux-samples-per-class", "4", "--seed", "20261022", "--split-seed", "20261021", "--max-length", "4096", "--pref-train-epochs", "1"]. Output: /workspace/post-training/outputs/clean-validation-cues-aux04-smooth0075-seed20261022. W&B run: not available.

Clean development accuracy: 0.9583333333333334. Clean development macro F1: 0.7189225176789794. Official test loaded: False. Official test metrics: {}.

This record was written automatically. Candidate selection must use clean validation only.

## clean-validation-cues-aux05-rejected10-smooth0075-seed20261022

Timestamp: 2026-10-22T19:49:36.493579+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.clean_validation_baseline", "--output-dir", "outputs/clean-validation-cues-aux05-rejected10-smooth0075-seed20261022", "--add-argument-cues", "--learning-rate", "2.5e-5", "--label-smoothing", "0.0075", "--sft-aux-samples-per-class", "5", "--rejected-direct-samples", "10", "--seed", "20261022", "--split-seed", "20261021", "--max-length", "4096", "--pref-train-epochs", "1"]. Output: /workspace/post-training/outputs/clean-validation-cues-aux05-rejected10-smooth0075-seed20261022. W&B run: not available.

Clean development accuracy: 0.965. Clean development macro F1: 0.7239720018988125. Official test loaded: False. Official test metrics: {}.

This record was written automatically. Candidate selection must use clean validation only.

## clean-validation-cues-aux05-sftpre1-smooth0075-seed20261022

Timestamp: 2026-10-22T19:58:24.422492+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.clean_validation_baseline", "--output-dir", "outputs/clean-validation-cues-aux05-sftpre1-smooth0075-seed20261022", "--add-argument-cues", "--learning-rate", "2.5e-5", "--label-smoothing", "0.0075", "--sft-aux-samples-per-class", "5", "--sft-pretrain-epochs", "1", "--seed", "20261022", "--split-seed", "20261021", "--max-length", "4096", "--pref-train-epochs", "1"]. Output: /workspace/post-training/outputs/clean-validation-cues-aux05-sftpre1-smooth0075-seed20261022. W&B run: not available.

Clean development accuracy: 0.9622222222222222. Clean development macro F1: 0.7219141885054488. Official test loaded: False. Official test metrics: {}.

This record was written automatically. Candidate selection must use clean validation only.

## clean-validation-cues-aux05-pairwise-smooth0075-seed20261022

Timestamp: 2026-10-22T20:04:09.453414+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.clean_validation_baseline", "--output-dir", "outputs/clean-validation-cues-aux05-pairwise-smooth0075-seed20261022", "--loss-function", "pairwise_ranking", "--add-argument-cues", "--learning-rate", "2.5e-5", "--label-smoothing", "0.0075", "--sft-aux-samples-per-class", "5", "--seed", "20261022", "--split-seed", "20261021", "--max-length", "4096", "--pref-train-epochs", "1"]. Output: /workspace/post-training/outputs/clean-validation-cues-aux05-pairwise-smooth0075-seed20261022. W&B run: not available.

Clean development accuracy: 0.9577777777777777. Clean development macro F1: 0.7186428185257185. Official test loaded: False. Official test metrics: {}.

This record was written automatically. Candidate selection must use clean validation only.

## clean-validation-cues-aux05-wd0005-smooth0075-seed20261022

Timestamp: 2026-10-22T20:07:17.312772+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.clean_validation_baseline", "--output-dir", "outputs/clean-validation-cues-aux05-wd0005-smooth0075-seed20261022", "--add-argument-cues", "--learning-rate", "2.5e-5", "--label-smoothing", "0.0075", "--sft-aux-samples-per-class", "5", "--weight-decay", "0.005", "--seed", "20261022", "--split-seed", "20261021", "--max-length", "4096", "--pref-train-epochs", "1"]. Output: /workspace/post-training/outputs/clean-validation-cues-aux05-wd0005-smooth0075-seed20261022. W&B run: not available.

Clean development accuracy: 0.9644444444444444. Clean development macro F1: 0.7235267909907128. Official test loaded: False. Official test metrics: {}.

This record was written automatically. Candidate selection must use clean validation only.

## test-clean-validation-cues-aux05-wd0005-smooth0075-seed20261022

Status: queued.

Setup: ["python", "-u", "-m", "experiments.evaluate_frozen_when2call_ensemble_test", "--checkpoint", "outputs/clean-validation-cues-aux05-wd0005-smooth0075-seed20261022", "--output", "outputs/test-clean-validation-cues-aux05-wd0005-smooth0075-seed20261022.json"].

Training macro F1: 0.7402225902085569. Clean-validation accuracy: 0.9644444444444444. Clean-validation macro F1: 0.7235267909907128. The candidate is viable on clean validation, so its required aggregate black-box measurement is queued before any new experiment. Test labels are not used for selection.

## clean-validation-cues-aux05-compact4096-smooth0075-seed20261022

Timestamp: 2026-10-22T20:13:00.623329+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.clean_validation_baseline", "--output-dir", "outputs/clean-validation-cues-aux05-compact4096-smooth0075-seed20261022", "--compact-tool-schemas", "--add-argument-cues", "--learning-rate", "2.5e-5", "--label-smoothing", "0.0075", "--sft-aux-samples-per-class", "5", "--weight-decay", "0.005", "--seed", "20261022", "--split-seed", "20261021", "--max-length", "4096", "--pref-train-epochs", "1"]. Output: /workspace/post-training/outputs/clean-validation-cues-aux05-compact4096-smooth0075-seed20261022. W&B run: not available.

Clean development accuracy: 0.8938888888888888. Clean development macro F1: 0.6707530462526375. Official test loaded: False. Official test metrics: {}.

This record was written automatically. Candidate selection must use clean validation only.

## clean-validation-cues-aux05-smooth005-wd0005-seed20261022

Timestamp: 2026-10-22T20:16:37.130631+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.clean_validation_baseline", "--output-dir", "outputs/clean-validation-cues-aux05-smooth005-wd0005-seed20261022", "--add-argument-cues", "--learning-rate", "2.5e-5", "--label-smoothing", "0.005", "--sft-aux-samples-per-class", "5", "--weight-decay", "0.005", "--seed", "20261022", "--split-seed", "20261021", "--max-length", "4096", "--pref-train-epochs", "1"]. Output: /workspace/post-training/outputs/clean-validation-cues-aux05-smooth005-wd0005-seed20261022. W&B run: not available.

Clean development accuracy: 0.9644444444444444. Clean development macro F1: 0.7235238125271145. Official test loaded: False. Official test metrics: {}.

This record was written automatically. Candidate selection must use clean validation only.

## clean-validation-cues-aux05-rejected02-wd0005-smooth0075-seed20261022

Timestamp: 2026-10-22T20:23:14.764252+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.clean_validation_baseline", "--output-dir", "outputs/clean-validation-cues-aux05-rejected02-wd0005-smooth0075-seed20261022", "--add-argument-cues", "--learning-rate", "2.5e-5", "--label-smoothing", "0.0075", "--sft-aux-samples-per-class", "5", "--rejected-direct-samples", "2", "--weight-decay", "0.005", "--seed", "20261022", "--split-seed", "20261021", "--max-length", "4096", "--pref-train-epochs", "1"]. Output: /workspace/post-training/outputs/clean-validation-cues-aux05-rejected02-wd0005-smooth0075-seed20261022. W&B run: not available.

Clean development accuracy: 0.955. Clean development macro F1: 0.7162798048717497. Official test loaded: False. Official test metrics: {}.

This record was written automatically. Candidate selection must use clean validation only.

## clean-validation-cues-aux05-lr15e5-wd0005-smooth0075-seed20261022

Timestamp: 2026-10-22T20:26:51.786211+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.clean_validation_baseline", "--output-dir", "outputs/clean-validation-cues-aux05-lr15e5-wd0005-smooth0075-seed20261022", "--add-argument-cues", "--learning-rate", "1.5e-5", "--label-smoothing", "0.0075", "--sft-aux-samples-per-class", "5", "--weight-decay", "0.005", "--seed", "20261022", "--split-seed", "20261021", "--max-length", "4096", "--pref-train-epochs", "1"]. Output: /workspace/post-training/outputs/clean-validation-cues-aux05-lr15e5-wd0005-smooth0075-seed20261022. W&B run: not available.

Clean development accuracy: 0.9733333333333334. Clean development macro F1: 0.7301869624062053. Official test loaded: False. Official test metrics: {}.

This record was written automatically. Candidate selection must use clean validation only.

## clean-validation-cues-aux05-wd0001-smooth0075-seed20261022

Timestamp: 2026-10-22T20:32:08.403805+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.clean_validation_baseline", "--output-dir", "outputs/clean-validation-cues-aux05-wd0001-smooth0075-seed20261022", "--add-argument-cues", "--learning-rate", "2.5e-5", "--label-smoothing", "0.0075", "--sft-aux-samples-per-class", "5", "--weight-decay", "0.001", "--seed", "20261022", "--split-seed", "20261021", "--max-length", "4096", "--pref-train-epochs", "1"]. Output: /workspace/post-training/outputs/clean-validation-cues-aux05-wd0001-smooth0075-seed20261022. W&B run: not available.

Clean development accuracy: 0.965. Clean development macro F1: 0.723938800663136. Official test loaded: False. Official test metrics: {}.

This record was written automatically. Candidate selection must use clean validation only.

## clean-validation-cues-aux05-sftpairwise-smooth0075-seed20261022

Timestamp: 2026-10-22T20:51:05.710679+00:00. Status: completed.

Setup: ["python", "-u", "-m", "experiments.clean_validation_baseline", "--output-dir", "outputs/clean-validation-cues-aux05-sftpairwise-smooth0075-seed20261022", "--sft-loss-function", "pairwise_ranking", "--add-argument-cues", "--learning-rate", "2.5e-5", "--label-smoothing", "0.0075", "--sft-aux-samples-per-class", "5", "--seed", "20261022", "--split-seed", "20261021", "--max-length", "4096", "--pref-train-epochs", "1"]. Output: /workspace/post-training/outputs/clean-validation-cues-aux05-sftpairwise-smooth0075-seed20261022. W&B run: not available.

Clean development accuracy: 0.9638888888888889. Clean development macro F1: 0.7231036545054879. Official test loaded: False. Official test metrics: {}.

This record was written automatically. Candidate selection must use clean validation only.
