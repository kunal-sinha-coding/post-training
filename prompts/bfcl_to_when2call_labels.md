# Prompt: Label BFCL Live Examples for the When2Call Action Classifier

## Task

Read the complete BFCL example and assign the assistant's required action to one of the four When2Call labels. Use the conversation, system instructions, available function descriptions and schemas, BFCL category, and a reference call when one is provided. The category is evidence about the task structure. It is not the label by itself.

## When2Call action labels

Return exactly one action label:

- `A` (`direct`): The assistant can satisfy the request in ordinary text without calling an available function. This includes a general answer or a text-generation task that does not need external information or an external action.
- `B` (`tool_call`): At least one available function can satisfy the request, and the required arguments are stated or can be safely inferred from the conversation and system instructions.
- `C` (`request_for_info`): An available function can satisfy the request, but at least one required argument is missing and cannot be safely inferred. The assistant should ask for that information.
- `D` (`cannot_answer`): The assistant cannot responsibly satisfy the request from the conversation or general knowledge, and none of the available functions can satisfy it.

Do not use `D` just because no function should be called. Choose `A` when the assistant can answer directly. Choose `D` only when the request cannot be met without unavailable information or capability.

## BFCL category definitions

Use these definitions to understand what the BFCL example is designed to test:

- `Simple`: One function is available and one function call is expected.
- `Multiple`: More than one function is available and one function call is expected.
- `Parallel`: One function is available and multiple invocations are expected, usually with different arguments.
- `Parallel Multiple`: Multiple functions are available and multiple distinct function calls are expected.
- `Relevance`: At least one available function is relevant and a function call is expected. BFCL may not provide one canonical call because several valid calls can satisfy the request.
- `Irrelevance`: None of the available functions is relevant, so no function call is expected. The assistant may still answer directly, or it may be unable to answer. Decide between `A` and `D` from the request itself.

These categories do not replace the action-label definitions. For example, a call-oriented category can map to `C` if a required argument is genuinely missing. An Irrelevance example can map to `A` or `D`.

## Decision procedure

1. Read all system and user messages. Identify the user's actual request and any constraints.
2. Inspect the available function names, descriptions, required parameters, types, and constraints. Decide whether a function can fulfill the request.
3. If no function is needed and the assistant can answer in text, choose `A`.
4. If a suitable function exists and its required arguments are available or safely inferable, choose `B`.
5. If a suitable function exists but a required argument is missing and cannot be inferred, choose `C`.
6. If no suitable function exists and the assistant cannot responsibly answer directly, choose `D`.
7. Use the BFCL reference call, when provided, to check which function or functions BFCL expects and the expected call count. Do not assume that reference argument values were stated by the user. Verify each value against the conversation and system instructions.
8. Do not invent function capabilities, argument values, or missing context. If the best label remains uncertain, give the best-supported A/B/C/D label and set `needs_review` to `true` with a short reason.

## Required output

Return one JSON object and no other text:

```json
{
  "label": "A | B | C | D",
  "label_name": "direct | tool_call | request_for_info | cannot_answer",
  "confidence": "high | medium | low",
  "rationale": "Short explanation grounded in the request and available functions.",
  "expected_call_count": 0,
  "needs_review": false,
  "review_reason": null
}
```

Set `expected_call_count` from a BFCL reference answer when available. Use `0` for Irrelevance. Use `null` when BFCL gives no reference call. This field records task structure and does not change the four-way action label.

## Data and evaluation limits

Label only the BFCL training candidates that pass the source-ID and text-overlap audit. Do not use When2Call validation or test labels to create, revise, or select labels. Keep black-box test evaluation separate and report aggregate metrics only after the model and training procedure are fixed.
