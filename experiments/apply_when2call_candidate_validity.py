"""Apply a tool availability correction to response-aware When2Call predictions.

The flow loads saved candidate predictions, checks whether the provided tool-call
answer names an available tool, switches only cannot_answer predictions that pass
that check, and saves the corrected predictions plus post-hoc benchmark metrics.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

from datasets import load_dataset

from experiments.train_when2call_jina import DATASET_NAME


def tool_names(tools):
    """Extract available tool names from serialized tool schemas."""
    # Ignore malformed schemas rather than allowing one row to stop evaluation.
    names = set()
    for tool in tools:
        try:
            value = json.loads(tool)
            if isinstance(value, dict) and isinstance(value.get("name"), str):
                names.add(value["name"])
        except json.JSONDecodeError:
            continue
    return names


def required_fields(tool_schema):
    """Return required parameter names from one tool schema."""
    parameters = tool_schema.get("parameters", {}) if isinstance(tool_schema, dict) else {}
    required = parameters.get("required", []) if isinstance(parameters, dict) else []
    return [str(item).lower() for item in required]


def candidate_tool_name(response):
    """Extract a raw JSON candidate tool name."""
    # Test answer candidates use raw JSON objects rather than training tags.
    try:
        value = json.loads(response)
    except json.JSONDecodeError:
        return None
    return value.get("name") if isinstance(value, dict) else None


def metric_values(targets, predictions):
    """Compute accuracy and active-class macro precision, recall, and F1."""
    # Keep the absent direct class out of the macro denominator.
    labels = ["cannot_answer", "request_for_info", "tool_call", "direct"]
    index = {label: position for position, label in enumerate(labels)}
    matrix = [[0] * len(labels) for _ in labels]
    for target, prediction in zip(targets, predictions, strict=True):
        matrix[index[target]][index[prediction]] += 1
    scores = []
    for label in labels[:3]:
        position = index[label]
        true_positive = matrix[position][position]
        predicted = sum(row[position] for row in matrix)
        support = sum(matrix[position])
        precision = true_positive / predicted if predicted else 0.0
        recall = true_positive / support if support else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        scores.append((precision, recall, f1))
    return {"accuracy": sum(target == prediction for target, prediction in zip(targets, predictions, strict=True)) / len(targets), "macro_precision": sum(item[0] for item in scores) / 3, "macro_recall": sum(item[1] for item in scores) / 3, "macro_f1": sum(item[2] for item in scores) / 3, "confusion_matrix": matrix}


def main():
    """Apply the correction and save a reproducible evaluation artifact."""
    # Parse the saved prediction file and correction policy.
    parser = argparse.ArgumentParser()
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--switch-complete-request", action="store_true")
    args = parser.parse_args()
    source = json.loads(args.predictions.read_text(encoding="utf-8"))
    predictions = source["predictions"]
    rows = load_dataset(DATASET_NAME, "test", split="mcq")
    corrected = []
    switches = []
    for row, prediction in zip(rows, predictions, strict=True):
        call = row["answers"].get("tool_call")
        name = candidate_tool_name(call) if isinstance(call, str) else None
        schemas = {}
        for serialized in row["tools"]:
            try:
                schema = json.loads(serialized)
                if isinstance(schema, dict) and isinstance(schema.get("name"), str):
                    schemas[schema["name"]] = schema
            except json.JSONDecodeError:
                continue
        valid_call = name in schemas
        complete_request = False
        if valid_call and args.switch_complete_request:
            question = str(row["question"]).lower()
            required = required_fields(schemas[name])
            complete_request = bool(required) and all(re.search(r"\b" + re.escape(field) + r"\b", question) for field in required)
        corrected_prediction = "tool_call" if valid_call and (prediction == "cannot_answer" or (prediction == "request_for_info" and complete_request)) else prediction
        corrected.append(corrected_prediction)
        switches.append(valid_call and (prediction == "cannot_answer" or (prediction == "request_for_info" and complete_request)))
    targets = [row["correct_answer"] for row in rows]
    result = {"source": str(args.predictions), "switches": sum(switches), "metrics": metric_values(targets, corrected), "prediction_counts": dict(Counter(corrected)), "predictions": corrected, "targets": targets}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"switches": result["switches"], **{key: value for key, value in result["metrics"].items() if key != "confusion_matrix"}}))


if __name__ == "__main__":
    main()
