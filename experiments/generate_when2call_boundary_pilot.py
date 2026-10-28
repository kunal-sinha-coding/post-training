"""Generate a small balanced synthetic pilot around action boundaries.

The flow samples only train_pref source rows, generates paired complete and missing-argument requests plus plausible unsupported requests, verifies structure and labels with a separate API call, and saves trainer-ready prompts with a cost ledger. It never loads validation or test data.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import random
from pathlib import Path
from typing import Any

from experiments.train_qwen_when2call import LABELS, LABEL_TO_ID, load_rows, make_prompt, prepare_rows

MODEL = "gpt-6-luna"
INPUT_PRICE_PER_MILLION = 0.10
OUTPUT_PRICE_PER_MILLION = 0.50
RESERVED_COST_PER_CALL = 0.0015
LABEL_DEFINITIONS = """Action labels:
- cannot_answer: The request needs a capability that none of the tools provide, and it cannot be answered directly from the request.
- request_for_info: A tool can do the task, but a required input is missing and cannot be inferred.
- tool_call: A listed tool is needed and the request gives enough information to use it.
- direct: The request can be answered without a tool.
"""
PAIR_FORMAT = {
    "type": "json_schema", "name": "when2call_boundary_pair", "strict": True,
    "schema": {"type": "object", "properties": {
        "tool_name": {"type": "string"},
        "missing_required_field": {"type": "string"},
        "complete_request": {"type": "string"},
        "complete_arguments_json": {"type": "string"},
        "incomplete_request": {"type": "string"},
        "incomplete_arguments_json": {"type": "string"},
        "scenario_note": {"type": "string"},
    }, "required": ["tool_name", "missing_required_field", "complete_request", "complete_arguments_json", "incomplete_request", "incomplete_arguments_json", "scenario_note"], "additionalProperties": False},
}
UNSUPPORTED_FORMAT = {
    "type": "json_schema", "name": "when2call_unsupported_request", "strict": True,
    "schema": {"type": "object", "properties": {"request": {"type": "string"}, "scenario_note": {"type": "string"}}, "required": ["request", "scenario_note"], "additionalProperties": False},
}
JUDGE_FORMAT = {
    "type": "json_schema", "name": "when2call_boundary_judgment", "strict": True,
    "schema": {"type": "object", "properties": {
        "complete_label": {"type": "string", "enum": list(LABELS)},
        "incomplete_label": {"type": "string", "enum": list(LABELS)},
        "unsupported_label": {"type": "string", "enum": list(LABELS)},
        "pair_preserves_intent": {"type": "boolean"},
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
        "reason": {"type": "string"},
    }, "required": ["complete_label", "incomplete_label", "unsupported_label", "pair_preserves_intent", "confidence", "reason"], "additionalProperties": False},
}


def normalize(text: str) -> str:
    """Normalize request text for exact duplicate checks."""
    # Fold case and whitespace without changing the saved request.
    return " ".join(text.casefold().split())


def source_request(row: Any) -> str:
    """Return the source row's user text in order."""
    # Keep multi-message user context intact when selecting generation anchors.
    return "\n".join(message["content"] for message in row["messages"] if message["role"] == "user")


def tool_object(raw: str) -> dict[str, Any] | None:
    """Parse one source tool schema into its function object."""
    # Accept the direct and wrapped function schema forms in train_pref.
    try:
        value = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None
    function = value.get("function", value) if isinstance(value, dict) else None
    return function if isinstance(function, dict) else None


def schema_fields(raw: str) -> tuple[str, dict[str, Any], list[str]]:
    """Return a tool name, parameter properties, and required fields."""
    # Read fields only from the source schema that will be kept unchanged.
    function = tool_object(raw) or {}
    parameters = function.get("parameters", {})
    properties = parameters.get("properties", {}) if isinstance(parameters, dict) else {}
    required = parameters.get("required", function.get("required", [])) if isinstance(parameters, dict) else []
    return str(function.get("name", "")), properties if isinstance(properties, dict) else {}, [str(x) for x in required if isinstance(x, str)]


def eligible_rows(rows: Any, prepared: list[Any], label: str) -> list[int]:
    """Find bounded source rows with schemas suited to the requested pilot class."""
    # Keep only single-turn rows with compact tool context and the requested source label.
    selected = []
    target = LABEL_TO_ID[label]
    for index, row in enumerate(rows):
        if prepared[index].label != target or not row.get("tools") or len(row["tools"]) > 5:
            continue
        if len([message for message in row["messages"] if message["role"] == "user"]) != 1:
            continue
        if sum(len(str(schema)) for schema in row["tools"]) > 10000:
            continue
        if label == "tool_call" and not any(required and any(not isinstance(props.get(field), dict) or "default" not in props[field] for field in required) for raw in row["tools"] for _, props, required in [schema_fields(raw)]):
            continue
        selected.append(index)
    return selected


def build_jobs(rows: Any, prepared: list[Any], pair_count: int, unsupported_count: int, seed: int, anchor_strategy: str) -> list[dict[str, Any]]:
    """Build a deterministic class-balanced set of train_pref generation jobs."""
    # Sample distinct source anchors for paired tool decisions and unsupported requests.
    rng = random.Random(seed)
    tool_rows = eligible_rows(rows, prepared, "tool_call")
    unsupported_rows = eligible_rows(rows, prepared, "cannot_answer")
    if len(tool_rows) < pair_count or len(unsupported_rows) < unsupported_count:
        raise RuntimeError("The train_pref split does not contain enough eligible source anchors.")
    rng.shuffle(tool_rows)
    rng.shuffle(unsupported_rows)
    schema_frequency = {}
    if anchor_strategy == "rare_schema":
        # Count tool-schema occurrences only in train_pref rows to identify long-tail schemas.
        for row in rows:
            for raw in set(row.get("tools", [])):
                signature = json.dumps(tool_object(raw) or raw, sort_keys=True, ensure_ascii=False)
                schema_frequency[signature] = schema_frequency.get(signature, 0) + 1
        # Prefer source examples with lower-frequency schemas while keeping randomized tie order.
        def rarity(index: int) -> float:
            signatures = [json.dumps(tool_object(raw) or raw, sort_keys=True, ensure_ascii=False) for raw in rows[index]["tools"]]
            return sum(schema_frequency.get(signature, 0) for signature in signatures) / max(1, len(signatures))
        tool_rows.sort(key=rarity)
        unsupported_rows.sort(key=rarity)
    jobs = []
    for slot, index in enumerate(tool_rows[:pair_count]):
        job = {"kind": "pair", "slot": slot, "source_indices": [index], "source_request": source_request(rows[index]), "tools": list(rows[index]["tools"])}
        if anchor_strategy == "rare_schema":
            # Require the generator to ground the pair in the rarest schema available in its source row.
            target_schema = min(job["tools"], key=lambda raw: schema_frequency.get(json.dumps(tool_object(raw) or raw, sort_keys=True, ensure_ascii=False), 0))
            job["target_tool_name"] = schema_fields(target_schema)[0]
        jobs.append(job)
    for slot, index in enumerate(unsupported_rows[:unsupported_count]):
        jobs.append({"kind": "unsupported", "slot": slot, "source_indices": [index], "source_request": source_request(rows[index]), "tools": list(rows[index]["tools"])})
    return jobs


def generation_prompt(job: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """Build the instruction and output schema for one generation job."""
    # Ask for a novel request that preserves source schemas and the intended decision boundary.
    context = {"source_request": job["source_request"], "available_tools": job["tools"]}
    if job.get("target_tool_name"):
        context["required_target_tool"] = job["target_tool_name"]
    if job["kind"] == "pair":
        instruction = "Create a new scenario in the same general domain, not a paraphrase of the source. If required_target_tool is provided, use that exact tool. Otherwise, select one listed tool. Select one required field with no default. Write two requests about the same task. The complete request must state all required information and have arguments for every required field. The incomplete request must differ only in one meaningful missing value for the selected required field. It must not imply that missing value, while it must give every other required value. Return valid JSON argument objects that match the selected schema."
        return f"{LABEL_DEFINITIONS}\n{instruction}\nSource context:\n{json.dumps(context, ensure_ascii=False)}", PAIR_FORMAT
    instruction = "Create one new, plausible request in the same broad domain as the source, not a paraphrase. Make it sound like it might use one of the listed tools, but require a capability that none of the listed schemas provide. It must not be answerable directly from stable knowledge. Do not alter the tools."
    return f"{LABEL_DEFINITIONS}\n{instruction}\nSource context:\n{json.dumps(context, ensure_ascii=False)}", UNSUPPORTED_FORMAT


def validate_pair(job: dict[str, Any], item: dict[str, Any]) -> tuple[bool, str]:
    """Check tool identity and required arguments for a generated boundary pair."""
    # Reject requests unless the complete and missing variants match the selected schema.
    name = str(item.get("tool_name", ""))
    schemas = {schema_fields(raw)[0]: raw for raw in job["tools"]}
    raw = schemas.get(name)
    if raw is None:
        return False, "unknown_tool"
    if job.get("target_tool_name") and name != job["target_tool_name"]:
        return False, "target_tool_mismatch"
    _, properties, required = schema_fields(raw)
    missing = str(item.get("missing_required_field", ""))
    if missing not in required or not properties:
        return False, "invalid_required_field"
    complete_text = str(item.get("complete_request", "")).strip()
    incomplete_text = str(item.get("incomplete_request", "")).strip()
    if len(complete_text) < 12 or len(incomplete_text) < 12 or normalize(complete_text) == normalize(incomplete_text):
        return False, "invalid_request_pair"
    try:
        complete = json.loads(item["complete_arguments_json"])
        incomplete = json.loads(item["incomplete_arguments_json"])
    except (KeyError, json.JSONDecodeError, TypeError):
        return False, "invalid_arguments_json"
    if not isinstance(complete, dict) or not isinstance(incomplete, dict):
        return False, "arguments_not_objects"
    if not set(required).issubset(complete) or set(required) - {missing} != set(incomplete):
        return False, "required_argument_coverage"
    if missing in incomplete or not set(complete).issubset(properties) or not set(incomplete).issubset(properties):
        return False, "argument_schema_mismatch"
    return True, "accepted_structure"


def make_judge_prompt(job: dict[str, Any], item: dict[str, Any]) -> str:
    """Build a separate label check that hides the generator's target labels."""
    # Ask the judge to classify both requests from the unchanged tools and request text.
    context = {"available_tools": job["tools"], "complete_request": item.get("complete_request", ""), "incomplete_request": item.get("incomplete_request", ""), "unsupported_request": item.get("request", "")}
    instruction = "Classify each request from the tools and request alone. For the first two, say whether they express the same task and differ by the absence of exactly one required value. Use high confidence only when the action labels and relation are clear."
    return f"{LABEL_DEFINITIONS}\n{instruction}\n{json.dumps(context, ensure_ascii=False)}"


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    """Write one JSON artifact with an atomic file replacement."""
    # Keep the cost ledger valid when concurrent API jobs update it.
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


async def call_json(client: Any, semaphore: asyncio.Semaphore, prompt: str, schema: dict[str, Any], ledger: dict[str, Any], ledger_path: Path, cost_lock: asyncio.Lock, cap: float) -> tuple[dict[str, Any] | None, str]:
    """Call the Responses API under a semaphore and a shared cost cap."""
    # Reserve a fixed call cost before sending the structured request.
    async with semaphore:
        async with cost_lock:
            reserved = float(ledger["reserved_cost_usd"])
            spent = float(ledger["estimated_cost_usd"])
            if spent + reserved + RESERVED_COST_PER_CALL > cap:
                return None, "cost_cap"
            ledger["reserved_cost_usd"] = reserved + RESERVED_COST_PER_CALL
            atomic_json(ledger_path, ledger)
        try:
            response = await client.responses.create(model=MODEL, reasoning={"effort": "none"}, max_output_tokens=700, input=[{"role": "user", "content": prompt}], text={"format": schema})
            value = json.loads(response.output_text)
            usage = response.usage
            async with cost_lock:
                ledger["reserved_cost_usd"] = max(0.0, float(ledger["reserved_cost_usd"]) - RESERVED_COST_PER_CALL)
                ledger["input_tokens"] += int(usage.input_tokens or 0)
                ledger["output_tokens"] += int(usage.output_tokens or 0)
                ledger["requests"] += 1
                ledger["estimated_cost_usd"] = ledger["input_tokens"] * INPUT_PRICE_PER_MILLION / 1_000_000 + ledger["output_tokens"] * OUTPUT_PRICE_PER_MILLION / 1_000_000
                atomic_json(ledger_path, ledger)
            return value, "ok"
        except Exception as error:
            # Record only exception types so no prompt content or credentials enter the log.
            async with cost_lock:
                ledger["reserved_cost_usd"] = max(0.0, float(ledger["reserved_cost_usd"]) - RESERVED_COST_PER_CALL)
                ledger["errors"] += 1
                ledger["last_error_type"] = type(error).__name__
                atomic_json(ledger_path, ledger)
            return None, type(error).__name__


async def generate_job(job: dict[str, Any], client: Any, semaphore: asyncio.Semaphore, ledger: dict[str, Any], ledger_path: Path, cost_lock: asyncio.Lock, cap: float, seen: set[str], seen_lock: asyncio.Lock) -> dict[str, Any] | None:
    """Generate, structurally validate, and independently judge one pilot job."""
    # Retry invalid or rejected candidates up to two times to keep the pilot bounded.
    for attempt in range(2):
        prompt, schema = generation_prompt(job)
        item, status = await call_json(client, semaphore, prompt, schema, ledger, ledger_path, cost_lock, cap)
        if item is None:
            return None
        if job["kind"] == "pair":
            valid, reason = validate_pair(job, item)
        else:
            request = str(item.get("request", "")).strip()
            valid, reason = (len(request) >= 12, "accepted_structure" if len(request) >= 12 else "invalid_request")
        if not valid:
            ledger["rejected_structure"] += 1
            continue
        judgment, status = await call_json(client, semaphore, make_judge_prompt(job, item), JUDGE_FORMAT, ledger, ledger_path, cost_lock, cap)
        if judgment is None or judgment.get("confidence") != "high":
            ledger["rejected_judgment"] += 1
            continue
        if job["kind"] == "pair":
            accepted = judgment.get("complete_label") == "tool_call" and judgment.get("incomplete_label") == "request_for_info" and judgment.get("pair_preserves_intent") is True
            requests = [item["complete_request"], item["incomplete_request"]]
            labels = ["tool_call", "request_for_info"]
        else:
            accepted = judgment.get("unsupported_label") == "cannot_answer"
            requests = [item["request"]]
            labels = ["cannot_answer"]
        if not accepted:
            ledger["rejected_judgment"] += 1
            continue
        keys = [normalize(request) for request in requests]
        async with seen_lock:
            if any(key in seen for key in keys):
                ledger["rejected_duplicate"] += 1
                continue
            seen.update(keys)
        rows = []
        for request, label in zip(requests, labels):
            synthetic = {"messages": [{"role": "user", "content": request}], "tools": job["tools"]}
            rows.append({"prompt": make_prompt(synthetic), "label": LABEL_TO_ID[label], "label_name": label, "augmentation_type": "paired_required_argument_boundary" if job["kind"] == "pair" else "plausible_unsupported_capability", "source_indices": job["source_indices"], "request": request, "scenario_note": item.get("scenario_note", ""), "judge_reason": judgment.get("reason", ""), "attempts": attempt + 1})
        return {"slot": job["slot"], "kind": job["kind"], "rows": rows, "source_indices": job["source_indices"]}
    return None


async def run(args: argparse.Namespace) -> dict[str, Any]:
    """Generate the bounded, three-class balanced synthetic set."""
    # Load train_pref only and build unique anchors from its tool-call and cannot-answer rows.
    source_rows = load_rows()
    prepared = prepare_rows(source_rows)
    jobs = build_jobs(source_rows, prepared, args.pairs, args.unsupported, args.seed, args.anchor_strategy)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    output_path = args.output_dir / f"balanced_boundary_{args.anchor_strategy}.jsonl"
    audit_path = args.output_dir / "generation-audit.jsonl"
    ledger_path = args.output_dir / "cost-ledger.json"
    seen = {normalize(source_request(row)) for row in source_rows}
    ledger = {"model": MODEL, "source": "nvidia/When2Call train_pref", "input_price_per_million": INPUT_PRICE_PER_MILLION, "output_price_per_million": OUTPUT_PRICE_PER_MILLION, "requests": 0, "input_tokens": 0, "output_tokens": 0, "estimated_cost_usd": 0.0, "reserved_cost_usd": 0.0, "errors": 0, "rejected_structure": 0, "rejected_judgment": 0, "rejected_duplicate": 0, "max_cost_usd": args.max_cost_usd, "concurrency": args.workers, "seed": args.seed, "anchor_strategy": args.anchor_strategy}
    atomic_json(ledger_path, ledger)
    output_path.write_text("", encoding="utf-8")
    audit_path.write_text("", encoding="utf-8")
    from openai import AsyncOpenAI
    client = AsyncOpenAI(timeout=90.0, max_retries=1)
    semaphore = asyncio.Semaphore(args.workers)
    cost_lock = asyncio.Lock()
    seen_lock = asyncio.Lock()
    tasks = [asyncio.create_task(generate_job(job, client, semaphore, ledger, ledger_path, cost_lock, args.max_cost_usd, seen, seen_lock)) for job in jobs]
    accepted_pairs = accepted_unsupported = completed = 0
    with output_path.open("a", encoding="utf-8") as data_file, audit_path.open("a", encoding="utf-8") as audit_file:
        for task in asyncio.as_completed(tasks):
            result = await task
            completed += 1
            if result:
                accepted_pairs += int(result["kind"] == "pair")
                accepted_unsupported += int(result["kind"] == "unsupported")
                for row in result["rows"]:
                    data_file.write(json.dumps({key: row[key] for key in ("prompt", "label", "augmentation_type", "source_indices")}, ensure_ascii=False) + "\n")
                data_file.flush()
                audit_file.write(json.dumps({"accepted": True, **result}, ensure_ascii=False) + "\n")
            else:
                audit_file.write(json.dumps({"accepted": False, "completed_slot": completed}) + "\n")
            audit_file.flush()
            if completed % 20 == 0 or completed == len(tasks):
                print(json.dumps({"completed": completed, "total": len(tasks), "accepted_pairs": accepted_pairs, "accepted_unsupported": accepted_unsupported, "rows": 2 * accepted_pairs + accepted_unsupported, "estimated_cost_usd": ledger["estimated_cost_usd"]}), flush=True)
    await client.close()
    summary = {"status": "completed", "source": "nvidia/When2Call train_pref", "pairs_requested": args.pairs, "unsupported_requested": args.unsupported, "accepted_pairs": accepted_pairs, "accepted_unsupported": accepted_unsupported, "rows_written": 2 * accepted_pairs + accepted_unsupported, "class_counts": {"tool_call": accepted_pairs, "request_for_info": accepted_pairs, "cannot_answer": accepted_unsupported}, "output_jsonl": str(output_path), "anchor_strategy": args.anchor_strategy, "cost_ledger": str(ledger_path), "estimated_cost_usd": ledger["estimated_cost_usd"], "generation_model": MODEL, "concurrency": args.workers, "seed": args.seed, "official_test_loaded": False, "test_labels_used": False}
    atomic_json(args.output_dir / "metrics.json", summary)
    return summary


def main() -> int:
    """Parse controls and run the synthetic-data pilot generator."""
    # Enforce the total-generation cap before starting any API request.
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--pairs", type=int, default=167)
    parser.add_argument("--unsupported", type=int, default=166)
    parser.add_argument("--workers", type=int, default=24)
    parser.add_argument("--seed", type=int, default=20261095)
    parser.add_argument("--max-cost-usd", type=float, default=2.0)
    parser.add_argument("--anchor-strategy", choices=("random", "rare_schema"), default="random")
    args = parser.parse_args()
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is required.")
    if args.pairs < 1 or args.unsupported < 1 or args.workers < 1 or args.max_cost_usd <= 0:
        raise ValueError("Pair, unsupported, worker, and cost limits must be positive.")
    result = asyncio.run(run(args))
    print(json.dumps(result, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
