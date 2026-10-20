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
