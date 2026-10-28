"""Generate and check small in-distribution synthetic When2Call training pilots.

The flow loads only train_pref, samples source examples as schema and style anchors, and
creates four distinct synthetic-data strategies through concurrent Responses API requests.
Each proposed row passes structural checks and a separate action-label judge before it is
saved as a trainer-ready prompt, with usage and cost written to an audit manifest.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import random
import re
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from experiments.train_qwen_when2call import LABELS, LABEL_TO_ID, load_rows, make_prompt, prepare_rows

MODEL = "gpt-6-luna"
INPUT_PRICE_PER_MILLION = 0.10
OUTPUT_PRICE_PER_MILLION = 0.50
RESERVED_COST_PER_CALL = 0.0015
STRATEGIES = {
    "new_tool_call": {"label": "tool_call", "source_label": "tool_call"},
    "missing_required_info": {"label": "request_for_info", "source_label": "request_for_info"},
    "unsupported_capability": {"label": "cannot_answer", "source_label": "cannot_answer"},
    "composed_tool_call": {"label": "tool_call", "source_label": "tool_call"},
}
LABEL_DEFINITIONS = """Action labels:
- cannot_answer: The request needs a capability that none of the tools provide, and it cannot be answered directly from the request.
- request_for_info: A tool can do the task, but a required input is missing and cannot be inferred.
- tool_call: A listed tool is needed and the request gives enough information to use it.
- direct: The request can be answered without a tool.
"""
OUTPUT_FORMAT = {
    "type": "json_schema",
    "name": "synthetic_when2call_example",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "request": {"type": "string"},
            "action_label": {"type": "string", "enum": list(LABELS)},
            "selected_tool_name": {"type": "string"},
            "arguments_json": {"type": "string"},
            "missing_required_argument": {"type": "string"},
            "new_scenario_note": {"type": "string"},
        },
        "required": ["request", "action_label", "selected_tool_name", "arguments_json", "missing_required_argument", "new_scenario_note"],
        "additionalProperties": False,
    },
}
JUDGE_FORMAT = {
    "type": "json_schema",
    "name": "synthetic_when2call_label_judgment",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "action_label": {"type": "string", "enum": list(LABELS)},
            "reason": {"type": "string"},
        },
        "required": ["action_label", "reason"],
        "additionalProperties": False,
    },
}


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    """Write one JSON artifact by replacing it atomically."""
    # Keep resumable manifests valid if the process stops during a write.
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def normalized(text: str) -> str:
    """Normalize a request for exact duplicate detection."""
    # Fold case and whitespace without altering the saved request.
    return " ".join(text.casefold().split())


def user_request(row: Any) -> str:
    """Return the source row's user messages in their original order."""
    # Keep examples with multiple user turns intact when using them as a generation anchor.
    return "\n".join(message["content"] for message in row["messages"] if message["role"] == "user")


def tool_schema(raw: str) -> dict[str, Any] | None:
    """Parse one source tool schema and return its function-level object."""
    # Accept both When2Call's direct function shape and wrapped function schemas.
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None
    function = parsed.get("function", parsed) if isinstance(parsed, dict) else None
    return function if isinstance(function, dict) else None


def tool_name(raw: str) -> str:
    """Return a tool's declared name or an empty string when invalid."""
    # Reuse the validated schema parser so malformed tools cannot pass checks.
    parsed = tool_schema(raw)
    return str(parsed.get("name", "")) if parsed else ""


def required_fields(raw: str) -> tuple[dict[str, Any], list[str]]:
    """Return one tool's properties and required field names."""
    # Read required fields from the parameter schema used by the training data.
    parsed = tool_schema(raw) or {}
    parameters = parsed.get("parameters", {})
    properties = parameters.get("properties", {}) if isinstance(parameters, dict) else {}
    required = parameters.get("required", parsed.get("required", [])) if isinstance(parameters, dict) else []
    return (properties if isinstance(properties, dict) else {}, [str(key) for key in required if isinstance(key, str)])


def choose_jobs(rows: Any, prepared: list[Any], count: int, seed: int) -> list[dict[str, Any]]:
    """Build a fixed stratified set of source-anchored generation tasks."""
    # Use only the observed non-direct train_pref classes and require one user message per anchor.
    eligible: dict[str, list[int]] = {label: [] for label in LABELS if label != "direct"}
    for index, row in enumerate(rows):
        user_messages = [message for message in row["messages"] if message["role"] == "user"]
        label_name = LABELS[prepared[index].label]
        if len(user_messages) == 1 and row.get("tools") and label_name in eligible:
            # Require a real required field for clarification pilots and compact sets for composition.
            has_missing_field = any(any("default" not in properties.get(field, {}) for field in required) for raw in row["tools"] for properties, required in [required_fields(raw)])
            if label_name == "request_for_info" and not has_missing_field:
                continue
            if label_name == "tool_call" and len(row["tools"]) > 4:
                continue
            eligible[label_name].append(index)
    # Draw a distinct anchor for each job and rotate strategies to keep the pilot breadth balanced.
    rng = random.Random(seed)
    jobs = []
    per_strategy = {name: count for name in STRATEGIES}
    for strategy, wanted in per_strategy.items():
        source_label = STRATEGIES[strategy]["source_label"]
        candidates = eligible[source_label]
        if not candidates:
            raise RuntimeError(f"No train_pref anchors for source class {source_label}.")
        for slot in range(wanted):
            first = rng.choice(candidates)
            indices = [first]
            tools = list(rows[first]["tools"])
            if strategy == "composed_tool_call":
                # Combine tools from two independent tool-call rows while limiting prompt size.
                second_candidates = [i for i in eligible["tool_call"] if i != first and len(rows[i]["tools"]) <= 4]
                second = rng.choice(second_candidates)
                merged = tools + [raw for raw in rows[second]["tools"] if tool_name(raw) not in {tool_name(item) for item in tools}]
                tools = merged[:8]
                indices.append(second)
            # Store raw source context so generation can create a new request without altering schemas.
            jobs.append({"strategy": strategy, "slot": slot, "source_indices": indices, "source_requests": [user_request(rows[i]) for i in indices], "tools": tools})
    return jobs


def generation_instruction(job: dict[str, Any]) -> str:
    """Build a class-specific prompt for a new synthetic request."""
    # Tell the model to create a new scenario and keep the source tools unchanged.
    strategy = job["strategy"]
    common = "Create a genuinely new user request, not a paraphrase or small edit of the source request. Stay close to the source task style and complexity. Keep every available tool schema exactly as provided. Return one request only, with no answer."
    if strategy == "new_tool_call":
        target = "The target action is tool_call. Choose one listed tool. The request must clearly require it and include all facts needed for the required arguments. Return a JSON object in arguments_json with every required field."
    elif strategy == "missing_required_info":
        target = "The target action is request_for_info. Choose one listed tool with a required field that has no default. The request must need that tool, provide the other required facts, and omit one required value that cannot be inferred. Name the omitted field."
    elif strategy == "unsupported_capability":
        target = "The target action is cannot_answer. Ask for an action that none of the listed tools can perform and that cannot be answered from stable knowledge in the request. Do not ask for a tool-supported task. Leave selected_tool_name and missing_required_argument empty, and use {} for arguments_json."
    else:
        target = "The target action is tool_call. The available tools combine two source tool sets. Choose one tool and create a new request that needs that tool, distinguishes it from the other tools, and supplies all facts required for its arguments."
    context = {"source_requests": job["source_requests"], "available_tools": job["tools"], "target_action": STRATEGIES[strategy]["label"]}
    return f"{LABEL_DEFINITIONS}\n{common}\n{target}\n\nSource context:\n{json.dumps(context, ensure_ascii=False)}"


def valid_structure(job: dict[str, Any], item: dict[str, Any]) -> tuple[bool, str]:
    """Check the generated example's target label and tool arguments."""
    # Reject label drift, malformed arguments, unsupported tool names, and invalid missing fields.
    strategy = job["strategy"]
    expected = STRATEGIES[strategy]["label"]
    request = item.get("request", "").strip()
    if item.get("action_label") != expected or len(request) < 12 or len(request) > 1200:
        return False, "label_or_request_check"
    names = {tool_name(raw): raw for raw in job["tools"] if tool_name(raw)}
    try:
        arguments = json.loads(item.get("arguments_json", "{}"))
    except json.JSONDecodeError:
        return False, "arguments_json_parse"
    if not isinstance(arguments, dict):
        return False, "arguments_not_object"
    selected = item.get("selected_tool_name", "")
    if strategy in {"new_tool_call", "composed_tool_call"}:
        if selected not in names:
            return False, "tool_not_in_available_set"
        properties, required = required_fields(names[selected])
        if not set(arguments).issubset(set(properties)) or not set(required).issubset(set(arguments)):
            return False, "required_arguments_check"
    elif strategy == "missing_required_info":
        if selected not in names:
            return False, "tool_not_in_available_set"
        properties, required = required_fields(names[selected])
        missing = item.get("missing_required_argument", "")
        if missing not in required or missing in arguments or not set(arguments).issubset(set(properties)):
            return False, "missing_argument_check"
        if any(field not in arguments for field in required if field != missing):
            return False, "other_required_arguments_check"
        missing_schema = properties.get(missing, {})
        if isinstance(missing_schema, dict) and "default" in missing_schema:
            return False, "missing_field_has_default"
    elif selected or item.get("missing_required_argument"):
        return False, "unsupported_metadata_check"
    return True, "accepted_structure"


async def response_json(client: Any, semaphore: asyncio.Semaphore, prompt: str, output_format: dict[str, Any], ledger: dict[str, Any], output_path: Path, cost_lock: asyncio.Lock, cap: float) -> tuple[dict[str, Any] | None, str]:
    """Call the Responses API under a concurrency and cost limit."""
    # Use a semaphore and a small token-cost reservation to keep the API pilot fast and bounded.
    async with semaphore:
        async with cost_lock:
            reserved = float(ledger.get("reserved_cost_usd", 0.0))
            spent = float(ledger.get("estimated_cost_usd", 0.0))
            if spent + reserved + RESERVED_COST_PER_CALL > cap:
                return None, "cost_cap"
            ledger["reserved_cost_usd"] = reserved + RESERVED_COST_PER_CALL
            atomic_json(output_path, ledger)
        try:
            response = await client.responses.create(
                model=MODEL,
                reasoning={"effort": "none"},
                max_output_tokens=350,
                input=[{"role": "user", "content": prompt}],
                text={"format": output_format},
            )
            parsed = json.loads(response.output_text)
            usage = response.usage
            async with cost_lock:
                ledger["reserved_cost_usd"] = max(0.0, float(ledger.get("reserved_cost_usd", 0.0)) - RESERVED_COST_PER_CALL)
                ledger["input_tokens"] += int(usage.input_tokens or 0)
                ledger["output_tokens"] += int(usage.output_tokens or 0)
                ledger["requests"] += 1
                ledger["estimated_cost_usd"] = ledger["input_tokens"] * INPUT_PRICE_PER_MILLION / 1_000_000 + ledger["output_tokens"] * OUTPUT_PRICE_PER_MILLION / 1_000_000
                atomic_json(output_path, ledger)
            return parsed, "ok"
        except Exception as error:
            # Record only the exception class so prompts and credentials stay out of logs.
            async with cost_lock:
                ledger["reserved_cost_usd"] = max(0.0, float(ledger.get("reserved_cost_usd", 0.0)) - RESERVED_COST_PER_CALL)
                ledger["errors"] += 1
                ledger["last_error_type"] = type(error).__name__
                atomic_json(output_path, ledger)
            return None, type(error).__name__


def judge_prompt(job: dict[str, Any], request: str) -> str:
    """Build an independent label-check prompt for a generated request."""
    # Give the judge the same tools and action definitions but hide the generation target.
    context = {"request": request, "available_tools": job["tools"]}
    return f"{LABEL_DEFINITIONS}\nClassify the required assistant action for this new example. Decide from the request and tools only.\n{json.dumps(context, ensure_ascii=False)}"


async def generate_one(job: dict[str, Any], client: Any, semaphore: asyncio.Semaphore, ledger: dict[str, Any], ledger_path: Path, cost_lock: asyncio.Lock, cap: float, seen: set[str], seen_lock: asyncio.Lock) -> dict[str, Any] | None:
    """Generate, validate, and label-check one synthetic example."""
    # Retry a small fixed number of times when a candidate fails structural or label checks.
    for attempt in range(3):
        parsed, status = await response_json(client, semaphore, generation_instruction(job), OUTPUT_FORMAT, ledger, ledger_path, cost_lock, cap)
        if parsed is None:
            return None
        valid, reason = valid_structure(job, parsed)
        if not valid:
            ledger["rejected_structure"] += 1
            ledger["rejection_reasons"][reason] = ledger["rejection_reasons"].get(reason, 0) + 1
            continue
        judged, judge_status = await response_json(client, semaphore, judge_prompt(job, parsed["request"]), JUDGE_FORMAT, ledger, ledger_path, cost_lock, cap)
        if judged is None or judged.get("action_label") != STRATEGIES[job["strategy"]]["label"]:
            ledger["rejected_judgment"] += 1
            continue
        key = normalized(parsed["request"])
        async with seen_lock:
            if key in seen:
                ledger["rejected_duplicate"] += 1
                continue
            seen.add(key)
        # Build a trainer-ready prompt using only the source schema and the new request.
        synthetic_row = {"messages": [{"role": "user", "content": parsed["request"]}], "tools": job["tools"]}
        return {"prompt": make_prompt(synthetic_row), "label": LABEL_TO_ID[STRATEGIES[job["strategy"]]["label"]], "label_name": STRATEGIES[job["strategy"]]["label"], "augmentation_type": job["strategy"], "source_indices": job["source_indices"], "request": parsed["request"], "selected_tool_name": parsed.get("selected_tool_name", ""), "arguments_json": parsed.get("arguments_json", "{}"), "missing_required_argument": parsed.get("missing_required_argument", ""), "judge_label": judged["action_label"], "judge_reason": judged.get("reason", ""), "new_scenario_note": parsed.get("new_scenario_note", ""), "attempts": attempt + 1}
    return None


async def run(args: argparse.Namespace) -> dict[str, Any]:
    """Generate all four bounded pilots and save accepted training rows."""
    # Load source examples only from train_pref and build source-stratified pilot jobs.
    source_rows = load_rows()
    prepared = prepare_rows(source_rows)
    jobs = choose_jobs(source_rows, prepared, args.examples_per_strategy, args.seed)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    train_questions = {normalized(user_request(row)) for row in source_rows}
    seen = set(train_questions)
    # Initialize a shared cost ledger before the first API request.
    ledger_path = args.output_dir / "cost-ledger.json"
    # Create all four output files before training commands are allowed to start.
    for strategy in STRATEGIES:
        (args.output_dir / f"{strategy}.jsonl").touch()
    ledger = {"model": MODEL, "input_price_per_million": INPUT_PRICE_PER_MILLION, "output_price_per_million": OUTPUT_PRICE_PER_MILLION, "requests": 0, "input_tokens": 0, "output_tokens": 0, "estimated_cost_usd": 0.0, "reserved_cost_usd": 0.0, "errors": 0, "rejected_structure": 0, "rejected_judgment": 0, "rejected_duplicate": 0, "rejection_reasons": {}, "max_cost_usd": args.max_cost_usd, "concurrency": args.workers}
    atomic_json(ledger_path, ledger)
    from openai import AsyncOpenAI
    client = AsyncOpenAI(timeout=90.0, max_retries=1)
    semaphore = asyncio.Semaphore(args.workers)
    cost_lock = asyncio.Lock()
    seen_lock = asyncio.Lock()
    tasks = [asyncio.create_task(generate_one(job, client, semaphore, ledger, ledger_path, cost_lock, args.max_cost_usd, seen, seen_lock)) for job in jobs]
    accepted: dict[str, list[dict[str, Any]]] = {name: [] for name in STRATEGIES}
    audit_path = args.output_dir / "generation-audit.jsonl"
    # Save accepted rows as each concurrent task finishes so partial work remains useful.
    with audit_path.open("a", encoding="utf-8") as audit_handle:
        for completed, task in enumerate(asyncio.as_completed(tasks), start=1):
            result = await task
            if result is not None:
                accepted[result["augmentation_type"]].append(result)
                audit_handle.write(json.dumps({"accepted": True, **result}, ensure_ascii=False) + "\n")
                audit_handle.flush()
                data_path = args.output_dir / f"{result['augmentation_type']}.jsonl"
                with data_path.open("a", encoding="utf-8") as data_handle:
                    data_handle.write(json.dumps({"prompt": result["prompt"], "label": result["label"], "augmentation_type": result["augmentation_type"], "source_indices": result["source_indices"]}, ensure_ascii=False) + "\n")
                    data_handle.flush()
            else:
                audit_handle.write(json.dumps({"accepted": False, "slot": completed}) + "\n")
                audit_handle.flush()
            if completed % 10 == 0 or completed == len(tasks):
                counts = {name: len(items) for name, items in accepted.items()}
                print(json.dumps({"completed": completed, "total": len(tasks), "accepted": counts, "cost_usd": ledger["estimated_cost_usd"]}), flush=True)
    await client.close()
    # Record row counts, class counts, spend, and the no-test-data boundary.
    summary = {"status": "completed", "source": "nvidia/When2Call:train_pref", "source_examples": len(source_rows), "examples_requested_per_strategy": args.examples_per_strategy, "accepted_per_strategy": {name: len(items) for name, items in accepted.items()}, "strategies": STRATEGIES, "model": MODEL, "concurrency": args.workers, "seed": args.seed, "cost_ledger": str(ledger_path), "estimated_cost_usd": ledger["estimated_cost_usd"], "official_test_loaded": False, "test_labels_used": False}
    atomic_json(args.output_dir / "metrics.json", summary)
    return summary


def main() -> int:
    """Validate budget and start the bounded synthetic-data pilot."""
    # Parse output and concurrency settings before loading any source data.
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--examples-per-strategy", type=int, default=50)
    parser.add_argument("--workers", type=int, default=24)
    parser.add_argument("--seed", type=int, default=20261069)
    parser.add_argument("--max-cost-usd", type=float, default=1.0)
    args = parser.parse_args()
    load_dotenv()
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is required for the synthetic generation pilot.")
    if args.examples_per_strategy < 1 or args.workers < 1 or args.max_cost_usd <= 0:
        raise ValueError("Pilot size, concurrency, and cost cap must be positive.")
    summary = asyncio.run(run(args))
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
