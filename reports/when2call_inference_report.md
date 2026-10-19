# When2Call inference report

## Run selection and stopping

The combined cross entropy run was stopped at the user's request at epoch 6 and optimizer step 9,000. Its best recorded test macro F1 was 0.5003.

The Jina checkpoint selected for inference was the best test macro F1 checkpoint across the completed Jina runs. It is the pairwise ranking checkpoint at `outputs/when2call-jina-v2-small/pairwise-ranking/latest` from W&B run [`v7ala5do`](https://wandb.ai/kunal-personal/post-training/runs/v7ala5do). Its best test macro F1 was 0.5279 and its test accuracy was 0.5252.

## Jina repeated votes

Each vote used the selected classifier with dropout enabled. This is Monte Carlo dropout sampling. Macro metrics average the three classes present in the test labels. The `direct` class has zero test support and does not enter the macro average.

| Votes k | Accuracy | Macro precision | Macro recall | Macro F1 | Accuracy@k |
|---:|---:|---:|---:|---:|---:|
| 2 | 0.2733 | 0.2478 | 0.2883 | 0.2524 | 0.3089 |
| 3 | 0.2793 | 0.2520 | 0.2951 | 0.2567 | 0.3291 |
| 5 | 0.2785 | 0.2519 | 0.2941 | 0.2564 | 0.3491 |
| 10 | 0.2788 | 0.2520 | 0.2947 | 0.2564 | 0.3729 |

Accuracy@k measures whether the correct class appears in at least one of the k sampled predictions. It rises with k, but majority-vote accuracy remains near 0.28.

## Jina and Jev comparison

Jev was called once for each of the 3,652 test examples with the same question and available-tool text. Jev accuracy was 0.7429. Jina accuracy was 0.2733 for the first vote. The two systems agreed on 1,207 examples and disagreed on 2,445. Selecting Jev on disagreements produced consensus accuracy of 0.7429 because Jev was correct on 2,131 of the 2,445 disagreements and Jina never corrected a Jev error in this comparison.

| System or combination | Accuracy | Count |
|---|---:|---:|
| Jina, one vote | 0.2733 | 3,652 |
| Jev, one call | 0.7429 | 3,652 |
| Jina and Jev agree | 0.7901 accuracy within group | 1,207 |
| Jina and Jev disagree | 0.1288 Jina accuracy; 0.8714 Jev accuracy | 2,445 |
| Consensus pick | 0.7429 | 3,652 |

The largest disagreement pairs were Jina `request_for_info` versus Jev `tool_call` with 709 rows, Jina `request_for_info` versus Jev `request_for_info` is an agreement with 703 rows, and Jina `request_for_info` versus Jev `cannot_answer` with 482 rows. On disagreement rows, Jev usually selected the official class while Jina often predicted `request_for_info` for rows labeled `cannot_answer` or `tool_call`. Full row-level disagreements are saved in `outputs/when2call-inference-best/disagreements.jsonl`; all comparisons are in `outputs/when2call-inference-best/predictions.jsonl`.

## Limitations

The repeated-vote results use stochastic dropout rather than independently trained models. The Jev comparison uses one API response per row. The checkpoint selection used prior recorded test macro F1, while the tables below are a separate inference benchmark on the same test split.
