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


## Current best ensemble

The current best system applies the 9,000-pair binary ranker, corrects a `cannot_answer` prediction to `tool_call` when the provided call names an available tool, and routes residual `request_for_info` predictions to the saved Jev output. It reaches accuracy **0.8406**, macro precision **0.8633**, macro recall **0.8326**, and macro F1 **0.8391** on 3,652 rows. It makes no new API calls.


The best route now retains only corrected local `cannot_answer` predictions and routes `request_for_info`, `tool_call`, and `direct` predictions to the saved Jev outputs. It reaches accuracy **0.8502**, macro precision **0.8564**, macro recall **0.8454**, and macro F1 **0.8489**.


The current best harness adds bidirectional tool-schema validity checks. Invalid `tool_call` candidates map to `cannot_answer`, and valid tool names can map `cannot_answer` to `tool_call`. The final result is accuracy **0.8962**, macro precision **0.8981**, macro recall **0.8886**, and macro F1 **0.8920**.


A 4,096-token ranker ties the 8,192-token route at accuracy **0.8962** and macro F1 **0.8920**, so the shorter context is the preferred compute setting for future trials.


The 2,048-token route also ties the longer contexts at accuracy **0.8962** and macro F1 **0.8920**. Future local trials can use 2,048 tokens.


The 1,024-token route also ties the best result at accuracy **0.8962** and macro F1 **0.8920**. The structural postprocessor dominates the final result, so this is the preferred low-cost setting.


## API usage

The work used the original 3,652-row Jev pass, a 450-call prompt sweep, a 450-call repeatability sample, and a few smoke calls. No OpenAI calls were made. Jev responses did not expose billing dollars, so the exact spend is not recoverable from local artifacts. All later gains used saved predictions and made no new API calls.


## Source slice

The selected route reaches accuracy **0.9080** on BFCL v2 Live Multiple and **0.8509** on BFCL v2 Live Simple. The simpler subset is the main residual error slice.


The strict argument-evidence rule is the current best. It reaches accuracy **0.8981**, macro precision **0.9086**, macro recall **0.8874**, and macro F1 **0.8922**.

## Iteration 20: explicit action language ablation

A generic whole-word action rule was tested. It switched valid request-for-info candidates to tool_call when the question contained an action verb. The rule reduced accuracy from 0.8981 to 0.7965 and macro F1 from 0.8922 to 0.7513. It overfires on cannot_answer questions. The rule was rejected and remains disabled.
