# When2Call Research Summary

Current status: Active.

The non-idle execution rule is active. A completed experiment must be followed immediately by analysis, durable logging, and the next experiment. The loop must continue until the exact top level message `STOP` is received.

The repository contains When2Call classifiers based on Jina embeddings, MiniLM artifacts, Jev predictions, and rule based ensembles. Several historical experiments report official test accuracy and macro F1. The code also uses test labels to select routing rules and checkpoints. Those results are useful for diagnosis, but they are not valid evidence for clean model selection.

The clean protocol will split `train_pref` deterministically into training and development data. Training labels remain inferred from response content. Development labels are withheld from training and used only for validation. The official test set will remain untouched until the final frozen candidate.

The first experiment is a cheap baseline audit. It will measure class balance, label inference coverage, duplicate source identifiers, and the current checkpoint on the clean development split. The next comparison will test cross entropy against pairwise training under the same split.

Main known risks are noisy inferred training labels, train and evaluation target mismatch, class imbalance, long context truncation, and historical test leakage.

Experiment EXP-20261020-001 completed on 2026-10-20. A deterministic 80/20 split of 9,000 cached `train_pref` rows produced 7,200 training and 1,800 development examples. The warm started Jina model reached 0.936667 development accuracy and 0.703032 development macro F1. The development confusion matrix shows 27 `cannot_answer` examples predicted as `tool_call`, 41 `request_for_info` examples predicted as `tool_call` or `cannot_answer`, and 43 `tool_call` examples predicted as `request_for_info`. The single inferred `direct` example was missed.

Next action: compare cross entropy with pairwise preference training on the same split and checkpoint provenance. The likely high value bottleneck is separation of `request_for_info` and `tool_call`, but the direct class count is too small for a reliable class conclusion.

EXP-20261020-002 rejected pairwise ranking. Development accuracy was 0.903889 and macro F1 was 0.678567. Cross entropy remains the current best. The next experiment audits inferred labels before changing the loss again.

The label audit found balanced chosen labels: 2,997 `cannot_answer`, 3,001 `request_for_info`, 3,000 `tool_call`, and 2 `direct`. Rejected responses contain 2,736 `direct` labels. This explains why raw pairwise ranking regressed and removes class weighting from the immediate plan. The next test will examine whether tool schema text causes shortcut errors.

EXP-20261020-003 rejected schema removal. Development accuracy was 0.590000 and macro F1 was 0.374995. Tool definitions are necessary evidence. The next experiment will preserve schemas and add explicit required argument names.

The required argument cue configuration improved both metrics across two seeds. The current best validation result is 0.948333 accuracy and 0.711410 macro F1. The next experiment will test calibration using a separate training calibration slice.

Training-only calibration improved the current result to 0.949444 accuracy and 0.712267 macro F1. The next experiment will test whether the selected bias is stable across the second argument cue seed.

Cross-seed calibration was unstable. It improved seed 20261021 but reduced seed 20261020 and selected the opposite bias. The calibrated rule is rejected as a general configuration. The uncalibrated argument cue model remains the reproducible candidate.

A larger calibration slice gave seed 20261020 a small local gain to 0.939444 accuracy and 0.704614 macro F1, but did not produce a shared calibration rule. The uncalibrated argument cue model remains the reproducible candidate for future comparisons.

The third argument cue seed regressed to 0.922222 accuracy and 0.691627 macro F1. The gain is split sensitive. The next action is a split stability audit using fixed model outputs.

The fixed-output audit showed that each checkpoint scored higher on partitions used by other runs. The earlier seed comparison changed both model training order and the validation partition. The next experiment fixes the split and varies only training seed.
