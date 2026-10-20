# When2Call Validation Leaderboard

Only the clean development split may be used for selection.

| Rank | Experiment | Accuracy | Macro F1 | Artifact | Status |
| --- | --- | ---: | ---: | --- | --- |
| 1 | EXP-20261020-001 clean Jina warm-start baseline | 0.936667 | 0.703032 | [metrics](../outputs/clean-validation-baseline/metrics.json) | Current |
| 1 | EXP-20261020-005 argument cues seed 20261021 | 0.948333 | 0.711410 | [metrics](../outputs/clean-validation-argument-cues-seed21/metrics.json) | Current best |
| 1 | EXP-20261020-006 training-only calibration | 0.949444 | 0.712267 | [metrics](../outputs/clean-validation-calibration.json) | Current best |
| 2 | EXP-20261020-004 argument cues seed 20261020 | 0.938889 | 0.704172 | [metrics](../outputs/clean-validation-argument-cues/metrics.json) | Replicated |
| 3 | EXP-20261020-009 argument cues seed 20261022 | 0.922222 | 0.691627 | [metrics](../outputs/clean-validation-argument-cues-seed22/metrics.json) | Negative replication |

Historical official test results remain in the existing logs. They are excluded from this leaderboard because previous selection used test labels or test metrics.
