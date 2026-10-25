# When2Call research status

The best observed frozen combination is the existing single Jina checkpoint at seed 20261048 plus Qwen2.5 1.5B SFT through equal probability averaging. It scored 0.6946878422782037 official test accuracy and 0.5157041428790551 macro F1 across all four classes. Qwen alone scored 0.6788061336254108 accuracy and 0.5050116864318432 macro F1 under the same evaluator. The gain equals 58 additional correct predictions among 3652 examples.

The confidence gate also improved both metrics. The saved three-Jina encoder expert produced smaller hybrid gains. All four methods were frozen before the shared aggregate measurement. Each model was scored once. No per-example official outputs or correctness were saved. The complete comparison is in logs/leaderboard.md and logs/results.txt, with W&B run 0m0zb20q.

The next queued comparison uses the existing best single Jina checkpoint and Qwen SFT 1.5B. It compares fixed geometric probability pooling and equal Borda rank pooling against arithmetic averaging and entropy gating. No weights or thresholds are fitted. The queue runs manifest preparation first and one aggregate-only test evaluation second.

Historical encoder and Qwen F1 values used different absent-class conventions. The earlier cross-model F1 ranking was incorrect. New results use the same all-four-class definition and report a present-class diagnostic separately. The existing encoder preference validation is contaminated by its warm start and cannot fit a learned combiner. A read-only source audit found that a new calibration source still needs stronger provenance and target-label verification.
