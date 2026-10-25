# Prompt: Map BFCL Live Examples to When2Call Action Labels

## Task

Map one BFCL Live interaction to the single assistant action label used by the When2Call four-way classifier. Use the full system message, user request, and available function descriptions. Do not create a function call unless the example evidence supports one.

## Labels

Return exactly one primary label:

- `direct` (`A`): The assistant can satisfy the request with a normal text response and does not need an available function.
- `tool_call` (`B`): An available function can satisfy the request, and the information needed for its required arguments is present or can be safely inferred from the conversation.
- `request_for_info` (`C`): An available function can satisfy the request, but a required argument is missing and cannot be safely inferred. Ask for the missing information.
- `cannot_answer` (`D`): The request cannot be satisfied by an available function, and the assistant cannot responsibly answer it directly from the conversation or general knowledge.

## Category-specific guidance

- `simple` and `multiple` examples normally map to `tool_call`. Change this to `request_for_info` only when the reference call or function schema shows that required information is missing from the conversation.
- `parallel` and `parallel_multiple` examples map to `tool_call` when the required call or calls are supported and sufficiently specified. Record the expected call count separately because the four-way action label does not encode parallel structure.
- `relevance` means at least one function is relevant and expected to be called in the BFCL task. Map it to `tool_call` when its arguments are sufficiently specified. If the request lacks a required argument, use `request_for_info`.
- `irrelevance` means no provided function should be called. Do not map every such example to `cannot_answer`. Use `direct` if the assistant can satisfy the request without a function. Use `cannot_answer` only if the request still cannot be responsibly satisfied without a function. If the distinction is unclear, mark the row `needs_review` rather than guessing.

## Evidence and limits

- Treat the BFCL category as a prior, not as a substitute for reading the request and function schemas.
- Use BFCL reference calls, when present, to verify the intended function names and whether argument values are available. Do not invent missing values.
- Do not infer that a tool is relevant only because its name looks similar. Check its documented purpose and required arguments.
- Do not use When2Call validation or test labels to construct or select these labels.
- Preserve the original wording and function schemas. Do not rewrite a request to make a label easier.
- For parallel examples, set `expected_call_count` to the number of reference calls when available. Do not flatten multiple calls into one fabricated call.

## Output

Return one JSON object per example with these fields:

```json
{
  "source_id": "BFCL example id",
  "category": "BFCL category",
  "label": "direct | tool_call | request_for_info | cannot_answer | needs_review",
  "confidence": "high | medium | low",
  "rationale": "Short evidence-based explanation.",
  "expected_call_count": 0,
  "review_reason": null
}
```

`needs_review` is a construction status, not a fifth training class. Do not include rows with this status in training until a reviewer resolves them.
