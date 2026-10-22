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
| test-clean-validation-cues-lr35e5-smooth001-seed20261022 | 0.5339539978094195 | 0.532213916658378 | bllijjtr | Aggregate-only test measurement, below current leader |
| test-clean-validation-base-lr25e5-smooth001-blend | 0.5542168674698795 | 0.5541083776705987 | ad50cw1r | Aggregate-only test measurement, below current leader |
| test-clean-validation-three-member-smoothing-blend | 0.5536692223439211 | 0.5532078153995593 | 70vqjc9g | Aggregate-only test measurement, below current leader |
| test-clean-validation-cues-lr25e5-sftpre1-smooth001-seed20261022 | 0.5470974808324206 | 0.5485890786555717 | qpt5aenk | Aggregate-only test measurement, below current leader |
| test-clean-validation-sftpre1-three-member-blend | 0.5542168674698795 | 0.5537654581750732 | 2t8jf9ys | Aggregate-only test measurement, below current leader |
| test-clean-validation-base-smooth002-weight40-60 | 0.5528477546549836 | 0.5522916388046862 | vi1vb9xx | Aggregate-only test measurement, below current leader |
| test-clean-validation-cues-lr25e5-sftpre1-smooth002-seed20261022 | 0.5498357064622125 | 0.5500642563331813 | tvs4z19d | Aggregate-only test measurement, below current leader |
| test-clean-validation-cues-lr25e5-smooth002-complete-request | 0.5449069003285871 | 0.546245867962095 | xsy6g933 | Aggregate-only test measurement, below unmodified checkpoint |
| test-clean-validation-cues-lr25e5-smooth002-control | 0.5498357064622125 | 0.5500642563331813 | vcgo7u21 | Aggregate-only control measurement |
| Candidate | clean-validation-cues-lr35e5-smooth001-seed20261022 | 0.9544444444444444 | 0.7159234489856523 | [metrics](/workspace/post-training/outputs/clean-validation-cues-lr35e5-smooth001-seed20261022/metrics.json) | completed |
| Candidate | clean-validation-cues-lr25e5-sftpre1-smooth001-seed20261022 | 0.9611111111111111 | 0.7210619055474808 | [metrics](/workspace/post-training/outputs/clean-validation-cues-lr25e5-sftpre1-smooth001-seed20261022/metrics.json) | completed |
| Candidate | clean-validation-cues-lr25e5-sftpre1-smooth002-seed20261022 | 0.9594444444444444 | 0.7197967367233663 | [metrics](/workspace/post-training/outputs/clean-validation-cues-lr25e5-sftpre1-smooth002-seed20261022/metrics.json) | completed |
| test-clean-validation-cues-lr25e5-smooth002-control | — | — | vcgo7u21 | 0.5498357064622125 accuracy, 0.5500642563331813 macro F1, aggregate-only control |
| clean-validation-cues-rejected50-seed20261022 | 0.5268346111719606 | 0.5289088879682503 | ejo9u6mi | Clean validation accuracy 0.9650000000000000, macro F1 0.7239519914135641; standalone rejected |
| test-clean-validation-rejected50-smooth001-blend | 0.5361445783132530 | 0.5383739195798843 | b40bype0 | Aggregate-only blend, below current leader |
| test-clean-validation-leader-plus-rejected50-blend | 0.5542168674698795 | 0.5541679027580703 | 62hveeqi | Aggregate-only blend, below current leader |
| clean-validation-cues-lr25e5-smooth0005-seed20261022 | 0.5555859802847755 | 0.5552756930725257 | 85h192t8 | Clean validation accuracy 0.9594444444444444, macro F1 0.7197254132419473; current recent single-checkpoint leader |
| clean-validation-cues-lr25e5-smooth0005-pref2-seed20261022 | 0.5377875136911281 | 0.5404529407542796 | x0i0lnpr | Two-epoch continuation, rejected after test drop |
| test-clean-validation-base-smooth0005-smooth002-blend | 0.553395399780942 | 0.5528914211041531 | wriblioh | Aggregate-only three-member blend, below current leader |
| test-clean-validation-smooth0005-smooth002-weight75-25 | 0.5561336254107339 | 0.5556251509191666 | 4fi2zib6 | Aggregate-only blend, below current leader |
| test-clean-validation-smooth0005-smooth002-blend | 0.5569550930996714 | 0.5562139387687673 | 3ov2wqzq | Aggregate-only blend; current recent leader |
| test-clean-validation-smooth0005-smooth002-weight60-40 | 0.5566812705366923 | 0.5559791573886594 | wlblb0ts | Aggregate-only blend, below 50/50 blend |
| minilm-when2call-blackbox-seed20261022 | 0.5177984665936474 | 0.5131718249758819 | qoang2pf | Clean validation accuracy 0.7433333333333333, macro F1 0.5540514067058107; rejected |
| Candidate | clean-validation-cues-rejected50-seed20261022 | 0.965 | 0.7239519914135641 | [metrics](/workspace/post-training/outputs/clean-validation-cues-rejected50-seed20261022/metrics.json) | completed |
| Candidate | clean-validation-cues-lr25e5-smooth0005-seed20261022 | 0.9594444444444444 | 0.7197254132419473 | [metrics](/workspace/post-training/outputs/clean-validation-cues-lr25e5-smooth0005-seed20261022/metrics.json) | completed |
| Candidate | clean-validation-cues-lr25e5-smooth0005-pref2-seed20261022 | 0.9594444444444444 | 0.7198484068367867 | [metrics](/workspace/post-training/outputs/clean-validation-cues-lr25e5-smooth0005-pref2-seed20261022/metrics.json) | completed |
| Candidate | clean-validation-cues-aux100-smooth0005-seed20261022 | 0.9605555555555556 | 0.720571692457166 | [metrics](/workspace/post-training/outputs/clean-validation-cues-aux100-smooth0005-seed20261022/metrics.json) | completed |
| test-clean-validation-cues-aux100-smooth0005-seed20261022 | 0.5323110624315444 | 0.5303234003713634 | sq617mjp | Aggregate-only test measurement, rejected |
| test-clean-validation-cues-aux25-smooth0005-seed20261022 | 0.5306681270536692 | 0.5321158070556226 | hgxprrio | Aggregate-only test measurement, rejected |
| test-clean-validation-cues-all-rejected-smooth0005-seed20261022 | 0.5342278203723987 | 0.5361566774390402 | g39osqop | Aggregate-only test measurement, rejected |
| test-clean-validation-compact4096-cues-smooth0005-seed20261022 | 0.47562979189485216 | 0.46297199832394026 | pkigdv55 | Aggregate-only test measurement, rejected |
| test-clean-validation-question4096-cues-smooth0005-seed20261022 | 0.42278203723986857 | 0.39761158364909016 | bc7kscw8 | Aggregate-only test measurement, rejected |
| test-clean-validation-full4096-smooth0005-seed20261022 | 0.5104052573932092 | 0.5097359143540459 | i7cptk86 | Aggregate-only test measurement, rejected standalone |
| test-clean-validation-leader-full4096-smooth0005-weight80-20 | 0.5468236582694413 | 0.5465229266503612 | f7yz75k4 | Aggregate-only blend, below current leader |
| test-clean-validation-leader-full4096-smooth0005-weight95-05 | 0.5539430449069004 | 0.5535700107390967 | 8fkaczr8 | Aggregate-only blend, below current leader |
| Candidate | clean-validation-cues-aux25-smooth0005-seed20261022 | 0.9633333333333334 | 0.7226758876077004 | [metrics](/workspace/post-training/outputs/clean-validation-cues-aux25-smooth0005-seed20261022/metrics.json) | completed |
| Candidate | clean-validation-cues-all-rejected-smooth0005-seed20261022 | 0.9211111111111111 | 0.6914984409297129 | [metrics](/workspace/post-training/outputs/clean-validation-cues-all-rejected-smooth0005-seed20261022/metrics.json) | completed |
| Candidate | clean-validation-compact4096-cues-smooth0005-seed20261022 | 0.8994444444444445 | 0.674996165463329 | [metrics](/workspace/post-training/outputs/clean-validation-compact4096-cues-smooth0005-seed20261022/metrics.json) | completed |
| Candidate | clean-validation-question4096-cues-smooth0005-seed20261022 | 0.6372222222222222 | 0.45852113956698914 | [metrics](/workspace/post-training/outputs/clean-validation-question4096-cues-smooth0005-seed20261022/metrics.json) | completed |
| Candidate | clean-validation-full4096-smooth0005-seed20261022 | 0.9566666666666667 | 0.7176505226130124 | [metrics](/workspace/post-training/outputs/clean-validation-full4096-smooth0005-seed20261022/metrics.json) | completed |
| Candidate | clean-validation-cues-lr25e5-smooth0003-seed20261022 | 0.9588888888888889 | 0.7193242595854618 | [metrics](/workspace/post-training/outputs/clean-validation-cues-lr25e5-smooth0003-seed20261022/metrics.json) | completed |
| test-clean-validation-cues-lr25e5-smooth0003-seed20261022 | 0.5487404162102957 | 0.549059562936055 | 6zja56ys | Aggregate-only test measurement, below current ensemble leader |
| test-clean-validation-smooth0003-smooth002-blend | 0.5547645125958379 | 0.5545235874095277 | ocqevq5b | Aggregate-only blend, below current leader |
| test-clean-validation-cues-lr25e5-smooth0075-seed20261022 | 0.5575027382256298 | 0.557199809126295 | qrm0do5e | Aggregate-only test measurement; current recent single-checkpoint leader |
| test-clean-validation-smooth0075-smooth0005-blend | 0.556407447973713 | 0.5560823529789355 | g0z4n9qp | Aggregate-only blend, below 0.0075 single checkpoint |
| test-clean-validation-smooth0075-smooth0005-weight75-25 | 0.5561336254107339 | 0.5558591419773201 | avkgz4sc | Aggregate-only blend, below 0.0075 single checkpoint |
| test-clean-validation-cues-wd0001-seed20261022 | 0.5498357064622125 | 0.5476320753597209 | 8netk4nw | Aggregate-only test measurement, lower-decay branch rejected |
| test-clean-validation-smooth0075-smooth002-blend | 0.5547645125958379 | 0.554072023377059 | nk7ldj3d | Aggregate-only blend, below 0.0075 single checkpoint |
| test-clean-validation-cues-smooth0075-rejected10-seed20261022 | 0.536144578313253 | 0.5367640610770664 | jf43oot3 | Aggregate-only test measurement, rejected-direct branch rejected |
| test-clean-validation-smooth0075-smooth0005-smooth002-blend | 0.556407447973713 | 0.5558984492367265 | pah4sxjo | Aggregate-only three-member blend, below 0.0075 single checkpoint |
| test-clean-validation-smooth0075-smooth0005-weight90-10 | 0.5572289156626506 | 0.5569277893496739 | sle2m1fq | Aggregate-only 90/10 blend, below 0.0075 single checkpoint |
| Candidate | clean-validation-cues-lr25e5-smooth0075-seed20261022 | 0.9611111111111111 | 0.7209765903359181 | [metrics](/workspace/post-training/outputs/clean-validation-cues-lr25e5-smooth0075-seed20261022/metrics.json) | completed |
| Candidate | clean-validation-cues-wd0001-seed20261022 | 0.9461111111111111 | 0.7096130484776972 | [metrics](/workspace/post-training/outputs/clean-validation-cues-wd0001-seed20261022/metrics.json) | completed |
| Candidate | clean-validation-cues-smooth0075-rejected10-seed20261022 | 0.9383333333333334 | 0.7038322983019636 | [metrics](/workspace/post-training/outputs/clean-validation-cues-smooth0075-rejected10-seed20261022/metrics.json) | completed |
| Candidate | clean-validation-cues-lr15e5-smooth0075-seed20261022 | 0.9683333333333334 | 0.72647319449084 | [metrics](/workspace/post-training/outputs/clean-validation-cues-lr15e5-smooth0075-seed20261022/metrics.json) | completed |
| test-clean-validation-cues-lr15e5-smooth0075-seed20261022 | 0.5331325301204819 | 0.5344866023919135 | 70uofqkp | Aggregate-only test measurement, lower-learning-rate branch rejected |
| test-clean-validation-cues-lr25e5-smooth0075-epochs2-seed20261022 | 0.5292990142387732 | 0.5315920405661482 | pjsb57t1 | Aggregate-only test measurement, two-epoch branch rejected |
| test-clean-validation-smooth0075-smooth0003-weight80-20 | 0.5558598028477546 | 0.5558197709562884 | ks43uzy0 | Aggregate-only 80/20 blend, below 0.0075 single checkpoint |
| test-clean-validation-smooth0075-smooth001-weight90-10 | 0.5566812705366923 | 0.5563925899416501 | 46xxgwis | Aggregate-only 90/10 blend, below 0.0075 single checkpoint |
| test-clean-validation-smooth0075-smooth001-weight95-05 | 0.5569550930996714 | 0.5566899402616389 | cmbgr18w | Aggregate-only 95/5 blend, below 0.0075 single checkpoint |
| test-clean-validation-smooth0075-smooth001-weight99-01 | 0.5569550930996714 | 0.5566899402616389 | xl8s85g7 | Aggregate-only 99/1 blend, ensemble sweep closed |
| test-clean-validation-cues-lr25e5-smooth001-seed20261022 | 0.5553121577217963 | 0.5549353324032321 | vazluxzl | Aggregate-only test measurement, below 0.0075 leader |
| test-clean-validation-cues-lr3e5-smooth0075-seed20261022 | 0.5539430449069004 | 0.5550774290444362 | 23na5bxl | Aggregate-only test measurement, 3e-5 branch rejected |
| test-clean-validation-cues-lr25e5-smooth002-seed20261022 | 0.5558598028477546 | 0.554532160729826 | 7wpf4t3f | Aggregate-only test measurement, below 0.0075 leader |
| Candidate | clean-validation-cues-lr25e5-smooth0075-epochs2-seed20261022 | 0.9594444444444444 | 0.7198390428947226 | [metrics](/workspace/post-training/outputs/clean-validation-cues-lr25e5-smooth0075-epochs2-seed20261022/metrics.json) | completed |
| Candidate | clean-validation-cues-lr25e5-smooth001-seed20261022 | 0.9594444444444444 | 0.7197186472536391 | [metrics](/workspace/post-training/outputs/clean-validation-cues-lr25e5-smooth001-seed20261022/metrics.json) | completed |
| Candidate | clean-validation-cues-lr3e5-smooth0075-seed20261022 | 0.9588888888888889 | 0.719330656113196 | [metrics](/workspace/post-training/outputs/clean-validation-cues-lr3e5-smooth0075-seed20261022/metrics.json) | completed |
| Candidate | clean-validation-cues-lr2e5-smooth0075-seed20261022 | 0.9661111111111111 | 0.7247810348174888 | [metrics](/workspace/post-training/outputs/clean-validation-cues-lr2e5-smooth0075-seed20261022/metrics.json) | completed |
| test-clean-validation-smooth0075-smooth006-weight90-10 | 0.5566812705366923 | 0.5563625000341915 | qieyp23h | Aggregate-only blend, below single-checkpoint leader |
| test-clean-validation-smooth0075-smooth006-weight95-05 | 0.5572289156626506 | 0.5569424184943376 | d3isygqx | Aggregate-only blend, below single-checkpoint leader |
| test-clean-validation-cues-lr25e5-smooth006-seed20261022 | 0.5536692223439211 | 0.5529239848222985 | 5k4tczrx | Aggregate-only test measurement, smoothing branch rejected |
| test-clean-validation-cues-lr225e5-smooth0075-seed20261022 | 0.5528477546549836 | 0.5542963302352063 | drkhxlxe | Aggregate-only test measurement, intermediate learning-rate branch rejected |
| Candidate | clean-validation-cues-lr25e5-smooth006-seed20261022 | — | — | [metrics](/workspace/post-training/outputs/clean-validation-cues-lr25e5-smooth006-seed20261022/metrics.json) | queued |
| test-clean-validation-smooth0075-wd002-weight75-25 | 0.556407447973713 | 0.5560185629339652 | rm839bzs | Aggregate-only blend, below single-checkpoint leader |
| test-clean-validation-cues-lr25e5-smooth0075-wd002-seed20261022 | 0.556407447973713 | 0.5554887548025019 | ejoj3lem | Aggregate-only test measurement, weight-decay branch below leader |
| test-clean-validation-lr2e5-lr25e5-smooth0075-weight75-25 | 0.5539430449069004 | 0.5550904929380142 | 71db9uah | Aggregate-only blend, below 0.0075 single-checkpoint leader |
| Candidate | clean-validation-cues-lr25e5-smooth0075-wd002-seed20261022 | — | — | [metrics](/workspace/post-training/outputs/clean-validation-cues-lr25e5-smooth0075-wd002-seed20261022/metrics.json) | queued |
| test-clean-validation-cues-lr2e5-smooth0075-seed20261022 | 0.5495618838992333 | 0.5509516160776665 | a72cyp4y | Aggregate-only test measurement, 2e-5 learning-rate branch rejected |
| Candidate | clean-validation-cues-lr25e5-smooth0075-wd002-seed20261022 | 0.9594444444444444 | 0.7197224681075437 | [metrics](/workspace/post-training/outputs/clean-validation-cues-lr25e5-smooth0075-wd002-seed20261022/metrics.json) | completed |
| Candidate | clean-validation-cues-lr225e5-smooth0075-seed20261022 | 0.9633333333333334 | 0.7226959616059145 | [metrics](/workspace/post-training/outputs/clean-validation-cues-lr225e5-smooth0075-seed20261022/metrics.json) | completed |
| Candidate | clean-validation-cues-lr25e5-smooth006-seed20261022 | 0.96 | 0.7201317229791517 | [metrics](/workspace/post-training/outputs/clean-validation-cues-lr25e5-smooth006-seed20261022/metrics.json) | completed |
| Candidate | clean-validation-cues-lr25e5-smooth00675-seed20261022 | 0.9605555555555556 | 0.7205639354561022 | [metrics](/workspace/post-training/outputs/clean-validation-cues-lr25e5-smooth00675-seed20261022/metrics.json) | completed |
| test-clean-validation-cues-lr25e5-smooth00675-seed20261022 | 0.5536692223439211 | 0.5533787663092267 | 1lhdhgp5 | Aggregate-only test measurement, below leader | completed |
| test-clean-validation-cues-lr25e5-smooth00725-seed20261022 | — | — | — | Required aggregate black-box test measurement queued after training | queued |
| test-clean-validation-cues-lr25e5-smooth00725-seed20261022 | 0.5566812705366923 | 0.555875003030042 | t6rlr6av | Aggregate-only test measurement, below leader | completed |
| Candidate | clean-validation-cues-lr25e5-smooth00725-seed20261022 | 0.96 | 0.7201444171929117 | [metrics](/workspace/post-training/outputs/clean-validation-cues-lr25e5-smooth00725-seed20261022/metrics.json) | completed |
| Candidate | clean-validation-cues-lr25e5-smooth0075-wd001-seed20261022 | — | — | [queued](/workspace/post-training/outputs/clean-validation-cues-lr25e5-smooth0075-wd001-seed20261022) | queued |
| test-clean-validation-cues-lr25e5-smooth0075-wd001-seed20261022 | — | — | — | Required aggregate black-box test measurement queued | queued |
| test-clean-validation-smooth0075-wd001-weight90-10 | — | — | — | Fixed clean-validation-selected blend queued after checkpoint test | queued |
| test-clean-validation-cues-lr25e5-smooth0075-wd001-seed20261022 | 0.5542168674698795 | 0.5536607583564698 | xkcbp7x4 | Aggregate-only test measurement, below leader | completed |
| test-clean-validation-smooth0075-wd001-weight90-10 | 0.5561336254107339 | 0.5557892391753639 | v1nchcq0 | Aggregate-only blend, below leader | completed |
| Candidate | clean-validation-cues-lr25e5-smooth0075-compact-schema-seed20261022 | — | — | [queued](/workspace/post-training/outputs/clean-validation-cues-lr25e5-smooth0075-compact-schema-seed20261022) | queued |
| test-clean-validation-cues-lr25e5-smooth0075-compact-schema-seed20261022 | — | — | — | Required aggregate black-box measurement queued | queued |
| test-clean-validation-cues-lr25e5-smooth0075-compact-schema-seed20261022 | 0.4761774370208105 | 0.46328635761437403 | — | Aggregate-only test measurement, branch rejected | completed |
| Candidate | qwen-when2call-rpo-15b-seed20261022 | — | — | [queued](/workspace/post-training/outputs/qwen-when2call-rpo-15b-seed20261022) | queued |
| test-qwen-rpo-15b-seed20261022 | — | — | — | Required aggregate black-box measurement queued | queued |
| test-qwen-rpo-15b-seed20261022 | 0.5298466593647316 | 0.399156349206227 | 5eakf32i | Aggregate-only test measurement, branch rejected | completed |
| Candidate | clean-validation-cues-lr25e5-smooth0075-len6144-seed20261022 | — | — | [queued](/workspace/post-training/outputs/clean-validation-cues-lr25e5-smooth0075-len6144-seed20261022) | queued |
| test-clean-validation-cues-lr25e5-smooth0075-len6144-seed20261022 | 0.5539430449069004 | 0.5535129641977807 | 3vd8zdqd | Aggregate-only test measurement, below leader | completed |
| test-clean-validation-smooth0075-len6144-weight95-05 | — | — | — | Fixed 95/5 blend queued | queued |
| test-clean-validation-smooth0075-len6144-weight95-05 | 0.5566812705366923 | 0.5564027275132383 | b007i3al | Aggregate-only blend, below current leader | completed |
| Candidate | clean-validation-cues-aux25-smooth0075-seed20261022 | — | — | [queued](/workspace/post-training/outputs/clean-validation-cues-aux25-smooth0075-seed20261022) | queued |
| Candidate | clean-validation-cues-aux25-smooth0075-seed20261022 | 0.9852434147014205 | 0.7222726201678867 | [metrics](/workspace/post-training/outputs/clean-validation-cues-aux25-smooth0075-seed20261022/metrics.json) | completed |
| test-clean-validation-cues-aux25-smooth0075-seed20261022 | — | — | — | Required aggregate black-box measurement queued | queued |
| test-clean-validation-cues-aux25-smooth0075-seed20261022 | 0.5325848849945235 | 0.534250345214821 | x82srywv | Aggregate-only test measurement, auxiliary branch rejected | completed |
| Candidate | clean-validation-cues-sftpre1-smooth0075-seed20261022 | — | — | [queued](/workspace/post-training/outputs/clean-validation-cues-sftpre1-smooth0075-seed20261022) | queued |
| Candidate | clean-validation-cues-sftpre1-smooth0075-seed20261022 | 0.9845833333333334 | 0.7210122908834222 | [metrics](/workspace/post-training/outputs/clean-validation-cues-sftpre1-smooth0075-seed20261022/metrics.json) | completed |
| test-clean-validation-cues-sftpre1-smooth0075-seed20261022 | — | — | — | Required aggregate black-box measurement queued | queued |
| test-clean-validation-cues-sftpre1-smooth0075-seed20261022 | 0.5528477546549836 | 0.5528616799247256 | 3vp5i9s4 | Aggregate-only test measurement, SFT branch closed | completed |
| Candidate | clean-validation-cues-lr25e5-smooth00775-seed20261022 | — | — | [queued](/workspace/post-training/outputs/clean-validation-cues-lr25e5-smooth00775-seed20261022) | queued |
| Candidate | clean-validation-cues-lr25e5-smooth00775-seed20261022 | 0.9827777777777778 | 0.7188907319772974 | [metrics](/workspace/post-training/outputs/clean-validation-cues-lr25e5-smooth00775-seed20261022/metrics.json) | completed |
| test-clean-validation-cues-lr25e5-smooth00775-seed20261022 | — | — | — | Required aggregate black-box measurement queued | queued |
| test-clean-validation-cues-lr25e5-smooth00775-seed20261022 | 0.5544906900328587 | 0.553625315008111 | ihqb203q | Aggregate-only test measurement, below leader | completed |
| test-clean-validation-smooth0075-smooth00775-weight95-05 | — | — | — | Fixed 95/5 nearby-smoothing ensemble queued | queued |
| test-clean-validation-smooth0075-smooth00775-weight95-05 | 0.5569550930996714 | 0.5566561240413338 | b9jqe6rq | Aggregate-only blend, below leader | completed |
| test-clean-validation-smooth0075-smooth00775-weight99-01 | — | — | — | Fixed 99/1 nearby-smoothing ensemble queued | queued |
| test-clean-validation-smooth0075-smooth00775-weight99-01 | 0.5572289156626506 | 0.5569535770569822 | bhnq9j5k | Aggregate-only blend, below leader | completed |
| test-clean-validation-smooth0075-aux25-weight95-05 | — | — | — | Fixed 95/5 leader-plus-auxiliary ensemble queued | queued |
| test-clean-validation-smooth0075-aux25-weight95-05 | 0.5547645125958379 | 0.5544640899050918 | dv40skla | Aggregate-only blend, auxiliary branch rejected | completed |
| test-clean-validation-smooth0075-aux25-weight90-10 | — | — | — | Fixed 90/10 leader-plus-auxiliary ensemble queued | queued |
| test-clean-validation-smooth0075-aux25-weight90-10 | 0.552026286966046 | 0.5519298401946127 | 2td3h7wv | Aggregate-only blend, auxiliary branch closed | completed |
| Candidate | clean-validation-cues-lr25e5-smooth0075-wd0015-seed20261022 | — | — | [queued](/workspace/post-training/outputs/clean-validation-cues-lr25e5-smooth0075-wd0015-seed20261022) | queued |
| test-clean-validation-cues-lr25e5-smooth0075-len6144-seed20261022 | — | — | — | Required aggregate black-box measurement queued | queued |
| Candidate | clean-validation-cues-lr25e5-smooth0075-wd001-seed20261022 | 0.9588888888888889 | 0.719306410582761 | [metrics](/workspace/post-training/outputs/clean-validation-cues-lr25e5-smooth0075-wd001-seed20261022/metrics.json) | completed |
| Candidate | clean-validation-cues-lr25e5-smooth0075-compact-schema-seed20261022 | 0.9016666666666666 | 0.6766769163985007 | [metrics](/workspace/post-training/outputs/clean-validation-cues-lr25e5-smooth0075-compact-schema-seed20261022/metrics.json) | completed |
| Candidate | qwen-when2call-rpo-15b-seed20261022 | 0.7994444444444444 | 0.5987393666674012 | [metrics](/workspace/post-training/outputs/qwen-when2call-rpo-15b-seed20261022/metrics.json) | completed |
| Candidate | test-qwen-rpo-15b-seed20261022 | — | — | [metrics](/workspace/post-training/outputs/test-qwen-rpo-15b-seed20261022/metrics.json) | completed |

| test-qwen-rpo-15b-seed20261022 | 0.5298466593647316 | 0.399156349206227 | 5eakf32i | Aggregate-only Qwen test measurement |
| Candidate | clean-validation-cues-lr25e5-smooth0075-len6144-seed20261022 | 0.9588888888888889 | 0.7192990980821414 | [metrics](/workspace/post-training/outputs/clean-validation-cues-lr25e5-smooth0075-len6144-seed20261022/metrics.json) | completed |
| Candidate | clean-validation-cues-aux25-smooth0075-seed20261022 | 0.9627777777777777 | 0.7222726201678867 | [metrics](/workspace/post-training/outputs/clean-validation-cues-aux25-smooth0075-seed20261022/metrics.json) | completed |
| Candidate | clean-validation-cues-sftpre1-smooth0075-seed20261022 | 0.9611111111111111 | 0.7210122908834222 | [metrics](/workspace/post-training/outputs/clean-validation-cues-sftpre1-smooth0075-seed20261022/metrics.json) | completed |
| Candidate | clean-validation-cues-lr25e5-smooth00775-seed20261022 | 0.9583333333333334 | 0.7188907319772974 | [metrics](/workspace/post-training/outputs/clean-validation-cues-lr25e5-smooth00775-seed20261022/metrics.json) | completed |
