"""Label leakage-screened BFCL Live rows with GPT-6 Luna for When2Call augmentation.

The flow loads official BFCL Live categories and possible answers, removes When2Call test source-ID
and question near-duplicates without reading test labels, sends each remaining example to GPT-6 Luna
through semaphore-limited Responses API calls using the reviewed prompt, saves resumable annotations,
and writes a deterministic train and held-out split with label-count metadata.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import random
import re
from collections import Counter
from pathlib import Path

from openai import AsyncOpenAI

CATEGORIES = ("simple", "multiple", "parallel", "parallel_multiple", "relevance", "irrelevance")
LABELS = ("cannot_answer", "request_for_info", "tool_call", "direct")
LABEL_BY_CODE = {"A": "direct", "B": "tool_call", "C": "request_for_info", "D": "cannot_answer"}
OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "label": {"type": "string", "enum": ["A", "B", "C", "D"]},
        "label_name": {"type": "string", "enum": ["direct", "tool_call", "request_for_info", "cannot_answer"]},
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
        "rationale": {"type": "string"},
        "expected_call_count": {"anyOf": [{"type": "integer"}, {"type": "null"}]},
        "needs_review": {"type": "boolean"},
        "review_reason": {"anyOf": [{"type": "string"}, {"type": "null"}]},
    },
    "required": ["label", "label_name", "confidence", "rationale", "expected_call_count", "needs_review", "review_reason"],
    "additionalProperties": False,
}


def conversation_text(row: dict) -> str:
    """Join system and user messages while retaining their roles."""
    # Preserve the complete original conversation as evidence for the action decision.
    return "\n".join(f"{message['role']}: {message.get('content', '')}" for group in row["question"] for message in group)


def question_content(row: dict) -> str:
    """Join message content without role markers for the near-duplicate screen."""
    # Match the When2Call question field exactly before normalizing four-gram text.
    return " ".join(message.get("content", "") for group in row["question"] for message in group)


def tool_schemas(row: dict) -> str:
    """Serialize available function schemas in a readable stable format."""
    # Keep descriptions and required parameters so the model can assess function fit.
    return "\n".join(json.dumps(function, ensure_ascii=False, sort_keys=True) for function in row["function"])


def fourgrams(text: str) -> set[str]:
    """Create normalized character four-grams for conservative content overlap checks."""
    # Normalize case and whitespace so superficial formatting does not hide duplicate requests.
    normalized = re.sub(r"\s+", " ", text.lower()).strip()
    return {normalized[index:index + 4] for index in range(len(normalized) - 3)} if len(normalized) >= 4 else {normalized}


def jaccard(left: set[str], right: set[str]) -> float:
    """Return Jaccard similarity for two four-gram sets."""
    # Use a fixed similarity calculation for every candidate and public test question.
    union = left | right
    return len(left & right) / len(union) if union else 1.0


def load_reference_answers(directory: Path) -> dict[str, dict]:
    """Load BFCL reference calls for categories with canonical possible answers."""
    # Preserve per-example call evidence without loading any When2Call answer labels.
    references = {}
    for category in ("simple", "multiple", "parallel", "parallel_multiple"):
        path = directory / f"BFCL_v4_live_{category}_answer.json"
        if path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    item = json.loads(line)
                    references[item["id"]] = item.get("ground_truth", [])
    return references


def prepare_candidates(bfcl_directory: Path, test_path: Path, similarity_threshold: float) -> tuple[list[dict], dict]:
    """Filter BFCL rows by source ID and content overlap using test inputs only."""
    # Read only test IDs and question text, never test labels or answer choices.
    test_rows = [json.loads(line) for line in test_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    test_ids = {row["source_id"] for row in test_rows}
    test_grams = [fourgrams(row.get("question", "")) for row in test_rows]
    raw_rows, category_counts = [], Counter()
    for category in CATEGORIES:
        path = bfcl_directory / f"BFCL_v4_live_{category}.json"
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        category_counts[category] = len(rows)
        for row in rows:
            row["category"] = category
            raw_rows.append(row)
    # Remove all exact source-ID matches before the independent text-similarity check.
    source_disjoint = [row for row in raw_rows if row["id"] not in test_ids]
    duplicates = set()
    for row in source_disjoint:
        candidate = fourgrams(question_content(row))
        if any(jaccard(candidate, test) >= similarity_threshold for test in test_grams):
            duplicates.add(row["id"])
    candidates = [row for row in source_disjoint if row["id"] not in duplicates]
    audit = {
        "bfcl_category_counts": dict(category_counts),
        "when2call_test_rows": len(test_rows),
        "when2call_test_unique_source_ids": len(test_ids),
        "source_id_disjoint_count": len(source_disjoint),
        "near_duplicate_excluded_count": len(duplicates),
        "near_duplicate_threshold": similarity_threshold,
        "candidate_count": len(candidates),
        "candidate_category_counts": dict(Counter(row["category"] for row in candidates)),
        "test_answers_loaded": False,
    }
    return candidates, audit


def request_input(prompt: str, row: dict, references: dict[str, dict]) -> str:
    """Build one label request with its BFCL category, conversation, tools, and available reference."""
    # Include only BFCL training evidence and omit every When2Call label or answer field.
    reference = references.get(row["id"])
    reference_text = json.dumps(reference, ensure_ascii=False, sort_keys=True) if reference is not None else "No canonical BFCL reference call is available for this category."
    return (
        f"{prompt}\n\n"
        f"BFCL category: {row['category']}\n\n"
        f"BFCL example:\nConversation:\n{conversation_text(row)}\n\n"
        f"Available functions:\n{tool_schemas(row)}\n\n"
        f"BFCL reference call(s), if available:\n{reference_text}\n\n"
        "Return the required JSON label for this example."
    )


async def label_one(client: AsyncOpenAI, semaphore: asyncio.Semaphore, prompt: str, row: dict, references: dict[str, dict], retries: int) -> dict:
    """Request one GPT-6 Luna label and validate the structured response."""
    # Retry transient API errors with bounded exponential delays and keep the reviewed prompt fixed.
    for attempt in range(retries + 1):
        try:
            async with semaphore:
                response = await client.responses.create(
                    model="gpt-6-luna",
                    reasoning={"effort": "none"},
                    input=[{"role": "user", "content": request_input(prompt, row, references)}],
                    text={"format": {"type": "json_schema", "name": "bfcl_action_label", "strict": True, "schema": OUTPUT_SCHEMA}},
                    max_output_tokens=250,
                )
            decision = json.loads(response.output_text)
            code = decision["label"]
            label = LABEL_BY_CODE[code]
            if decision["label_name"] != label:
                raise ValueError(f"Label code and name disagree for {row['id']}.")
            return {
                "source_id": row["id"],
                "category": row["category"],
                "question": conversation_text(row),
                "tools": [json.dumps(function, ensure_ascii=False, sort_keys=True) for function in row["function"]],
                "prompt": action_prompt(row),
                "label": label,
                "label_id": LABELS.index(label),
                "label_code": code,
                "confidence": decision["confidence"],
                "rationale": decision["rationale"],
                "expected_call_count": decision["expected_call_count"],
                "needs_review": decision["needs_review"],
                "review_reason": decision["review_reason"],
                "api_model": "gpt-6-luna",
                "api_reasoning_effort": "none",
            }
        except Exception:
            if attempt >= retries:
                raise
            await asyncio.sleep(min(2 ** attempt, 30))
    raise RuntimeError(f"No label returned for {row['id']}.")


def action_prompt(row: dict) -> str:
    """Format one BFCL row as the When2Call four-way classifier input."""
    # Preserve system guidance separately and provide the original user request and tool schemas.
    systems = "\n".join(message.get("content", "") for group in row["question"] for message in group if message.get("role") == "system")
    users = "\n".join(message.get("content", "") for group in row["question"] for message in group if message.get("role") == "user")
    prefix = "Classify the required assistant action. Return exactly one label: A, B, C, or D.\nA = direct answer.\nB = tool call.\nC = request for more information.\nD = cannot answer.\n\n"
    if systems:
        prefix += f"Task instructions:\n{systems}\n\n"
    return prefix + f"Question: {users}\nAvailable tools:\n{tool_schemas(row)}\nAction label:"


def assign_split(rows: list[dict], seed: int, validation_fraction: float) -> None:
    """Assign a deterministic stratified train and validation split after labels are complete."""
    # Keep every source ID in exactly one split and preserve class representation where possible.
    rng = random.Random(seed)
    groups = {}
    for row in rows:
        groups.setdefault(row["label"], []).append(row)
    for group in groups.values():
        rng.shuffle(group)
        validation_count = max(1, round(len(group) * validation_fraction)) if len(group) > 1 else 0
        for index, row in enumerate(group):
            row["split"] = "validation" if index < validation_count else "train"


async def run(args: argparse.Namespace) -> int:
    """Label all unique candidates, resume saved work, then write final corpus and metadata."""
    # Load the fixed prompt and prepare the source-ID and content-disjoint BFCL pool.
    prompt = args.prompt.read_text(encoding="utf-8")
    prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    candidates, audit = prepare_candidates(args.bfcl_data_dir, args.when2call_test, args.similarity_threshold)
    references = load_reference_answers(args.bfcl_data_dir)
    existing = {}
    if args.output.exists():
        # Reuse complete labels from a prior interrupted run rather than paying twice for API calls.
        existing = {item["source_id"]: item for item in (json.loads(line) for line in args.output.read_text(encoding="utf-8").splitlines() if line.strip())}
    pending = [row for row in candidates if row["id"] not in existing]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    semaphore = asyncio.Semaphore(args.max_concurrency)
    client = AsyncOpenAI(timeout=args.timeout_seconds, max_retries=0)
    lock = asyncio.Lock()
    completed = len(existing)
    async def save_one(row: dict) -> None:
        # Append each successful response immediately so an interrupted annotation run can resume.
        nonlocal completed
        item = await label_one(client, semaphore, prompt, row, references, args.retries)
        async with lock:
            with args.output.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(item, ensure_ascii=False) + "\n")
            existing[item["source_id"]] = item
            completed += 1
            if completed % args.progress_every == 0 or completed == len(candidates):
                print(json.dumps({"labeled": completed, "total": len(candidates), "pending": len(candidates) - completed}), flush=True)
    # Run independent row labels concurrently while bounding in-flight API requests.
    tasks = [asyncio.create_task(save_one(row)) for row in pending]
    try:
        await asyncio.gather(*tasks)
    except Exception:
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        raise
    await client.close()
    labeled = [existing[row["id"]] for row in candidates]
    assign_split(labeled, args.seed, args.validation_fraction)
    # Rewrite labels in source order after split assignment and summarize class counts.
    args.output.write_text("".join(json.dumps(item, ensure_ascii=False) + "\n" for item in labeled), encoding="utf-8")
    metadata = {
        "experiment": "gpt6_luna_bfcl_live_to_when2call_labels",
        "prompt_path": str(args.prompt),
        "prompt_sha256": prompt_hash,
        "model": "gpt-6-luna",
        "endpoint": "OpenAI Responses API",
        "max_concurrency": args.max_concurrency,
        "retry_limit": args.retries,
        "label_split_seed": args.seed,
        "validation_fraction": args.validation_fraction,
        "labeling_scope": "Every BFCL Live row without a When2Call test source-ID match or question near-duplicate.",
        "selection_protocol": "When2Call test labels were not read or sent to the model.",
        "overlap_audit": audit,
        "label_counts": dict(Counter(item["label"] for item in labeled)),
        "split_label_counts": {split: dict(Counter(item["label"] for item in labeled if item["split"] == split)) for split in ("train", "validation")},
        "category_label_counts": {category: dict(Counter(item["label"] for item in labeled if item["category"] == category)) for category in CATEGORIES},
        "needs_review_count": sum(item["needs_review"] for item in labeled),
        "confidence_counts": dict(Counter(item["confidence"] for item in labeled)),
        "output": str(args.output),
    }
    metadata_path = args.output.with_suffix(".metadata.json")
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(metadata, indent=2), flush=True)
    return 0


def main() -> int:
    """Parse annotation settings and run the semaphore-limited labeling job."""
    # Make API concurrency, data paths, and resumability explicit command-line settings.
    parser = argparse.ArgumentParser()
    parser.add_argument("--bfcl-data-dir", type=Path, required=True)
    parser.add_argument("--when2call-test", type=Path, required=True)
    parser.add_argument("--prompt", type=Path, default=Path("prompts/bfcl_to_when2call_labels.md"))
    parser.add_argument("--output", type=Path, default=Path("data/bfcl_when2call_labeled.jsonl"))
    parser.add_argument("--max-concurrency", type=int, default=24)
    parser.add_argument("--timeout-seconds", type=float, default=120)
    parser.add_argument("--retries", type=int, default=5)
    parser.add_argument("--progress-every", type=int, default=25)
    parser.add_argument("--seed", type=int, default=20261025)
    parser.add_argument("--validation-fraction", type=float, default=0.2)
    parser.add_argument("--similarity-threshold", type=float, default=0.8)
    args = parser.parse_args()
    if args.max_concurrency < 1:
        parser.error("--max-concurrency must be positive.")
    return asyncio.run(run(args))


if __name__ == "__main__":
    # Propagate API, data, and output failures as a nonzero process status.
    raise SystemExit(main())
