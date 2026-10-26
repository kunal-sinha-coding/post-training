"""Measure GPT-6 Luna action-label alignment without exposing answer labels to the model.

The flow loads the action definitions, sends only each request and visible tools, requests one action
code, compares predictions locally, and saves aggregate-only metrics.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from collections import Counter
from pathlib import Path

from openai import OpenAI

LABELS = ("cannot_answer", "request_for_info", "tool_call", "direct")
LABEL_BY_CODE = {"A": "direct", "B": "tool_call", "C": "request_for_info", "D": "cannot_answer"}
CODE_BY_LABEL = {value: key for key, value in LABEL_BY_CODE.items()}
OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {"label": {"type": "string", "enum": ["A", "B", "C", "D"]}},
    "required": ["label"],
    "additionalProperties": False,
}


def category_for_source_id(source_id: str) -> str:
    """Map a When2Call source ID to its BFCL Live category name."""
    # Keep compound category names intact for aggregate reporting.
    parts = source_id.split("_")
    raw = parts[1] if len(parts) > 1 else "unknown"
    if raw.lower() == "parallel" and len(parts) > 2 and parts[2].lower() == "multiple":
        raw = "parallel_multiple"
    return {"simple": "Simple", "multiple": "Multiple", "parallel": "Parallel", "parallel_multiple": "Parallel Multiple", "relevance": "Relevance", "irrelevance": "Irrelevance"}.get(raw, raw.title())


def alignment_prompt(prompt: str) -> str:
    """Build an alignment prompt without BFCL categories or unused output fields."""
    # Keep the shared action definitions and omit category and reference-call instructions.
    prefix = prompt.split("## BFCL categories", 1)[0].rstrip()
    prefix = prefix.replace(
        "Use the conversation, system instructions, visible function descriptions and schemas, BFCL category, and a reference call when provided. Apply a category only when it describes this exact question and visible function list.",
        "Use the conversation, system instructions, and visible function descriptions and schemas. Base the action on the request and functions shown.",
    )
    # Apply one category-free decision procedure and require only the action code.
    return prefix + """

## Decision procedure for alignment

1. Identify the requested operation and its constraints.
2. Check whether a visible function performs that operation and whether the needed values are available.
3. Choose `A` when the request can be satisfied in ordinary text without a function.
4. Choose `B` when a suitable function can perform the operation with available or safely inferred values. Use a default only when it preserves the requested target, scope, and result.
5. Choose `C` when a suitable function exists but a required task-defining value is missing and the user can provide it.
6. Choose `D` when no suitable function exists and the request needs unavailable information or capability.

Return only this JSON object with one label code:

```json
{\"label\": \"A | B | C | D\"}
```
"""


def build_request(row: dict, index: int, prompt: str) -> dict:
    """Create one structured-output model request without test answer fields."""
    # Keep the inferred source category out because the visible tools may be transformed.
    tools = "\n".join(tool if isinstance(tool, str) else json.dumps(tool, ensure_ascii=False, sort_keys=True) for tool in row["tools"])
    user_input = f"Conversation:\nuser: {row['question']}\n\nAvailable functions:\n{tools}\n\nLabel the required assistant action."
    return {
        "custom_id": f"row-{index:05d}",
        "method": "POST",
        "url": "/v1/responses",
        "body": {
            "model": "gpt-6-luna",
            "reasoning": {"effort": "none"},
            "input": [{"role": "system", "content": prompt}, {"role": "user", "content": user_input}],
            "text": {"format": {"type": "json_schema", "name": "bfcl_action_label", "strict": True, "schema": OUTPUT_SCHEMA}},
            "max_output_tokens": 250,
        },
    }


def response_text(body: dict) -> str:
    """Extract structured JSON text from one Responses API result."""
    # Return the first complete schema-shaped JSON text block and ignore other message blocks.
    parts = []
    for item in body.get("output", []):
        if item.get("type") == "message":
            parts.extend(content.get("text", "") for content in item.get("content", []) if content.get("type") == "output_text")
    if not parts and isinstance(body.get("output_text"), str):
        parts.append(body["output_text"])
    for part in parts:
        try:
            parsed = json.loads(part)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict) and "label" in parsed:
            return part
    raise ValueError("No complete label object was present in the response text.")


def aggregate(expected: list[str], predicted: list[str], categories: list[str]) -> dict:
    """Calculate aggregate alignment and four-class macro F1 without retaining row predictions."""
    # Reduce predictions immediately to a four-class confusion matrix and category-level totals.
    matrix = [[0 for _ in LABELS] for _ in LABELS]
    by_category = {category: {"correct": 0, "examples": 0} for category in sorted(set(categories))}
    for truth, prediction, category in zip(expected, predicted, categories, strict=True):
        truth_id, prediction_id = LABELS.index(truth), LABELS.index(prediction)
        matrix[truth_id][prediction_id] += 1
        by_category[category]["correct"] += int(truth == prediction)
        by_category[category]["examples"] += 1
    f1_values = []
    per_label = {}
    for label_id, label in enumerate(LABELS):
        tp = matrix[label_id][label_id]
        fp = sum(matrix[row][label_id] for row in range(len(LABELS)) if row != label_id)
        fn = sum(matrix[label_id][column] for column in range(len(LABELS)) if column != label_id)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        per_label[label] = {"support": sum(matrix[label_id]), "precision": precision, "recall": recall, "f1": f1}
        f1_values.append(f1)
    # Report the exact-match rate and macro F1 over all four When2Call labels.
    for category, values in by_category.items():
        values["accuracy"] = values["correct"] / values["examples"] if values["examples"] else 0.0
    return {
        "examples": len(expected),
        "alignment_accuracy": sum(truth == prediction for truth, prediction in zip(expected, predicted, strict=True)) / max(1, len(expected)),
        "macro_f1_four_labels": sum(f1_values) / len(f1_values),
        "per_label": per_label,
        "by_bfcl_category": by_category,
        "confusion_matrix_label_order": list(LABELS),
        "confusion_matrix": matrix,
    }


def main() -> int:
    """Submit the fixed-prompt labeling batch and save only aggregate test measurements."""
    # Parse the public test artifact, reviewed prompt, batch controls, and output location.
    parser = argparse.ArgumentParser()
    parser.add_argument("--test-data", type=Path, required=True)
    parser.add_argument("--prompt", type=Path, default=Path("prompts/bfcl_to_when2call_labels.md"))
    parser.add_argument("--output", type=Path, default=Path("outputs/bfcl-prompt-test-alignment-20261026/metrics.json"))
    parser.add_argument("--poll-seconds", type=int, default=30)
    parser.add_argument("--batch-id")
    parser.add_argument("--allow-partial", action="store_true")
    args = parser.parse_args()
    source_prompt = args.prompt.read_text(encoding="utf-8")
    prompt = alignment_prompt(source_prompt)
    prompt_sha = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    # Keep reference labels local and exclude every answer-derived field from API request bodies.
    rows = [json.loads(line) for line in args.test_data.read_text(encoding="utf-8").splitlines() if line.strip()]
    expected = [row["correct_answer"] for row in rows]
    categories = [category_for_source_id(row["source_id"]) for row in rows]
    requests = [build_request(row, index, prompt) for index, row in enumerate(rows)]
    # Write the unlabeled inputs to a temporary request file for the official Batch API.
    input_path = Path("/tmp/when2call-prompt-alignment-batch.jsonl")
    input_path.write_text("".join(json.dumps(request, ensure_ascii=False) + "\n" for request in requests), encoding="utf-8")
    client = OpenAI()
    if args.batch_id:
        batch = client.batches.retrieve(args.batch_id)
    else:
        # Upload requests and create one batch for the fixed 3,652-example evaluation.
        input_file = client.files.create(file=input_path.open("rb"), purpose="batch")
        batch = client.batches.create(input_file_id=input_file.id, endpoint="/v1/responses", completion_window="24h", metadata={"task": "when2call_prompt_alignment", "model": "gpt-6-luna", "prompt_sha256": prompt_sha})
        print(json.dumps({"batch_id": batch.id, "status": batch.status, "request_count": len(requests), "input_file_id": input_file.id}), flush=True)
    # Poll until the batch has completed or the provider reports a terminal failure.
    while batch.status not in {"completed", "failed", "expired", "cancelled"}:
        time.sleep(args.poll_seconds)
        batch = client.batches.retrieve(batch.id)
        counts = batch.request_counts.model_dump() if batch.request_counts else None
        print(json.dumps({"batch_id": batch.id, "status": batch.status, "request_counts": counts}), flush=True)
    partial_allowed = args.allow_partial and batch.status == "cancelled"
    if (batch.status != "completed" and not partial_allowed) or not batch.output_file_id:
        raise RuntimeError(f"GPT-6 Luna batch ended with status={batch.status}, errors={batch.errors}")
    # Parse successful outputs in memory and reject incomplete runs instead of scoring a partial set.
    content = client.files.content(batch.output_file_id).read().decode("utf-8")
    outputs = [json.loads(line) for line in content.splitlines() if line.strip()]
    if len(outputs) != len(rows) and not partial_allowed:
        raise RuntimeError(f"Expected {len(rows)} successful predictions, received {len(outputs)}. Error file: {batch.error_file_id}")
    by_index = {}
    usage = Counter()
    for item in outputs:
        index = int(item["custom_id"].removeprefix("row-"))
        body = item["response"]["body"]
        parsed = json.loads(response_text(body))
        label = LABEL_BY_CODE.get(parsed.get("label"))
        if label is None:
            raise ValueError(f"Structured output label mismatch for custom_id={item['custom_id']}.")
        by_index[index] = label
        if body.get("usage"):
            usage["input_tokens"] += body["usage"].get("input_tokens", 0)
            usage["output_tokens"] += body["usage"].get("output_tokens", 0)
    if len(by_index) != len(outputs) or not by_index:
        raise RuntimeError(f"Received {len(by_index)} unique labels from {len(outputs)} successful responses.")
    completed_indices = sorted(by_index)
    predicted = [by_index[index] for index in completed_indices]
    scored_expected = [expected[index] for index in completed_indices]
    scored_categories = [categories[index] for index in completed_indices]
    metrics = aggregate(scored_expected, predicted, scored_categories)
    # Save dataset and prompt fingerprints plus aggregate scores, but no per-example test labels or predictions.
    result = {
        "experiment": "gpt6_luna_bfcl_label_prompt_alignment_when2call_test",
        "purpose": "Measure the reviewed BFCL action-label prompt's agreement with When2Call MCQ test labels.",
        "model": "gpt-6-luna",
        "endpoint": "/v1/responses via OpenAI Batch API",
        "batch_id": batch.id,
        "batch_status": batch.status,
        "partial_result": partial_allowed,
        "completed_examples": len(completed_indices),
        "not_scored_examples": len(rows) - len(completed_indices),
        "prompt_path": str(args.prompt),
        "prompt_sha256": prompt_sha,
        "source_prompt_sha256": hashlib.sha256(source_prompt.encode("utf-8")).hexdigest(),
        "test_dataset": "nvidia/When2Call test/mcq",
        "test_data_sha256": hashlib.sha256(args.test_data.read_bytes()).hexdigest(),
        "test_labels_sent_to_model": False,
        "test_labels_used_for": "aggregate prompt-alignment measurement only",
        "selection_or_prompt_tuning_on_test": False,
        "usage": dict(usage),
        "metrics": metrics,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    # Return a nonzero exit status for API failures or incomplete measurements.
    raise SystemExit(main())
