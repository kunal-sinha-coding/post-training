"""Generate cached, meaning-preserving paraphrases from the When2Call preference split.

The flow starts a W&B run, loads only train_pref, samples source rows, requests paraphrases
through the Responses API, keeps the original tool schemas and inferred labels, and saves costs.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import random
import re
import sys
import time
from collections import defaultdict
from pathlib import Path

from dotenv import load_dotenv

from experiments.train_qwen_when2call import load_rows, make_prompt, prepare_rows


MODEL = "gpt-6-luna"
INPUT_PRICE_PER_MILLION = 0.10
OUTPUT_PRICE_PER_MILLION = 0.50
SYSTEM_PROMPTS = {
    "natural": """Rewrite only the user request as one natural alternative phrasing.
Preserve its full meaning, intent, requested information, constraints, numbers, dates, and named entities.
Do not answer the request. Do not add facts, requests, or details. Do not mention the action label.
Return only the rewritten user request in the required JSON field.""",
    "concise": """Rewrite only the user request as a concise, natural alternative phrasing.
Keep every requested action, constraint, number, date, and named entity. Preserve the full intent.
Do not answer the request. Do not add, remove, or infer facts or requests. Do not mention the action label.
Return only the rewritten user request in the required JSON field.""",
}


def normalized(text: str) -> str:
    """Normalize spacing and letter case for duplicate checks."""
    # Fold case and whitespace without changing any stored source text.
    return " ".join(text.casefold().split())


def source_question(row: object) -> str:
    """Join user messages from one preference example."""
    # Preserve the original message order when a request has multiple user turns.
    return "\n".join(message["content"] for message in row["messages"] if message["role"] == "user")


def tool_names(row: object) -> list[str]:
    """Extract tool names without sending full schemas to the generator."""
    # Read only tool names so the prompt stays short and source capabilities remain visible.
    names = []
    for raw in row.get("tools", []) or []:
        try:
            parsed = json.loads(raw)
            function = parsed.get("function", parsed)
            name = function.get("name") if isinstance(function, dict) else None
            if name:
                names.append(str(name))
        except (json.JSONDecodeError, TypeError, AttributeError):
            continue
    return names


def stratified_sample(labels: list[int], limit: int, seed: int) -> list[int]:
    """Sample source row indices in proportion to their observed train labels."""
    # Group indices by inherited action label before assigning proportional quotas.
    groups: dict[int, list[int]] = defaultdict(list)
    for index, label in enumerate(labels):
        groups[label].append(index)
    # Compute integer quotas and distribute rounding remainder by largest fractional parts.
    raw = {label: min(len(indices), limit * len(indices) / len(labels)) for label, indices in groups.items()}
    quotas = {label: int(value) for label, value in raw.items()}
    for label in sorted(raw, key=lambda key: raw[key] - quotas[key], reverse=True)[: limit - sum(quotas.values())]:
        quotas[label] += 1
    # Sample each class independently and sort indices for reproducible output order.
    rng = random.Random(seed)
    selected = [index for label, indices in groups.items() for index in rng.sample(indices, quotas[label])]
    return sorted(selected)


async def request_paraphrase(client: object, semaphore: asyncio.Semaphore, question: str, names: list[str], system_prompt: str) -> tuple[str | None, int, int, str | None]:
    """Request one structured paraphrase and return usage or an error type."""
    # Limit in-flight API calls while preserving direct, asynchronous Responses API requests.
    async with semaphore:
        try:
            response = await client.responses.create(
                model=MODEL,
                reasoning={"effort": "none"},
                max_output_tokens=150,
                input=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": json.dumps({"request": question, "available_tool_names": names}, ensure_ascii=False)},
                ],
                text={"format": {"type": "json_schema", "name": "question_paraphrase", "strict": True, "schema": {"type": "object", "properties": {"paraphrase": {"type": "string"}}, "required": ["paraphrase"], "additionalProperties": False}}},
            )
            # Parse the constrained response and retain billed usage for the cost ledger.
            parsed = json.loads(response.output_text)
            usage = response.usage
            return str(parsed.get("paraphrase", "")).strip(), int(usage.input_tokens or 0), int(usage.output_tokens or 0), None
        except Exception as error:
            # Return only the error class so source content and credentials stay out of logs.
            return None, 0, 0, type(error).__name__


async def indexed_request(index: int, client: object, semaphore: asyncio.Semaphore, question: str, names: list[str], system_prompt: str) -> tuple[int, str | None, int, int, str | None]:
    """Attach the source index to one asynchronous generation result."""
    # Return the index with the result so completion order cannot change provenance.
    result, input_tokens, output_tokens, error = await request_paraphrase(client, semaphore, question, names, system_prompt)
    return index, result, input_tokens, output_tokens, error


def update_ledger(path: Path, ledger: dict) -> None:
    """Persist request counts and estimated generation cost after each response."""
    # Replace the cost ledger atomically so an interrupted run can resume safely.
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(ledger, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


async def generate(args: argparse.Namespace, run: object) -> dict:
    """Sample train rows, create prompt variants, and save each result as it completes."""
    # Load only the When2Call preference training split after W&B is ready.
    source_rows = load_rows()
    prepared = prepare_rows(source_rows)
    if len(source_rows) != 9000:
        raise RuntimeError(f"Expected 9,000 train_pref rows, found {len(source_rows)}.")
    # Select a fixed label-stratified subset and reuse saved source indices on restart.
    selected = stratified_sample([row.label for row in prepared], min(args.limit, len(prepared)), args.sample_seed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    existing = {}
    if args.output.exists():
        with args.output.open(encoding="utf-8") as handle:
            existing = {item["source_index"]: item for item in (json.loads(line) for line in handle if line.strip())}
    # Initialize actual usage and spend, then keep both cached across process restarts.
    ledger = {"model": MODEL, "input_price_per_million": INPUT_PRICE_PER_MILLION, "output_price_per_million": OUTPUT_PRICE_PER_MILLION, "prior_spend_usd": args.prior_spend_usd, "input_tokens": 0, "output_tokens": 0, "requests": 0, "accepted": len(existing), "rejected": 0, "estimated_cost_usd": 0.0, "total_spend_usd": args.prior_spend_usd, "max_cost_usd": args.max_cost_usd}
    if args.ledger.exists():
        ledger.update(json.loads(args.ledger.read_text(encoding="utf-8")))
    update_ledger(args.ledger, ledger)
    # Create asynchronous API workers only for source examples that are not already cached.
    from openai import AsyncOpenAI
    client = AsyncOpenAI(timeout=90.0, max_retries=0)
    semaphore = asyncio.Semaphore(args.workers)
    system_prompt = SYSTEM_PROMPTS[args.style]
    pending = [index for index in selected if index not in existing]
    tasks = [asyncio.create_task(indexed_request(index, client, semaphore, source_question(source_rows[index]), tool_names(source_rows[index]), system_prompt)) for index in pending]
    # Append completed generations and update actual spend without storing test information.
    with args.output.open("a", encoding="utf-8") as handle:
        for task in asyncio.as_completed(tasks):
            index, result, input_tokens, output_tokens, error = await task
            ledger["requests"] += 1
            ledger["input_tokens"] += input_tokens
            ledger["output_tokens"] += output_tokens
            ledger["estimated_cost_usd"] = ledger["input_tokens"] * INPUT_PRICE_PER_MILLION / 1_000_000 + ledger["output_tokens"] * OUTPUT_PRICE_PER_MILLION / 1_000_000
            ledger["total_spend_usd"] = ledger["prior_spend_usd"] + ledger["estimated_cost_usd"]
            accepted = False
            reason = error
            if result:
                # Reject unchanged, empty, excessively short, or number-altered variants.
                original = source_question(source_rows[index])
                digits_match = re.findall(r"\d+(?:\.\d+)?", original) == re.findall(r"\d+(?:\.\d+)?", result)
                length_ok = max(1, len(original) * 0.5) <= len(result) <= max(80, len(original) * 2)
                accepted = normalized(result) != normalized(original) and digits_match and length_ok
                reason = None if accepted else "surface_or_numeric_validation"
            if accepted:
                # Rebuild the original training prompt with only its user request replaced.
                source = source_rows[index]
                copied = {key: source[key] for key in source.keys()}
                copied["messages"] = [dict(message) for message in source["messages"]]
                user_indices = [position for position, message in enumerate(copied["messages"]) if message["role"] == "user"]
                if len(user_indices) == 1:
                    copied["messages"][user_indices[0]]["content"] = result
                    prompt = make_prompt(copied)
                    item = {"source_index": index, "prompt": prompt, "label": prepared[index].label, "augmentation_type": "api_question_paraphrase", "model": MODEL}
                    handle.write(json.dumps(item, ensure_ascii=False) + "\n")
                    handle.flush()
                    ledger["accepted"] += 1
                else:
                    accepted = False
                    reason = "multi_turn_source_not_rewritten"
            if not accepted:
                ledger["rejected"] += 1
            ledger["last_result"] = {"source_index": index, "accepted": accepted, "reason": reason}
            update_ledger(args.ledger, ledger)
            # Stop launching further work if the hard generation budget is reached.
            if ledger["requests"] % 25 == 0:
                run.log({"generation/accepted": ledger["accepted"], "generation/rejected": ledger["rejected"], "generation/estimated_cost_usd": ledger["estimated_cost_usd"]})
            if ledger.get("total_spend_usd", args.prior_spend_usd) >= args.max_cost_usd:
                break
    # Cancel any pending requests after the output loop ends at the budget guard.
    for task in tasks:
        if not task.done():
            task.cancel()
    if any(not task.done() for task in tasks):
        await asyncio.gather(*tasks, return_exceptions=True)
    await client.close()
    # Record the final source, selection, and cost summary for reproduction.
    result = {"status": "completed", "source_dataset": "nvidia/When2Call:train_pref", "source_examples": len(source_rows), "sample_indices": selected, "sample_seed": args.sample_seed, "style": args.style, "model": MODEL, "output": str(args.output), "accepted": ledger["accepted"], "rejected": ledger["rejected"], "cost_ledger": str(args.ledger), "usage": ledger, "official_test_loaded": False, "wandb_run_id": run.id, "wandb_run_url": run.url}
    args.summary.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    run.summary.update({"accepted": ledger["accepted"], "estimated_cost_usd": ledger["estimated_cost_usd"], "official_test_loaded": False})
    return result


def main() -> int:
    """Initialize W&B, enforce the generation budget, and run the cached paraphrase job."""
    # Parse budget and artifact settings before loading training data.
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=1000)
    parser.add_argument("--sample-seed", type=int, default=20261067)
    parser.add_argument("--workers", type=int, default=16)
    # Select a distinct rewrite objective while preserving the same input and acceptance checks.
    parser.add_argument("--style", choices=tuple(SYSTEM_PROMPTS), default="natural")
    parser.add_argument("--prior-spend-usd", type=float, default=0.0)
    parser.add_argument("--max-cost-usd", type=float, default=0.5)
    args = parser.parse_args()
    # Load credentials and fail before data access if API or W&B access is unavailable.
    load_dotenv()
    if not os.getenv("OPENAI_API_KEY") or not os.getenv("WANDB_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY and WANDB_API_KEY are required.")
    # Reject unsafe sample and cost limits before starting API work.
    if args.limit < 1 or args.workers < 1 or args.max_cost_usd <= args.prior_spend_usd:
        raise ValueError("The sample, concurrency, and remaining cost budget must be positive.")
    import wandb
    # Start an auditable run before loading the source examples.
    run = wandb.init(project=os.getenv("WANDB_PROJECT", "when2call-research"), entity=os.getenv("WANDB_ENTITY"), name=args.output.parent.name, job_type="when2call-question-paraphrase-generation", config={"command": [sys.executable, "-m", "experiments.augment_when2call_questions", *sys.argv[1:]], "model": MODEL, "limit": args.limit, "sample_seed": args.sample_seed, "workers": args.workers, "style": args.style, "prior_spend_usd": args.prior_spend_usd, "max_cost_usd": args.max_cost_usd, "official_test_loaded": False})
    started = time.time()
    try:
        asyncio.run(generate(args, run))
    finally:
        # Finish W&B even if the generator exits on an API or disk error.
        run.finish()
    return 0


if __name__ == "__main__":
    # Exit with an error code when generation fails.
    raise SystemExit(main())
