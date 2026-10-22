# When2Call Validation and Official Test Leaderboard

Only the clean development split may be used for selection. Official test metrics are measured only after a candidate is frozen and are never used to select or tune later candidates.

## Clean development results used for selection

| Rank | Experiment | Accuracy | Macro F1 | Artifact | Test status | Status |
| --- | --- | ---: | ---: | --- | --- | --- |
| 1 | EXP-20261020-006 training-only calibration | 0.949444 | 0.712267 | [metrics](../outputs/clean-validation-calibration.json) | Not measured | Current best |
| 2 | EXP-20261020-005 argument cues seed 20261021 | 0.948333 | 0.711410 | [metrics](../outputs/clean-validation-argument-cues-seed21/metrics.json) | Not measured | Current |
| 3 | EXP-20261020-004 argument cues seed 20261020 | 0.938889 | 0.704172 | [metrics](../outputs/clean-validation-argument-cues/metrics.json) | Not measured | Replicated |
| 4 | EXP-20261020-001 clean Jina warm-start baseline | 0.936667 | 0.703032 | [metrics](../outputs/clean-validation-baseline/metrics.json) | Not measured | Current |
| 5 | EXP-20261020-009 argument cues seed 20261022 | 0.922222 | 0.691627 | [metrics](../outputs/clean-validation-argument-cues-seed22/metrics.json) | Not measured | Negative replication |
| Candidate | qwen-sft-15b-seed20261022 | 0.89444 | 0.67099 | [metrics](/workspace/post-training/outputs/qwen-when2call-sft-15b-seed20261022/metrics.json) | Not measured | Completed |
| Candidate | qwen-sft-05b-seed20261022 | 0.87444 | 0.65687 | [metrics](/workspace/post-training/outputs/qwen-when2call-sft-05b-seed20261022/metrics.json) | Not measured | Completed |
| Candidate | qwen-rpo-05b-seed20261022 | 0.83222 | 0.62484 | [metrics](/workspace/post-training/outputs/qwen-when2call-rpo-05b-seed20261022/metrics.json) | Not measured | Completed |
| Candidate | qwen-rl-05b-seed20261022 | 0.79222 | 0.56393 | [metrics](/workspace/post-training/outputs/qwen-when2call-rl-05b-seed20261022/metrics.json) | Not measured | Completed |

## Official aggregate-only test results

These measurements were collected after candidate freezing. They are not used for candidate selection. A dash means that no test measurement has been run.

| Candidate | Test accuracy | Test macro F1 | W&B test run | Selection boundary |
| --- | ---: | ---: | --- | --- |
| EXP-20261020-006 training-only calibration | — | — | — | Current validation leader, not measured |
| Qwen2.5-1.5B-Instruct SFT | — | — | m1rg8d6l is the training run, not a test run | Best Qwen validation candidate, not measured |
| EXP-20261020-056 Jina staged SFT plus preference plus smoothing | 0.574480 | 0.574969 | [f3fl4i4c](https://forge.coreweave.com/wandb/kunal-personal/when2call-research/runs/f3fl4i4c) | Historical test leader, held-out validation not available because all 9,000 labeled rows were used |

Historical official test results remain detailed in [research_log.md](research_log.md). The historical test leader was selected under an earlier protocol that did not maintain the current clean-validation boundary, so it is reported for reference and not ranked with the current validation candidates.
| Candidate | qwen-when2call-sft-15b-2ep-seed20261022 | — | — | [metrics](/workspace/post-training/outputs/qwen-when2call-sft-15b-2ep-seed20261022/metrics.json) | failed_or_incomplete |
| Candidate | qwen-when2call-sft-15b-lr1e5-seed20261022 | 0.8711111111111111 | 0.6540315541682907 | [metrics](/workspace/post-training/outputs/qwen-when2call-sft-15b-lr1e5-seed20261022/metrics.json) | completed |
| Candidate | test-qwen-sft-05b-seed20261022 | — | — | [metrics](/workspace/post-training/outputs/test-qwen-sft-05b-seed20261022/metrics.json) | completed |

| test-qwen-sft-05b-seed20261022 | 0.5958378970427163 | 0.4232188202379165 | w944h7e8 | Aggregate-only Qwen test measurement |
| Candidate | test-qwen-sft-15b-seed20261022 | — | — | [metrics](/workspace/post-training/outputs/test-qwen-sft-15b-seed20261022/metrics.json) | completed |

| test-qwen-sft-15b-seed20261022 | 0.6788061336254108 | 0.5050116864318432 | vefoyfhf | Aggregate-only Qwen test measurement |
| Candidate | test-qwen-rpo-05b-seed20261022 | — | — | [metrics](/workspace/post-training/outputs/test-qwen-rpo-05b-seed20261022/metrics.json) | completed |

| test-qwen-rpo-05b-seed20261022 | 0.5813253012048193 | 0.4273368362156368 | 8v90395u | Aggregate-only Qwen test measurement |
| Candidate | test-qwen-rl-05b-seed20261022 | — | — | [metrics](/workspace/post-training/outputs/test-qwen-rl-05b-seed20261022/metrics.json) | completed |

| test-qwen-rl-05b-seed20261022 | 0.5648959474260679 | 0.42326700764133907 | g1lggfyw | Aggregate-only Qwen test measurement |
| Candidate | test-qwen-sft-15b-lr1e5-seed20261022 | — | — | [metrics](/workspace/post-training/outputs/test-qwen-sft-15b-lr1e5-seed20261022/metrics.json) | completed |

| test-qwen-sft-15b-lr1e5-seed20261022 | 0.6297918948521358 | 0.4587653046615539 | lzvvcnfp | Aggregate-only Qwen test measurement |
| Candidate | qwen-when2call-sft-05b-2ep-seed20261022 | — | — | [metrics](/workspace/post-training/outputs/qwen-when2call-sft-05b-2ep-seed20261022/metrics.json) | failed_or_incomplete |
| Candidate | test-qwen-sft-15b-2ep-seed20261022 | — | — | [metrics](/workspace/post-training/outputs/test-qwen-sft-15b-2ep-seed20261022/metrics.json) | completed |

| test-qwen-sft-15b-2ep-seed20261022 | 0.6514238773274917 | 0.46092686327503485 | vbdutodo | Aggregate-only Qwen test measurement |
| Candidate | clean-validation-cues-seed20261022 | 0.9388888888888889 | 0.7042109139304156 | [metrics](/workspace/post-training/outputs/clean-validation-cues-seed20261022/metrics.json) | completed |
| Candidate | clean-validation-compact-2048-seed20261022 | — | — | [metrics](/workspace/post-training/outputs/clean-validation-compact-2048-seed20261022/metrics.json) | failed_or_incomplete |
| Candidate | clean-validation-compact-2048-seed20261022 | 0.8294444444444444 | 0.6212644631405057 | [metrics](/workspace/post-training/outputs/clean-validation-compact-2048-seed20261022/metrics.json) | completed |
| Candidate | clean-validation-full-2048-smooth005-seed20261022 | — | — | [metrics](/workspace/post-training/outputs/clean-validation-full-2048-smooth005-seed20261022/metrics.json) | failed_or_incomplete |
| Candidate | clean-validation-question-2048-smooth005-seed20261022 | 0.5905555555555555 | 0.4272945672381965 | [metrics](/workspace/post-training/outputs/clean-validation-question-2048-smooth005-seed20261022/metrics.json) | completed |
| Candidate | clean-validation-pairwise-cues-seed20261022 | 0.915 | 0.6857616478914805 | [metrics](/workspace/post-training/outputs/clean-validation-pairwise-cues-seed20261022/metrics.json) | completed |
| Candidate | clean-validation-cues-smooth002-seed20261022 | 0.9405555555555556 | 0.7055713243319585 | [metrics](/workspace/post-training/outputs/clean-validation-cues-smooth002-seed20261022/metrics.json) | completed |
| Candidate | clean-validation-cues-wd005-seed20261022 | 0.935 | 0.7016421857214856 | [metrics](/workspace/post-training/outputs/clean-validation-cues-wd005-seed20261022/metrics.json) | completed |
| Candidate | clean-validation-cues-sftpre1-seed20261022 | 0.945 | 0.7089487218519661 | [metrics](/workspace/post-training/outputs/clean-validation-cues-sftpre1-seed20261022/metrics.json) | completed |
| Candidate | clean-validation-cues-len8192-seed20261022 | 0.9344444444444444 | 0.7011448404944383 | [metrics](/workspace/post-training/outputs/clean-validation-cues-len8192-seed20261022/metrics.json) | completed |
| Candidate | clean-validation-compact-4096-seed20261022 | 0.8783333333333333 | 0.6593892555894565 | [metrics](/workspace/post-training/outputs/clean-validation-compact-4096-seed20261022/metrics.json) | completed |
| Candidate | clean-validation-cues-sftpairwise-seed20261022 | 0.9288888888888889 | 0.6973110405998094 | [metrics](/workspace/post-training/outputs/clean-validation-cues-sftpairwise-seed20261022/metrics.json) | completed |
| Candidate | clean-validation-cues-sftsmooth002-seed20261022 | — | — | [metrics](/workspace/post-training/outputs/clean-validation-cues-sftsmooth002-seed20261022/metrics.json) | failed_or_incomplete |
| Candidate | clean-validation-cues-sftsmooth002-seed20261022 | 0.9216666666666666 | 0.6922046717292848 | [metrics](/workspace/post-training/outputs/clean-validation-cues-sftsmooth002-seed20261022/metrics.json) | completed |
| test-clean-validation-cues-sftsmooth002-seed20261022 | 0.5432639649507119 | 0.5442518795459972 | ymdpwtrh | Aggregate-only test measurement |
| test-clean-validation-argument-cues-seed21 | 0.537513691128149 | 0.5390601515339869 | emfbfg60 | Aggregate-only test measurement |
| test-clean-validation-three-member-clean-selected | 0.5495618838992333 | 0.55092406368306 | kufawwcd | Aggregate-only test measurement |
| test-clean-validation-cues-wd0005-seed20261022 | 0.5210843373493976 | 0.5221766573591942 | guz4zrfl | Aggregate-only test measurement |
| test-clean-validation-cues-lr25e5-seed20261022 | 0.5460021905805038 | 0.5466183186540272 | abwm67cs | Aggregate-only test measurement |
| test-clean-validation-lr25e5-three-member | 0.547645125958379 | 0.5483385906271478 | u132g828 | Aggregate-only test measurement |
| Candidate | clean-validation-cues-wd0005-seed20261022 | 0.9433333333333334 | 0.70767933046275 | [metrics](/workspace/post-training/outputs/clean-validation-cues-wd0005-seed20261022/metrics.json) | completed |
| Candidate | clean-validation-cues-lr25e5-seed20261022 | 0.9588888888888889 | 0.7193348010015539 | [metrics](/workspace/post-training/outputs/clean-validation-cues-lr25e5-seed20261022/metrics.json) | completed |
| Candidate | clean-validation-cues-lr25e5-smooth002-seed20261022 | 0.9583333333333334 | 0.718887236467644 | [metrics](/workspace/post-training/outputs/clean-validation-cues-lr25e5-smooth002-seed20261022/metrics.json) | completed |
| test-clean-validation-cues-lr25e5-smooth002-seed20261022 | 0.5558598028477546 | 0.554532160729826 | 488ggz5g | Aggregate-only test measurement |
| Candidate | clean-validation-cues-lr25e5-smooth001-seed20261022 | 0.9594444444444444 | 0.7197261438751257 | [metrics](/workspace/post-training/outputs/clean-validation-cues-lr25e5-smooth001-seed20261022/metrics.json) | completed |
| test-clean-validation-cues-lr25e5-smooth001-seed20261022 | 0.5553121577217963 | 0.5549353324032321 | vazluxzl | Aggregate-only test measurement |
| test-clean-validation-lr25e5-smoothing-blend | 0.5550383351588171 | 0.5543185329447103 | hlcorjpt | Aggregate-only test measurement, below current leader |
