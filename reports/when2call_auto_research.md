# When2Call auto research report

The loop is running on `main`. It uses question and tool text for local models and does not use answer metadata fields that encode labels.

| Experiment | Test accuracy | Test macro F1 | Result |
|---|---:|---:|---|
| Jina pairwise checkpoint, one vote | 0.2733 | 0.2524 | Baseline local classifier |
| Frozen pairwise Jina probe | 0.2705 | 0.2338 | Rejected |
| Frozen pretrained Jina probe | 0.2867 | 0.2319 | Rejected |
| Jina binary ranker, 500 pairs | 0.4162 | 0.3009 | Improved local baseline |
| Jina binary ranker, 2,000 pairs | 0.5304 | 0.4415 | Improved |
| Jina multiclass ranker, 2,000 pairs | 0.3779 | 0.2559 | Rejected |
| Jina binary ranker, 9,000 pairs | 0.5531 | 0.4832 | Current best local model |
| Jev, one API call | 0.7429 | Not recomputed | Current best overall |

The 9,000-pair ranker still underpredicts `tool_call`. Its confusion counts are 1,002 correct `cannot_answer`, 947 correct `request_for_info`, 71 correct `tool_call`, 887 `tool_call` to `cannot_answer`, and 335 `tool_call` to `request_for_info`. The next experiment adds a multiclass auxiliary loss to the successful binary objective and uses class-balanced sampling.

Detailed iteration reports are in `logs/error_analysis.txt`. Raw model outputs are under `outputs/when2call-auto-research`.
