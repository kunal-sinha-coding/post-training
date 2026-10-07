"""Generate category-balanced MBPP tasks through the OpenAI API and validate their tests.

The script builds proportional prompts from the saved taxonomy, samples three same-category
training tasks for each prompt, calls GPT-6 Luna with bounded concurrency, validates each
JSON response, executes its reference solution in the repository sandbox, and saves task,
assertion, usage, and cost artifacts for audit and training.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from openai import AsyncOpenAI

# Resolve repository paths and import the shared prompt and sandbox validators.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from analysis.generate_mbpp_category_prompts import generate_prompts
from analysis.materialize_mbpp_category_tasks import materialize_task

# Set standard GPT-6 Luna text rates in dollars per million tokens.
INPUT_RATE = 0.10
CACHED_INPUT_RATE = 0.01
OUTPUT_RATE = 0.50
MODEL = "gpt-6-luna"


def parse_args() -> argparse.Namespace:
    """Parse generation, prompt, concurrency, retry, and artifact options."""
    # Keep defaults aligned with the 100-task pilot and its saved taxonomy.
    parser = argparse.ArgumentParser(description="Generate and sandbox category-balanced MBPP tasks with the OpenAI API.")
    parser.add_argument("--taxonomy", type=Path, default=ROOT / "analysis" / "mbpp_task_taxonomy_10x.json")
    parser.add_argument("--generations", type=Path, default=ROOT / "analysis" / "checkpoint_830" / "checkpoint_830_training_generations.jsonl")
    parser.add_argument("--prompts", type=Path, default=ROOT / "analysis" / "mbpp_category_api_prompts_100.jsonl")
    parser.add_argument("--specs", type=Path, default=ROOT / "analysis" / "mbpp_category_synthetic_task_specs_api100.jsonl")
    parser.add_argument("--tasks", type=Path, default=ROOT / "analysis" / "mbpp_category_synthetic_tasks_api100.jsonl")
    parser.add_argument("--usage-summary", type=Path, default=ROOT / "analysis" / "mbpp_category_api_usage_100.json")
    parser.add_argument("--state-dir", type=Path, default=ROOT / "outputs" / "mbpp_synthetic_api100")
    parser.add_argument("--total-tasks", type=int, default=100)
    parser.add_argument("--seed", type=int, default=20261007)
    parser.add_argument("--concurrency", type=int, default=20)
    parser.add_argument("--limit", type=int, default=None, help="Generate only the first N prompts for a sanity check.")
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--timeout-seconds", type=float, default=5.0)
    return parser.parse_args()


def load_prompts(args: argparse.Namespace) -> list[dict[str, Any]]:
    """Create proportional prompts once or load the saved prompt set for resumption."""
    # Generate prompts with three sampled same-category examples when no prompt file exists.
    if not args.prompts.exists():
        count = generate_prompts(args.taxonomy, args.generations, args.prompts, None, args.seed, args.total_tasks)
        print(f"Created {count} category-proportional prompts at {args.prompts}.", flush=True)
    # Read each prompt record and require the saved prompt set to match the requested size.
    prompts = [json.loads(line) for line in args.prompts.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(prompts) != args.total_tasks:
        raise ValueError(f"Expected {args.total_tasks} prompts in {args.prompts}, found {len(prompts)}")
    # Check that every prompt has exactly three source tasks from its declared category.
    if any(not row.get("prompt") or len(row.get("example_task_ids", [])) != 3 for row in prompts):
        raise ValueError("Every saved prompt must contain prompt text and three example task IDs")
    return prompts


def token_cost(input_tokens: int, output_tokens: int, cached_input_tokens: int = 0) -> float:
    """Calculate standard GPT-6 Luna token cost from API usage counts."""
    # Price cached input at its published rate and all other tokens at standard rates.
    uncached_input = max(0, input_tokens - cached_input_tokens)
    return (uncached_input * INPUT_RATE + cached_input_tokens * CACHED_INPUT_RATE + output_tokens * OUTPUT_RATE) / 1_000_000


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    """Append one durable JSONL record and flush it to disk."""
    # Flush and sync each usage record so a stopped run keeps its cost ledger.
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


async def generate_one(
    prompt_row: dict[str, Any],
    client: AsyncOpenAI,
    semaphore: asyncio.Semaphore,
    state_dir: Path,
    usage_path: Path,
    usage_lock: asyncio.Lock,
    progress_lock: asyncio.Lock,
    progress: dict[str, int | float],
    retries: int,
    timeout_seconds: float,
    force: bool = False,
) -> dict[str, Any]:
    """Generate, validate, and sandbox one task while recording token usage."""
    # Reuse a fully validated task after interruption so completed API calls are not repeated.
    prompt_id = prompt_row["prompt_id"]
    state_path = state_dir / f"{prompt_id}.json"
    if state_path.exists() and not force:
        saved = json.loads(state_path.read_text(encoding="utf-8"))
        if saved.get("status") == "passed":
            async with progress_lock:
                progress["completed"] += 1
                print_progress(progress)
            return saved
    total_input = 0
    total_output = 0
    total_cached = 0
    last_error = "unknown generation error"
    # Retry malformed or invalid generations and keep each returned usage entry in the ledger.
    for attempt in range(1, retries + 2):
        try:
            async with semaphore:
                response = await client.responses.create(
                    model=MODEL,
                    input=prompt_row["prompt"],
                    reasoning={"effort": "none"},
                    text={"format": {"type": "json_object"}},
                    max_output_tokens=3000,
                )
            usage = response.usage
            input_tokens = int(usage.input_tokens) if usage else 0
            output_tokens = int(usage.output_tokens) if usage else 0
            cached_tokens = int(getattr(getattr(usage, "input_tokens_details", None), "cached_tokens", 0) or 0) if usage else 0
            total_input += input_tokens
            total_output += output_tokens
            total_cached += cached_tokens
            usage_row = {
                "prompt_id": prompt_id,
                "attempt": attempt,
                "model": MODEL,
                "input_tokens": input_tokens,
                "cached_input_tokens": cached_tokens,
                "output_tokens": output_tokens,
                "cost_usd": token_cost(input_tokens, output_tokens, cached_tokens),
            }
            # Serialize usage ledger writes to avoid interleaved records from concurrent calls.
            async with usage_lock:
                await asyncio.to_thread(append_jsonl, usage_path, usage_row)
                progress["api_calls"] += 1
                progress["input_tokens"] += input_tokens
                progress["output_tokens"] += output_tokens
                progress["cost_usd"] += usage_row["cost_usd"]
            data = json.loads(response.output_text)
            required = {"category", "task_text", "entry_point", "reference_solution", "test_inputs"}
            if set(data) != required:
                raise ValueError(f"response keys must be exactly {sorted(required)}")
            if data["category"] != prompt_row["category"]:
                raise ValueError("response category does not match its prompt")
            task = {"prompt_id": prompt_id, **data}
            # Run synchronous sandbox subprocesses outside the event loop so API tasks can progress concurrently.
            materialized = await asyncio.to_thread(materialize_task, task, timeout_seconds)
            materialized["example_task_ids"] = prompt_row["example_task_ids"]
            materialized["generation_model"] = MODEL
            record = {
                "status": "passed",
                "spec": task,
                "task": materialized,
                "usage": {"input_tokens": total_input, "cached_input_tokens": total_cached, "output_tokens": total_output},
                "attempts": attempt,
            }
            # Save each accepted record atomically before marking it complete.
            temporary_path = state_path.with_suffix(".tmp")
            temporary_path.write_text(json.dumps(record, ensure_ascii=False) + "\n", encoding="utf-8")
            os.replace(temporary_path, state_path)
            async with progress_lock:
                progress["completed"] += 1
                print_progress(progress)
            return record
        except Exception as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            if attempt <= retries:
                await asyncio.sleep(min(2 ** (attempt - 1), 8))
    # Preserve terminal errors so the caller can stop before training on an incomplete dataset.
    record = {"status": "failed", "prompt_id": prompt_id, "error": last_error, "attempts": retries + 1}
    state_path.write_text(json.dumps(record, ensure_ascii=False) + "\n", encoding="utf-8")
    async with progress_lock:
        progress["failed"] += 1
        print_progress(progress)
    return record


def print_progress(progress: dict[str, int | float]) -> None:
    """Print completed work, token counts, and current estimated API spend."""
    # Show cumulative costs as successful response usage is written to the ledger.
    print(
        f"Progress {progress['completed'] + progress['failed']}: "
        f"{progress['completed']} passed, {progress['failed']} failed; "
        f"{progress['api_calls']} API responses; input {progress['input_tokens']:,}, "
        f"output {progress['output_tokens']:,} tokens; estimated cost ${progress['cost_usd']:.6f}.",
        flush=True,
    )


async def run(args: argparse.Namespace) -> int:
    """Run bounded API generation, persist results, and report the complete cost."""
    # Load the ignored dotenv file and stop before making requests when credentials are absent.
    load_dotenv(ROOT / ".env")
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is missing from the environment and repository .env file")
    if args.total_tasks < 1 or args.concurrency < 1 or args.retries < 0:
        raise ValueError("Task count and concurrency must be positive, and retries cannot be negative")
    if args.limit is not None and not 1 <= args.limit <= args.total_tasks:
        raise ValueError("limit must be between 1 and total_tasks")
    prompts = load_prompts(args)
    selected = prompts[: args.limit] if args.limit is not None else prompts
    args.state_dir.mkdir(parents=True, exist_ok=True)
    usage_path = args.state_dir / "usage.jsonl"
    progress: dict[str, int | float] = {"completed": 0, "failed": 0, "api_calls": 0, "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0}
    # Include usage from earlier sanity-check or resumed calls in the total cost estimate.
    if usage_path.exists():
        for line in usage_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                usage_row = json.loads(line)
                progress["api_calls"] += 1
                progress["input_tokens"] += int(usage_row.get("input_tokens", 0))
                progress["output_tokens"] += int(usage_row.get("output_tokens", 0))
                progress["cost_usd"] += float(usage_row.get("cost_usd", 0.0))
    usage_lock = asyncio.Lock()
    progress_lock = asyncio.Lock()
    semaphore = asyncio.Semaphore(args.concurrency)
    # Use an async client and an explicit semaphore to cap simultaneous requests.
    async with AsyncOpenAI(api_key=api_key) as client:
        results = await asyncio.gather(*[
            generate_one(row, client, semaphore, args.state_dir, usage_path, usage_lock, progress_lock, progress, args.retries, args.timeout_seconds)
            for row in selected
        ])
    failed = [record for record in results if record["status"] != "passed"]
    if failed:
        raise RuntimeError(f"{len(failed)} task generations failed; inspect {args.state_dir}")
    # Keep the API client open while replacing duplicate descriptions in bounded batches.
    async with AsyncOpenAI(api_key=api_key) as retry_client:
        seen_descriptions: set[str] = set()
        duplicate_indices = []
        blocked_descriptions: set[str] = set()
        # Keep the first occurrence of each description and mark later rows for replacement.
        for index, record in enumerate(results):
            description = " ".join(record["task"]["task_text"].casefold().split())
            if description in seen_descriptions:
                duplicate_indices.append(index)
                blocked_descriptions.add(description)
            seen_descriptions.add(description)
        # Keep all original descriptions out of replacement candidates.
        used_descriptions = {
            " ".join(record["task"]["task_text"].casefold().split()) for record in results
        }
        pending = duplicate_indices
        # Regenerate duplicate rows with the existing concurrency limit.
        while pending:
            batch = pending[: args.concurrency]

            async def regenerate_duplicate(index: int) -> tuple[int, dict[str, Any] | None, str]:
                """Generate one replacement while avoiding known duplicate descriptions."""
                # Give each retry the descriptions that already caused a collision.
                avoid = set(blocked_descriptions)
                avoid.add(" ".join(results[index]["task"]["task_text"].casefold().split()))
                for _ in range(args.retries + 1):
                    retry_row = {
                        **selected[index],
                        "prompt": selected[index]["prompt"]
                        + "\n\nDo not reuse these task descriptions. Create a different task:\n"
                        + json.dumps(sorted(avoid), ensure_ascii=False),
                    }
                    candidate = await generate_one(
                        retry_row, retry_client, semaphore, args.state_dir, usage_path, usage_lock,
                        progress_lock, progress, args.retries, args.timeout_seconds, force=True,
                    )
                    description = " ".join(candidate.get("task", {}).get("task_text", "").casefold().split())
                    if candidate["status"] == "passed" and description not in used_descriptions:
                        return index, candidate, description
                    # Add a repeated response to this row's next prompt.
                    avoid.add(description)
                return index, None, ""

            replacements = await asyncio.gather(*(regenerate_duplicate(index) for index in batch))
            pending = []
            # Retain distinct replacements and retry only collisions among this batch.
            for index, candidate, description in replacements:
                if candidate is None:
                    raise RuntimeError(f"Could not generate a unique task for prompt {selected[index]['prompt_id']}")
                if description in used_descriptions:
                    pending.append(index)
                    blocked_descriptions.add(description)
                else:
                    results[index] = candidate
                    used_descriptions.add(description)
            pending.extend(duplicate_indices[len(batch):])
            duplicate_indices = pending
    # Write sample outputs to separate files and only publish full artifacts after all tasks pass.
    is_sample = args.limit is not None
    specs_path = args.specs.with_name(args.specs.stem + f"_sample{args.limit}.jsonl") if is_sample else args.specs
    tasks_path = args.tasks.with_name(args.tasks.stem + f"_sample{args.limit}.jsonl") if is_sample else args.tasks
    rows = [json.dumps(record["spec"], ensure_ascii=False) for record in results]
    task_rows = [json.dumps(record["task"], ensure_ascii=False) for record in results]
    specs_path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    tasks_path.write_text("\n".join(task_rows) + "\n", encoding="utf-8")
    # Report exact recorded API usage, including calls that needed schema or sandbox retries.
    print(f"Saved {len(results)} validated task specs to {specs_path}.", flush=True)
    print(f"Saved {len(results)} sandbox-tested tasks to {tasks_path}.", flush=True)
    print_progress(progress)
    # Save exact API token usage and estimated cost as a separate reproducibility artifact.
    usage_rows = [json.loads(line) for line in usage_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    usage_summary = {
        "model": MODEL,
        "reasoning_effort": "none",
        "prompt_count": len(prompts),
        "validated_task_count": len(results),
        "api_response_count": len(usage_rows),
        "input_tokens": sum(int(row.get("input_tokens", 0)) for row in usage_rows),
        "cached_input_tokens": sum(int(row.get("cached_input_tokens", 0)) for row in usage_rows),
        "output_tokens": sum(int(row.get("output_tokens", 0)) for row in usage_rows),
        "estimated_cost_usd": round(sum(float(row.get("cost_usd", 0.0)) for row in usage_rows), 8),
        "input_rate_per_million_usd": INPUT_RATE,
        "cached_input_rate_per_million_usd": CACHED_INPUT_RATE,
        "output_rate_per_million_usd": OUTPUT_RATE,
        "semaphore_limit": args.concurrency,
    }
    if not is_sample:
        args.usage_summary.write_text(json.dumps(usage_summary, indent=2) + "\n", encoding="utf-8")
        print(f"Saved API usage and cost summary to {args.usage_summary}.", flush=True)
    return len(results)


if __name__ == "__main__":
    # Parse configuration and run the async API generation workflow.
    parsed_args = parse_args()
    generated_count = asyncio.run(run(parsed_args))
    print(f"Completed {generated_count} synthetic tasks.", flush=True)
