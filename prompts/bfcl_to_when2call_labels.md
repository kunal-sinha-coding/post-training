# Prompt: Label BFCL Live Examples for the When2Call Action Classifier

## Task

Read one complete BFCL Live example and select the required assistant action from the When2Call four-way label set. Use the conversation, system instructions, visible function descriptions and schemas, BFCL category, and a reference call when provided. Apply a category only when it describes this exact question and visible function list.

## When2Call action labels

Return exactly one action label:

- `A` (`direct`): The assistant can satisfy the request in ordinary text without an available function. This includes general knowledge answers and text generation that do not need external information or an external action.
- `B` (`tool_call`): A visible function can perform the requested operation, and every required argument is stated or can be safely inferred from the conversation and system instructions.
- `C` (`request_for_info`): A visible function can perform the requested operation, but a required argument is missing and cannot be safely inferred. The user can reasonably provide the missing value.
- `D` (`cannot_answer`): No visible function can perform the requested operation, and the assistant cannot responsibly satisfy the request directly. This includes requests that need unavailable live, private, transactional, or physical capabilities.

Do not choose `C` only because a function is vaguely related to the topic. The function must perform the requested operation. Do not choose `D` when the assistant can answer directly without a function.

## BFCL categories

The category describes the function-call structure expected for the BFCL example:

- `Simple`: One function is available and one call is expected.
- `Multiple`: More than one function is available and one call is expected.
- `Parallel`: One function is available and multiple invocations are expected.
- `Parallel Multiple`: Multiple functions are available and multiple distinct calls are expected.
- `Relevance`: At least one visible function is relevant and a call is expected. BFCL may allow several valid calls and provide no single canonical call.
- `Irrelevance`: No visible function is relevant, so no function call is expected.

## Category rules

- For `Simple`, `Multiple`, `Parallel`, `Parallel Multiple`, and `Relevance`, choose `B` when the required values are available. Choose `C` only when the function can perform the requested operation but a required user value is missing.
- For `Irrelevance`, choose `A` if the assistant can answer in text. Choose `D` if the request still cannot be met. Never choose `B` or `C` for a valid Irrelevance example.
- These rules apply only when the category matches the question and visible functions. A transformed example may have a changed function list. Do not infer that the original BFCL category still applies from a source ID alone. If the category conflicts with the visible example, set `needs_review` to `true`, explain the conflict, and label the action from the visible request and functions.

## Decision procedure

1. Read every system and user message. Identify the requested operation and constraints.
2. Check each visible function's documented purpose, required parameters, types, defaults, and constraints.
3. Choose `A` if no function is needed and the request can be answered directly.
4. Choose `B` only if a suitable visible function can perform the requested operation and its required arguments are available or safely inferable. A schema default counts as available. Never invent an identifier or other required value.
5. Choose `C` only if a suitable visible function can perform the operation after the user supplies a specific missing required value.
6. Choose `D` if no visible function can perform the operation and a direct answer would require unavailable information or capability.
7. Use BFCL reference calls, when provided, to identify the intended function and expected call count. A reference argument value is not proof that the user supplied that value. Check the conversation.
8. If evidence conflicts or remains unclear, return the best-supported action label and set `needs_review` to `true` with a short reason.

## Required output

Return one JSON object and no other text:

```json
{
  "label": "A | B | C | D",
  "label_name": "direct | tool_call | request_for_info | cannot_answer",
  "confidence": "high | medium | low",
  "rationale": "Short explanation grounded in the request and visible functions.",
  "expected_call_count": 0,
  "needs_review": false,
  "review_reason": null
}
```

Set `expected_call_count` from a BFCL reference call when available. Use `1` for `Simple`, `Multiple`, and `Relevance` when no exact count is given. Use the reference count for `Parallel` and `Parallel Multiple`. Use `0` for `Irrelevance`. Use `null` if the category or count does not apply to the visible example. This field does not change the action label.

## Data and evaluation limits

Label only BFCL training candidates that pass the source-ID and text-overlap audit. Do not use When2Call validation or test labels to create, revise, or select labels. Keep any benchmark comparison separate and report aggregate metrics only after the prompt and labels are fixed.
