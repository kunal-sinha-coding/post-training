"""Build reproducible MBPP category prompts from the saved task taxonomy.

The script loads the task-level taxonomy and checkpoint-830 tests, samples three
same-category examples for each requested prompt, and writes prompt records as JSONL.
The category count is configurable so a small prompt preview and a larger generation
batch use the same prompt format.
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
TAXONOMY_PATH = ROOT / "analysis" / "mbpp_task_taxonomy_10x.json"
GENERATION_PATH = ROOT / "analysis" / "checkpoint_830" / "checkpoint_830_training_generations.jsonl"


def load_generation_records(path: Path) -> dict[int, dict[str, Any]]:
    """Load the saved training tests by task ID."""
    records: dict[int, dict[str, Any]] = {}
    # Read each checkpoint archive row once so every prompt can reuse its tests.
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            records[int(row["task_id"])] = row
    return records


def render_prompt(category: dict[str, Any], examples: list[dict[str, Any]], tests_by_id: dict[int, dict[str, Any]]) -> str:
    """Render one task-generation prompt with three same-category examples."""
    instructions = (
        "Create one original, self-contained Python programming task in the requested category. "
        "Match the examples in scope and difficulty. Do not copy their wording, function names, "
        "inputs, outputs, or algorithms. State the required behavior and edge cases clearly. "
        "Return one JSON object with exactly these keys: category, task_text, entry_point, "
        "reference_solution, test_inputs. The reference_solution must define the entry_point "
        "as one plain Python function. Do not use imports, classes, helper functions, filesystem "
        "access, network access, randomness, or time. The test_inputs value must contain exactly "
        "three executable Python call expressions that use literal arguments to call entry_point. "
        "Do not include expected outputs or assertions. Do not include explanations or Markdown fences."
    )
    # Include the saved original assertions as examples of task scope and test style.
    blocks = []
    for index, example in enumerate(examples, start=1):
        task_id = int(example["task_id"])
        tests = tests_by_id[task_id]["test_code"].strip()
        blocks.append(
            f"Example {index} task (training task {task_id}):\n\n{example['task_text']}\n\n"
            f"Example tests:\n\n```python\n{tests}\n```"
        )
    # State the category and output contract before the three demonstrations.
    return (
        f"Generate one new MBPP-style task in category {category['category']!r}.\n\n"
        f"Category definition: {category['definition']}\n\n{instructions}\n\n"
        + "\n\n".join(blocks)
        + "\n\nReturn only the required JSON object for one new task."
    )


def allocate_prompt_counts(categories: list[dict[str, Any]], total_prompts: int) -> list[int]:
    """Allocate a total prompt count in proportion to each category's training count."""
    # Use the largest-remainder method so integer category counts sum to the requested total.
    total_training = sum(int(category["training_count"]) for category in categories)
    exact_counts = [total_prompts * int(category["training_count"]) / total_training for category in categories]
    counts = [int(value) for value in exact_counts]
    remaining = total_prompts - sum(counts)
    order = sorted(range(len(categories)), key=lambda index: exact_counts[index] - counts[index], reverse=True)
    # Give leftover prompts to the categories with the largest fractional remainders.
    for index in order[:remaining]:
        counts[index] += 1
    return counts


def generate_prompts(taxonomy_path: Path, generations_path: Path, output_path: Path, prompts_per_category: int | None, seed: int, total_prompts: int | None = None) -> int:
    """Sample examples and save the requested prompts for every category."""
    if total_prompts is not None and total_prompts < 1:
        raise ValueError("total_prompts must be at least one")
    if total_prompts is None and (prompts_per_category is None or prompts_per_category < 1):
        raise ValueError("prompts_per_category must be at least one")
    # Load the taxonomy and source tests before sampling examples.
    taxonomy = json.loads(taxonomy_path.read_text(encoding="utf-8"))
    # Preserve the training-set category proportions when a total prompt count is requested.
    category_counts = allocate_prompt_counts(taxonomy["categories"], total_prompts) if total_prompts is not None else [prompts_per_category] * len(taxonomy["categories"])
    tests_by_id = load_generation_records(generations_path)
    rng = random.Random(seed)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    prompt_count = 0
    # Write a fixed number of independently sampled prompts for every category.
    with output_path.open("w", encoding="utf-8") as handle:
        for category_index, (category, prompt_count_for_category) in enumerate(zip(taxonomy["categories"], category_counts), start=1):
            examples_pool = category["tasks"]
            if len(examples_pool) < 3:
                raise ValueError(f"Category {category['category']!r} has fewer than three examples")
            for ordinal in range(1, prompt_count_for_category + 1):
                examples = rng.sample(examples_pool, 3)
                prompt = render_prompt(category, examples, tests_by_id)
                # Save provenance beside the full prompt so each draw can be audited.
                record = {
                    "prompt_id": f"{category_index:02d}-{ordinal:03d}",
                    "category": category["category"],
                    "category_training_count": category["training_count"],
                    "category_prompt_count": prompt_count_for_category,
                    "example_task_ids": [int(example["task_id"]) for example in examples],
                    "prompt": prompt,
                }
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
                prompt_count += 1
    return prompt_count


def parse_args() -> argparse.Namespace:
    """Parse paths, sample count, and random seed from the command line."""
    # Keep the preview count explicit while allowing larger per-category batches.
    parser = argparse.ArgumentParser(description="Generate reproducible MBPP category prompts.")
    parser.add_argument("--taxonomy", type=Path, default=TAXONOMY_PATH)
    parser.add_argument("--generations", type=Path, default=GENERATION_PATH)
    parser.add_argument("--output", type=Path, default=ROOT / "analysis" / "mbpp_category_prompt_preview.jsonl")
    parser.add_argument("--prompts-per-category", type=int, default=1)
    # Allow proportional allocation when the desired total is known.
    parser.add_argument("--total-prompts", type=int, default=None)
    parser.add_argument("--seed", type=int, default=20261006)
    return parser.parse_args()


if __name__ == "__main__":
    # Generate the configured prompt set and report its row count.
    args = parse_args()
    # Use per-category counts by default and proportional counts when requested.
    count = generate_prompts(args.taxonomy, args.generations, args.output, args.prompts_per_category, args.seed, args.total_prompts)
    print(f"Wrote {count} prompts to {args.output}", flush=True)
