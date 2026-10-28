"""Generate synthetic multi-turn argument-availability examples from train_pref.

The flow samples only When2Call train_pref rows, generates paired conversations where a required value is available or absent in earlier context, validates the tool arguments, checks labels with a separate high-confidence judge, and saves trainer-ready prompts with a cost ledger.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import random
from pathlib import Path
from typing import Any

from experiments.generate_when2call_boundary_pilot import (
    INPUT_PRICE_PER_MILLION,
    MODEL,
    OUTPUT_PRICE_PER_MILLION,
    RESERVED_COST_PER_CALL,
    atomic_json,
    call_json,
    eligible_rows,
    normalize,
    schema_fields,
    source_request,
)
from experiments.train_qwen_when2call import LABELS, LABEL_TO_ID, load_rows, make_prompt, prepare_rows

CONTEXT_FORMAT = {
    "type": "json_schema", "name": "when2call_contextual_pair", "strict": True,
    "schema": {"type": "object", "properties": {
        "tool_name": {"type": "string"},
        "missing_required_field": {"type": "string"},
        "prior_context_with_value": {"type": "string"},
        "prior_context_without_value": {"type": "string"},
        "assistant_acknowledgment": {"type": "string"},
        "shared_current_request": {"type": "string"},
        "complete_arguments_json": {"type": "string"},
        "incomplete_arguments_json": {"type": "string"},
        "scenario_note": {"type": "string"},
    }, "required": ["tool_name", "missing_required_field", "prior_context_with_value", "prior_context_without_value", "assistant_acknowledgment", "shared_current_request", "complete_arguments_json", "incomplete_arguments_json", "scenario_note"], "additionalProperties": False},
}
JUDGE_FORMAT = {
    "type": "json_schema", "name": "when2call_contextual_judgment", "strict": True,
    "schema": {"type": "object", "properties": {
        "complete_label": {"type": "string", "enum": list(LABELS)},
        "incomplete_label": {"type": "string", "enum": list(LABELS)},
        "pair_preserves_intent": {"type": "boolean"},
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
        "reason": {"type": "string"},
    }, "required": ["complete_label", "incomplete_label", "pair_preserves_intent", "confidence", "reason"], "additionalProperties": False},
}
LABEL_GUIDE = "Action labels: cannot_answer means no available tool can perform the request. request_for_info means a tool can do it but a required value is missing and cannot be inferred from the conversation. tool_call means the conversation supplies enough information for a listed tool. direct means no tool is needed."


def usable_target_tools(tools: list[str]) -> list[str]:
    """Return listed tools with at least one required field that has no default."""
    # Keep only schemas that can support a deterministic missing-value contrast.
    result = []
    for raw in tools:
        name, properties, required = schema_fields(raw)
        if name and any(field in properties and "default" not in properties[field] for field in required):
            result.append(raw)
    return result


def build_jobs(rows: Any, prepared: list[Any], count: int, seed: int) -> list[dict[str, Any]]:
    """Build a deterministic list of single-tool train_pref anchors."""
    # Sample only tool-call training rows with compact source tool context.
    rng = random.Random(seed)
    indices = eligible_rows(rows, prepared, "tool_call")
    indices = [index for index in indices if usable_target_tools(rows[index].get("tools", []))]
    if len(indices) < count:
        raise RuntimeError(f"Only {len(indices)} contextual generation anchors are eligible, below requested {count}.")
    rng.shuffle(indices)
    jobs = []
    for slot, index in enumerate(indices[:count]):
        job_tools = list(rows[index]["tools"])
        target = rng.choice(usable_target_tools(job_tools))
        jobs.append({"slot": slot, "source_indices": [index], "source_request": source_request(rows[index]), "tools": job_tools, "target_tool_name": schema_fields(target)[0]})
    return jobs


def generation_prompt(job: dict[str, Any]) -> str:
    """Ask for paired conversations with and without one inferable value."""
    # Keep the current request identical so only prior context changes the action label.
    instruction = "Create a novel multi-turn scenario, not a paraphrase. Use required_target_tool exactly. Choose one required field with no default. Write two prior-context messages about the same task. The with-value context must state a concrete value for the chosen field. The without-value context must preserve the same task but omit that value and must not imply it. The same shared current request must refer to the earlier context without restating the chosen value. Return exact valid argument objects for the complete context and the incomplete context, matching the tool schema. Keep the assistant acknowledgment neutral and never let it supply missing information."
    context = {"source_request_for_domain_only": job["source_request"], "available_tools": job["tools"], "required_target_tool": job["target_tool_name"]}
    return f"{LABEL_GUIDE}\n{instruction}\n{json.dumps(context, ensure_ascii=False)}"


def validate_item(job: dict[str, Any], item: dict[str, Any]) -> tuple[bool, str]:
    """Check schema identity, required argument coverage, and nonempty conversation text."""
    # Reject malformed pairs before sending them to the independent label judge.
    schemas = {schema_fields(raw)[0]: raw for raw in job["tools"]}
    raw = schemas.get(str(item.get("tool_name", "")))
    if raw is None or item.get("tool_name") != job["target_tool_name"]:
        return False, "tool_mismatch"
    _, properties, required = schema_fields(raw)
    missing = str(item.get("missing_required_field", ""))
    if missing not in required or "default" in properties.get(missing, {}):
        return False, "invalid_missing_field"
    for key in ("prior_context_with_value", "prior_context_without_value", "assistant_acknowledgment", "shared_current_request"):
        if len(str(item.get(key, "")).strip()) < 8:
            return False, "short_context"
    if normalize(item["prior_context_with_value"]) == normalize(item["prior_context_without_value"]):
        return False, "identical_contexts"
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


def judge_prompt(job: dict[str, Any], item: dict[str, Any]) -> str:
    """Ask a separate model to label both full conversations without seeing target labels."""
    # Include tool schemas and the complete dialogue history needed for inference.
    context = {
        "available_tools": job["tools"],
        "complete_conversation": [
            {"role": "user", "content": item["prior_context_with_value"]},
            {"role": "assistant", "content": item["assistant_acknowledgment"]},
            {"role": "user", "content": item["shared_current_request"]},
        ],
        "incomplete_conversation": [
            {"role": "user", "content": item["prior_context_without_value"]},
            {"role": "assistant", "content": item["assistant_acknowledgment"]},
            {"role": "user", "content": item["shared_current_request"]},
        ],
    }
    instruction = "Classify the final user request in each full conversation using all prior context. The two conversations must express the same task. Label tool_call only if all required values are available or inferable from the conversation. Label request_for_info if the selected tool is suitable but the required value is missing and cannot be inferred. Use high confidence only when the pair is clear."
    return f"{LABEL_GUIDE}\n{instruction}\n{json.dumps(context, ensure_ascii=False)}"


async def generate_one(job: dict[str, Any], client: Any, semaphore: asyncio.Semaphore, ledger: dict[str, Any], ledger_path: Path, lock: asyncio.Lock, cap: float, seen: set[str], seen_lock: asyncio.Lock) -> dict[str, Any] | None:
    """Generate, validate, judge, and serialize one multi-turn contextual pair."""
    # Retry once after structural or judgment rejection while respecting the shared cost cap.
    for attempt in range(2):
        item, _ = await call_json(client, semaphore, generation_prompt(job), CONTEXT_FORMAT, ledger, ledger_path, lock, cap)
        if item is None:
            return None
        valid, _ = validate_item(job, item)
        if not valid:
            ledger["rejected_structure"] += 1
            continue
        judgment, _ = await call_json(client, semaphore, judge_prompt(job, item), JUDGE_FORMAT, ledger, ledger_path, lock, cap)
        if judgment is None or judgment.get("confidence") != "high":
            ledger["rejected_judgment"] += 1
            continue
        accepted = judgment.get("complete_label") == "tool_call" and judgment.get("incomplete_label") == "request_for_info" and judgment.get("pair_preserves_intent") is True
        if not accepted:
            ledger["rejected_judgment"] += 1
            continue
        messages = [
            [
                {"role": "user", "content": item["prior_context_with_value"]},
                {"role": "assistant", "content": item["assistant_acknowledgment"]},
                {"role": "user", "content": item["shared_current_request"]},
            ],
            [
                {"role": "user", "content": item["prior_context_without_value"]},
                {"role": "assistant", "content": item["assistant_acknowledgment"]},
                {"role": "user", "content": item["shared_current_request"]},
            ],
        ]
        prompts = [make_prompt({"messages": dialogue, "tools": job["tools"]}) for dialogue in messages]
        async with seen_lock:
            keys = [normalize(prompt) for prompt in prompts]
            if any(key in seen for key in keys):
                ledger["rejected_duplicate"] += 1
                continue
            seen.update(keys)
        rows = [
            {"prompt": prompts[0], "label": LABEL_TO_ID["tool_call"], "augmentation_type": "context_supplied_required_value", "source_indices": job["source_indices"]},
            {"prompt": prompts[1], "label": LABEL_TO_ID["request_for_info"], "augmentation_type": "context_missing_required_value", "source_indices": job["source_indices"]},
        ]
        return {"slot": job["slot"], "rows": rows, "source_indices": job["source_indices"], "scenario_note": item.get("scenario_note", ""), "judge_reason": judgment.get("reason", ""), "attempts": attempt + 1}
    return None


async def run(args: argparse.Namespace) -> dict[str, Any]:
    """Run bounded generation from train_pref and save the trainer-ready pool."""
    # Load only train_pref rows, prepare eligible anchors, and create unique outputs.
    source_rows = load_rows()
    prepared = prepare_rows(source_rows)
    jobs = build_jobs(source_rows, prepared, args.pairs, args.seed)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    output_path = args.output_dir / "contextual_pairs.jsonl"
    audit_path = args.output_dir / "generation-audit.jsonl"
    ledger_path = args.output_dir / "cost-ledger.json"
    seen = {normalize(source_request(row)) for row in source_rows}
    ledger = {"model": MODEL, "source": "nvidia/When2Call train_pref", "input_price_per_million": INPUT_PRICE_PER_MILLION, "output_price_per_million": OUTPUT_PRICE_PER_MILLION, "requests": 0, "input_tokens": 0, "output_tokens": 0, "estimated_cost_usd": 0.0, "reserved_cost_usd": 0.0, "errors": 0, "rejected_structure": 0, "rejected_judgment": 0, "rejected_duplicate": 0, "max_cost_usd": args.max_cost_usd, "concurrency": args.workers, "seed": args.seed, "pilot_type": "multi_turn_context_value_boundary"}
    atomic_json(ledger_path, ledger)
    output_path.write_text("", encoding="utf-8")
    audit_path.write_text("", encoding="utf-8")
    from openai import AsyncOpenAI
    client = AsyncOpenAI(timeout=90.0, max_retries=1)
    semaphore = asyncio.Semaphore(args.workers)
    lock = asyncio.Lock()
    seen_lock = asyncio.Lock()
    tasks = [asyncio.create_task(generate_one(job, client, semaphore, ledger, ledger_path, lock, args.max_cost_usd, seen, seen_lock)) for job in jobs]
    accepted = completed = 0
    with output_path.open("a", encoding="utf-8") as data_file, audit_path.open("a", encoding="utf-8") as audit_file:
        for task in asyncio.as_completed(tasks):
            result = await task
            completed += 1
            if result:
                accepted += 1
                for row in result["rows"]:
                    data_file.write(json.dumps({key: row[key] for key in ("prompt", "label", "augmentation_type", "source_indices")}, ensure_ascii=False) + "\n")
                audit_file.write(json.dumps({"accepted": True, **result}, ensure_ascii=False) + "\n")
            else:
                audit_file.write(json.dumps({"accepted": False, "completed_slot": completed}) + "\n")
            data_file.flush(); audit_file.flush()
            if completed % 20 == 0 or completed == len(tasks):
                print(json.dumps({"completed": completed, "total": len(tasks), "accepted_pairs": accepted, "rows": 2 * accepted, "estimated_cost_usd": ledger["estimated_cost_usd"]}), flush=True)
    await client.close()
    summary = {"status": "completed", "source": "nvidia/When2Call train_pref", "pairs_requested": args.pairs, "accepted_pairs": accepted, "rows_written": 2 * accepted, "class_counts": {"tool_call": accepted, "request_for_info": accepted}, "output_jsonl": str(output_path), "cost_ledger": str(ledger_path), "estimated_cost_usd": ledger["estimated_cost_usd"], "generation_model": MODEL, "concurrency": args.workers, "seed": args.seed, "official_test_loaded": False, "test_labels_used": False}
    atomic_json(args.output_dir / "metrics.json", summary)
    return summary


def main() -> int:
    """Parse bounded generation settings and run the contextual pilot."""
    # Enforce positive size, concurrency, and spending limits before API calls.
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--pairs", type=int, default=300)
    parser.add_argument("--workers", type=int, default=24)
    parser.add_argument("--seed", type=int, default=20261109)
    parser.add_argument("--max-cost-usd", type=float, default=2.0)
    args = parser.parse_args()
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is required.")
    if args.pairs < 1 or args.workers < 1 or args.max_cost_usd <= 0:
        raise ValueError("Pair, worker, and cost limits must be positive.")
    result = asyncio.run(run(args))
    print(json.dumps(result, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
