"""Infer demonstrated input constraints and validate candidate calls against them.

The flow converts literal arguments to Python values, infers only relationships
that hold across every official example, and returns explicit violations for any
candidate that changes the demonstrated argument types, shapes, or domains.
"""

from __future__ import annotations

import ast
import math
import re
from typing import Any


CONTAINER_TYPES = (list, tuple, str, dict, set)


def _value(node: ast.expr) -> Any:
    """Return a standard literal value or raise when a constructor is present."""
    # Keep constructor expressions outside empirical value inference.
    return ast.literal_eval(node)


def _type_name(value: Any) -> str:
    """Return the exact stable name used by argument type constraints."""
    # Distinguish booleans from integers despite their Python subclass relation.
    return type(value).__name__


def infer_constraints(calls: list[ast.Call], prompt: str = "") -> list[dict[str, Any]]:
    """Infer conservative constraints that hold across every official call."""
    # Retain only argument positions that are standard literals in every call.
    if not calls:
        return [{"type": "none_output_allowed", "allowed": False}]
    width = min(len(call.args) for call in calls)
    columns: dict[int, list[Any]] = {}
    for index in range(width):
        try:
            columns[index] = [_value(call.args[index]) for call in calls]
        except (TypeError, ValueError):
            continue

    # Record exact demonstrated argument types before relational constraints.
    rules: list[dict[str, Any]] = []
    for index, values in columns.items():
        if len({_type_name(value) for value in values}) == 1:
            rules.append({"type": "arg_type", "arg": index, "type_name": _type_name(values[0])})

        # Preserve demonstrated scalar domains rather than extrapolating unsafe values.
        if all(type(value) in (int, float) for value in values):
            if all(value > 0 for value in values):
                rules.append({"type": "positive", "arg": index})
            elif all(value >= 0 for value in values):
                rules.append({"type": "nonnegative", "arg": index})
            if all(value != 0 for value in values):
                rules.append({"type": "nonzero", "arg": index})

        # Preserve nonempty inputs and demonstrated matrix shapes.
        if all(isinstance(value, CONTAINER_TYPES) and len(value) > 0 for value in values):
            rules.append({"type": "nonempty", "arg": index})
        if all(isinstance(value, (list, tuple)) and value and all(isinstance(row, (list, tuple)) for row in value) for value in values):
            if all(len({len(row) for row in value}) == 1 for value in values):
                rules.append({"type": "rectangular", "arg": index})
            if all(len(value) == len(value[0]) for value in values):
                rules.append({"type": "square", "arg": index})

        # Require prompt support before treating coincidentally ordered examples as sorted inputs.
        sorted_prompt = re.search(r"\bsort|sorted|ascending|increasing|nondecreasing|ordered", prompt.lower())
        if sorted_prompt and all(isinstance(value, (list, tuple)) and len(value) >= 2 for value in values):
            try:
                if all(list(value) == sorted(value) for value in values):
                    rules.append({"type": "sorted", "arg": index})
            except TypeError:
                pass

    # Infer size and parallel-container relationships across every example.
    for scalar, scalar_values in columns.items():
        for container, container_values in columns.items():
            if scalar == container:
                continue
            if all(type(size) is int and isinstance(value, CONTAINER_TYPES) and size == len(value) for size, value in zip(scalar_values, container_values)):
                rules.append({"type": "length_equals", "container": container, "scalar": scalar})
    indexes = re.search(r"index|position|kth|k-th|element at", prompt.lower())
    for first in columns:
        for second in range(first + 1, width):
            if second not in columns:
                continue
            left, right = columns[first], columns[second]
            if all(isinstance(a, (list, tuple, str)) and isinstance(b, (list, tuple, str)) and len(a) == len(b) for a, b in zip(left, right)):
                rules.append({"type": "equal_lengths", "args": [first, second]})
            if indexes:
                for index, container in ((first, second), (second, first)):
                    values, containers = columns[index], columns[container]
                    if all(type(value) is int and isinstance(items, (list, tuple, str)) for value, items in zip(values, containers)):
                        if all(0 <= value < len(items) for value, items in zip(values, containers)):
                            rules.append({"type": "zero_based_index", "container": container, "index": index})
                        elif all(1 <= value <= len(items) for value, items in zip(values, containers)):
                            rules.append({"type": "one_based_index", "container": container, "index": index})

    # Generated None is always rejected because it commonly reflects an invalid input path.
    rules.append({"type": "none_output_allowed", "allowed": False})
    return rules


def validate_call(constraints: list[dict[str, Any]], call: ast.Call) -> list[str]:
    """Return every inferred constraint violated by a candidate call."""
    # Decode standard literal arguments while retaining errors for constructor values.
    values: dict[int, Any] = {}
    for index, node in enumerate(call.args):
        try:
            values[index] = _value(node)
        except (TypeError, ValueError):
            continue

    # Evaluate every applicable rule so reports retain overlapping violations.
    violations: list[str] = []
    for rule in constraints:
        kind = rule["type"]
        arg = rule.get("arg")
        value = values.get(arg) if arg is not None else None
        if kind == "arg_type" and value is not None and _type_name(value) != rule["type_name"]:
            violations.append(f"arg_type:{arg}")
        elif kind == "positive" and value is not None and not value > 0:
            violations.append(f"positive:{arg}")
        elif kind == "nonnegative" and value is not None and not value >= 0:
            violations.append(f"nonnegative:{arg}")
        elif kind == "nonzero" and value is not None and value == 0:
            violations.append(f"nonzero:{arg}")
        elif kind == "nonempty" and value is not None and len(value) == 0:
            violations.append(f"nonempty:{arg}")
        elif kind == "sorted" and value is not None and list(value) != sorted(value):
            violations.append(f"sorted:{arg}")
        elif kind in {"rectangular", "square"} and value is not None:
            rectangular = bool(value) and all(isinstance(row, (list, tuple)) for row in value) and len({len(row) for row in value}) == 1
            if not rectangular or (kind == "square" and len(value) != len(value[0])):
                violations.append(f"{kind}:{arg}")
        elif kind == "length_equals" and rule["container"] in values and rule["scalar"] in values:
            if len(values[rule["container"]]) != values[rule["scalar"]]:
                violations.append(f"length_equals:{rule['container']}:{rule['scalar']}")
        elif kind == "equal_lengths" and all(index in values for index in rule["args"]):
            if len({len(values[index]) for index in rule["args"]}) != 1:
                violations.append("equal_lengths:" + ":".join(map(str, rule["args"])))
        elif kind in {"zero_based_index", "one_based_index"} and rule["container"] in values and rule["index"] in values:
            index_value, size = values[rule["index"]], len(values[rule["container"]])
            valid = 0 <= index_value < size if kind == "zero_based_index" else 1 <= index_value <= size
            if not valid:
                violations.append(f"{kind}:{rule['index']}:{rule['container']}")
    return violations
