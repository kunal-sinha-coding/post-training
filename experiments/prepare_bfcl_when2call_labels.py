"""Build an overlap-filtered BFCL action-label corpus for a When2Call pilot.

The flow loads official BFCL Live rows, removes source-ID and question near-duplicates of the
When2Call MCQ test, assigns obvious call actions from BFCL categories, uses a local instruction
model to resolve Irrelevance rows into direct or cannot-answer actions, and writes training rows
plus aggregate labeling and provenance metadata without reading test answer labels.
"""
from __future__ import annotations

import argparse
import json
import random
import re
from collections import Counter
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

CATEGORIES = ("simple", "multiple", "parallel", "parallel_multiple", "relevance", "irrelevance")
LABELS = ("cannot_answer", "request_for_info", "tool_call", "direct")
LABEL_TO_ID = {name: index for index, name in enumerate(LABELS)}


def question_text(row: dict) -> str:
    """Join BFCL conversation messages into readable role-tagged text."""
    # Keep system guidance and user content so label decisions reflect the full interaction.
    return "\n".join(f"{message['role']}: {message.get('content', '')}" for group in row["question"] for message in group)


def tool_text(row: dict) -> str:
    """Serialize each available function schema in a stable readable form."""
    # Retain each full function definition because descriptions clarify its real capability.
    return "\n".join(json.dumps(function, ensure_ascii=False, sort_keys=True) for function in row["function"])


def ngrams(text: str) -> set[str]:
    """Return normalized character four-grams for conservative near-duplicate checks."""
    # Normalize spacing and case before comparing content across source records.
    normalized = re.sub(r"\s+", " ", text.lower()).strip()
    return {normalized[index:index + 4] for index in range(len(normalized) - 3)} if len(normalized) >= 4 else {normalized}


def similarity(left: set[str], right: set[str]) -> float:
    """Compute Jaccard similarity between two four-gram sets."""
    # Use the same overlap ratio for every candidate and every public test question.
    union = left | right
    return len(left & right) / len(union) if union else 1.0


def load_reference_counts(directory: Path) -> dict[str, int]:
    """Read reference call counts for categories with canonical BFCL calls."""
    # Keep reference answers out of the user-question matching and test-label path.
    counts = {}
    for category in ("simple", "multiple", "parallel", "parallel_multiple"):
        path = directory / f"BFCL_v4_live_{category}_answer.json"
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                item = json.loads(line)
                counts[item["id"]] = len(item.get("ground_truth", []))
    return counts


def load_teacher(model_name: str) -> tuple[object, object, torch.device]:
    """Load a local instruction model for the ambiguous Irrelevance distinction."""
    # Use the cached Qwen Instruct checkpoint and deterministic decoding for reproducibility.
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    dtype = torch.bfloat16 if device.type == "cuda" else torch.float32
    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=False)
    model = AutoModelForCausalLM.from_pretrained(model_name, torch_dtype=dtype, trust_remote_code=False).to(device)
    model.eval()
    return model, tokenizer, device


def label_irrelevance(model: object, tokenizer: object, device: torch.device, instructions: str, row: dict, max_input_tokens: int) -> dict:
    """Ask the local model whether an irrelevant-tool request is direct or unanswerable."""
    # Give the model the user request and schemas while making BFCL's no-call status explicit.
    user_prompt = (
        "Apply the supplied labeling instructions to this BFCL Irrelevance example. "
        "BFCL says none of these functions should be called. Choose only `direct` if the assistant "
        "can satisfy the request in text without a function, or `cannot_answer` if it cannot "
        "responsibly satisfy it. If that distinction is unclear, choose `needs_review`. "
        "Return one JSON object with label, confidence, and a short rationale.\n\n"
        f"Conversation:\n{question_text(row)}\n\nAvailable functions:\n{tool_text(row)}"
    )
    messages = [{"role": "system", "content": instructions}, {"role": "user", "content": user_prompt}]
    encoded = tokenizer.apply_chat_template(messages, add_generation_prompt=True, return_tensors="pt", truncation=True, max_length=max_input_tokens).to(device)
    # Decode a short JSON decision with greedy sampling so relabeling is repeatable.
    with torch.no_grad():
        generated = model.generate(encoded, max_new_tokens=100, do_sample=False, pad_token_id=tokenizer.eos_token_id)
    result = tokenizer.decode(generated[0, encoded.shape[1]:], skip_special_tokens=True).strip()
    match = re.search(r"\{.*?\}", result, flags=re.DOTALL)
    if not match:
        return {"label": "needs_review", "confidence": "low", "rationale": "The labeling model did not return parseable JSON.", "review_reason": result[:300]}
    try:
        parsed = json.loads(match.group())
    except json.JSONDecodeError:
        return {"label": "needs_review", "confidence": "low", "rationale": "The labeling model returned invalid JSON.", "review_reason": result[:300]}
    label = str(parsed.get("label", "needs_review")).strip().lower()
    if label not in {"direct", "cannot_answer", "needs_review"}:
        label = "needs_review"
    return {"label": label, "confidence": str(parsed.get("confidence", "low")).lower(), "rationale": str(parsed.get("rationale", "")), "review_reason": None if label != "needs_review" else str(parsed.get("rationale", "Uncertain distinction."))}


def action_prompt(row: dict) -> str:
    """Format the BFCL example for the same four-way classifier used by When2Call."""
    # Preserve system instructions separately while keeping the decision question and tools intact.
    systems = "\n".join(message.get("content", "") for group in row["question"] for message in group if message.get("role") == "system")
    users = "\n".join(message.get("content", "") for group in row["question"] for message in group if message.get("role") == "user")
    prompt = (
        "Classify the required assistant action. Return exactly one label: A, B, C, or D.\n"
        "A = direct answer.\nB = tool call.\nC = request for more information.\nD = cannot answer.\n\n"
    )
    if systems:
        prompt += f"Task instructions:\n{systems}\n\n"
    return prompt + f"Question: {users}\nAvailable tools:\n{tool_text(row)}\nAction label:"


def main() -> int:
    """Filter, label, split, and save the BFCL action corpus and its count report."""
    # Parse explicit source paths and reproducibility settings before reading any input data.
    parser = argparse.ArgumentParser()
    parser.add_argument("--bfcl-data-dir", type=Path, required=True)
    parser.add_argument("--when2call-test", type=Path, required=True)
    parser.add_argument("--prompt", type=Path, default=Path("prompts/bfcl_to_when2call_labels.md"))
    parser.add_argument("--model", default="Qwen/Qwen2.5-1.5B-Instruct")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=20261025)
    parser.add_argument("--validation-fraction", type=float, default=0.2)
    parser.add_argument("--similarity-threshold", type=float, default=0.8)
    parser.add_argument("--max-input-tokens", type=int, default=8192)
    args = parser.parse_args()
    instructions = args.prompt.read_text(encoding="utf-8")
    # Build the test source-ID and question indexes without reading its answer labels.
    test_rows = [json.loads(line) for line in args.when2call_test.read_text(encoding="utf-8").splitlines() if line.strip()]
    test_source_ids = {row["source_id"] for row in test_rows}
    test_questions = [ngrams(row.get("question", "")) for row in test_rows]
    # Load current official category files and count their rows before leakage filtering.
    all_rows = []
    category_counts = Counter()
    for category in CATEGORIES:
        path = args.bfcl_data_dir / f"BFCL_v4_live_{category}.json"
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        category_counts[category] = len(rows)
        for row in rows:
            row["category"] = category
            all_rows.append(row)
    # Exclude source-ID overlap first, then remove question-level near duplicates.
    disjoint = [row for row in all_rows if row["id"] not in test_source_ids]
    near_duplicate_ids = set()
    for row in disjoint:
        candidate = ngrams(question_text(row))
        if any(similarity(candidate, test_question) >= args.similarity_threshold for test_question in test_questions):
            near_duplicate_ids.add(row["id"])
    candidates = [row for row in disjoint if row["id"] not in near_duplicate_ids]
    # Load the local teacher only when unresolved no-call rows require a direct-versus-refusal decision.
    irrelevance_rows = [row for row in candidates if row["category"] == "irrelevance"]
    teacher, tokenizer, device = load_teacher(args.model) if irrelevance_rows else (None, None, None)
    reference_counts = load_reference_counts(args.bfcl_data_dir)
    # Assign BFCL call categories to tool-call action and ask the teacher to resolve no-call rows.
    labeled = []
    for row in candidates:
        category = row["category"]
        if category == "irrelevance":
            decision = label_irrelevance(teacher, tokenizer, device, instructions, row, args.max_input_tokens)
            expected_calls = 0
        else:
            decision = {"label": "tool_call", "confidence": "high", "rationale": f"BFCL {category} category expects at least one function call.", "review_reason": None}
            expected_calls = reference_counts.get(row["id"], 1 if category == "relevance" else 0)
        item = {
            "source_id": row["id"],
            "category": category,
            "question": question_text(row),
            "tools": [json.dumps(function, ensure_ascii=False, sort_keys=True) for function in row["function"]],
            "prompt": action_prompt(row),
            "label": decision["label"],
            "label_id": LABEL_TO_ID.get(decision["label"]),
            "confidence": decision["confidence"],
            "rationale": decision["rationale"],
            "expected_call_count": expected_calls,
            "review_reason": decision["review_reason"],
        }
        labeled.append(item)
    # Stratify by resolved action label and assign held-out rows with a fixed seed.
    rng = random.Random(args.seed)
    grouped = {}
    for item in labeled:
        if item["label"] != "needs_review":
            grouped.setdefault(item["label"], []).append(item)
    for group in grouped.values():
        rng.shuffle(group)
        validation_count = max(1, round(len(group) * args.validation_fraction)) if len(group) > 1 else 0
        for index, item in enumerate(group):
            item["split"] = "validation" if index < validation_count else "train"
    for item in labeled:
        item.setdefault("split", "excluded_needs_review")
    # Save labeled prompts and audit metadata so the train and validation split can be reproduced.
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("".join(json.dumps(item, ensure_ascii=False) + "\n" for item in labeled), encoding="utf-8")
    report = {
        "bfcl_source": "https://github.com/ShishirPatil/gorilla/tree/main/berkeley-function-call-leaderboard/bfcl_eval/data",
        "when2call_test_used_for": "source_id and question-only overlap exclusion; answer labels were not read",
        "bfcl_category_counts": dict(category_counts),
        "source_id_disjoint_count": len(disjoint),
        "near_duplicate_excluded_count": len(near_duplicate_ids),
        "near_duplicate_threshold": args.similarity_threshold,
        "labeled_candidate_count": len(labeled),
        "label_counts": dict(Counter(item["label"] for item in labeled)),
        "split_label_counts": {split: dict(Counter(item["label"] for item in labeled if item["split"] == split)) for split in ("train", "validation", "excluded_needs_review")},
        "category_label_counts": {category: dict(Counter(item["label"] for item in labeled if item["category"] == category)) for category in CATEGORIES},
        "excluded_needs_review_count": sum(item["label"] == "needs_review" for item in labeled),
        "model_assisted_categories": ["irrelevance"],
        "labeling_model": args.model,
        "labeling_seed": args.seed,
        "validation_fraction": args.validation_fraction,
        "output": str(args.output),
    }
    report_path = args.output.with_suffix(".metadata.json")
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
