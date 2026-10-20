# When2Call Research Summary

Current status: Active.

The repository contains When2Call classifiers based on Jina embeddings, MiniLM artifacts, Jev predictions, and rule based ensembles. Several historical experiments report official test accuracy and macro F1. The code also uses test labels to select routing rules and checkpoints. Those results are useful for diagnosis, but they are not valid evidence for clean model selection.

The clean protocol will split `train_pref` deterministically into training and development data. Training labels remain inferred from response content. Development labels are withheld from training and used only for validation. The official test set will remain untouched until the final frozen candidate.

The first experiment is a cheap baseline audit. It will measure class balance, label inference coverage, duplicate source identifiers, and the current checkpoint on the clean development split. The next comparison will test cross entropy against pairwise training under the same split.

Main known risks are noisy inferred training labels, train and evaluation target mismatch, class imbalance, long context truncation, and historical test leakage.

Experiment EXP-20261020-001 completed on 2026-10-20. A deterministic 80/20 split of 9,000 cached `train_pref` rows produced 7,200 training and 1,800 development examples. The warm started Jina model reached 0.936667 development accuracy and 0.703032 development macro F1. The development confusion matrix shows 27 `cannot_answer` examples predicted as `tool_call`, 41 `request_for_info` examples predicted as `tool_call` or `cannot_answer`, and 43 `tool_call` examples predicted as `request_for_info`. The single inferred `direct` example was missed.

Next action: compare cross entropy with pairwise preference training on the same split and checkpoint provenance. The likely high value bottleneck is separation of `request_for_info` and `tool_call`, but the direct class count is too small for a reliable class conclusion.
