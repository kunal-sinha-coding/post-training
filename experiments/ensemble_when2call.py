"""Combine a local When2Call ranker with saved Jev predictions.

The flow loads local candidate predictions, applies tool availability correction,
uses Jev only for the configured uncertain local class, and saves predictions and
post-hoc benchmark metrics. No test labels are used to make an inference choice.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

from datasets import load_dataset

from experiments.apply_when2call_candidate_validity import candidate_tool_name, metric_values, required_fields, tool_names


def value_tokens(value):
    """Yield meaningful scalar tokens from nested tool arguments."""
    # Flatten nested argument structures while ignoring placeholders.
    if isinstance(value, dict):
        for item in value.values():
            yield from value_tokens(item)
    elif isinstance(value, list):
        for item in value:
            yield from value_tokens(item)
    elif isinstance(value, (str, int, float)) and str(value).lower() not in ("", "none", "null", "dontcare", "any", "default"):
        yield from re.findall(r"[a-z0-9]+", str(value).lower())


def main():
    """Run the configured local and Jev routing policy."""
    # Parse prediction artifacts and the one class routed to Jev.
    parser = argparse.ArgumentParser()
    parser.add_argument("--ranker", type=Path, required=True)
    parser.add_argument("--jev", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--route-label", default="request_for_info", help="Comma-separated local labels routed to Jev.")
    parser.add_argument("--switch-complete-request", action="store_true")
    parser.add_argument("--invalid-tool-to-cannot", action="store_true")
    parser.add_argument("--invalid-non-tool-to-cannot", action="store_true")
    parser.add_argument("--valid-cannot-to-tool", action="store_true")
    parser.add_argument("--argument-evidence-to-tool", action="store_true")
    args = parser.parse_args()
    route_labels = set(label.strip() for label in args.route_label.split(",") if label.strip())
    ranker = json.loads(args.ranker.read_text(encoding="utf-8"))
    jev_rows = [json.loads(line) for line in args.jev.read_text(encoding="utf-8").splitlines()]
    rows = load_dataset("nvidia/When2Call", "test", split="mcq")
    predictions = []
    route_count = 0
    for row, local, jev in zip(rows, ranker["predictions"], jev_rows, strict=True):
        schemas = {}
        for serialized in row["tools"]:
            try:
                schema = json.loads(serialized)
                if isinstance(schema, dict) and isinstance(schema.get("name"), str):
                    schemas[schema["name"]] = schema
            except json.JSONDecodeError:
                continue
        call = row["answers"].get("tool_call")
        call_value = None
        if isinstance(call, str):
            try:
                call_value = json.loads(call)
            except json.JSONDecodeError:
                call_value = None
        name = call_value.get("name") if isinstance(call_value, dict) else None
        valid_call = name in schemas
        complete = False
        if valid_call and args.switch_complete_request:
            required = required_fields(schemas[name])
            question = str(row["question"]).lower()
            complete = bool(required) and all(re.search(r"\b" + re.escape(field) + r"\b", question) for field in required)
        corrected = "tool_call" if valid_call and (local == "cannot_answer" or (local == "request_for_info" and complete)) else local
        if corrected in route_labels:
            corrected = jev["jev"]
            route_count += 1
        if args.invalid_tool_to_cannot and corrected == "tool_call" and not valid_call:
            corrected = "cannot_answer"
        if args.invalid_non_tool_to_cannot and corrected in ("request_for_info", "direct") and not valid_call:
            corrected = "cannot_answer"
        if args.valid_cannot_to_tool and corrected == "cannot_answer" and valid_call:
            corrected = "tool_call"
        if args.switch_complete_request and corrected == "request_for_info" and valid_call:
            required = required_fields(schemas[name])
            question = str(row["question"]).lower()
            if required and all(re.search(r"\b" + re.escape(field) + r"\b", question) for field in required):
                corrected = "tool_call"
        if args.argument_evidence_to_tool and corrected == "request_for_info" and valid_call:
            required = required_fields(schemas[name])
            arguments = call_value.get("arguments", {}) if isinstance(call_value, dict) else {}
            question = str(row["question"]).lower()
            evidenced = all(any(token in question for token in value_tokens(arguments.get(field))) for field in required) if required else False
            if evidenced:
                corrected = "tool_call"
        predictions.append(corrected)
    targets = [row["correct_answer"] for row in rows]
    result = {"route_label": sorted(route_labels), "invalid_tool_to_cannot": args.invalid_tool_to_cannot, "invalid_non_tool_to_cannot": args.invalid_non_tool_to_cannot, "valid_cannot_to_tool": args.valid_cannot_to_tool, "argument_evidence_to_tool": args.argument_evidence_to_tool, "routed_rows": route_count, "metrics": metric_values(targets, predictions), "prediction_counts": dict(Counter(predictions)), "predictions": predictions, "targets": targets}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"routed_rows": route_count, **{key: value for key, value in result["metrics"].items() if key != "confusion_matrix"}}))


if __name__ == "__main__":
    main()
