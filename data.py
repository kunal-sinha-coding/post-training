"""Load MBPP, optionally add hidden synthetic tests, and prepare GRPO and SFT datasets."""

from __future__ import annotations

import json
import ast
from pathlib import Path
from typing import Any


DEFAULT_PROMPT_TEMPLATE = (
    "You are an expert Python programmer. Implement the function described below.\n\n"
    "Task:\n{prompt}\n\nTests:\n{tests}\n\n"
    "Requirements:\n"
)


def _first_value(record: dict[str, Any], *keys: str, default: Any = "") -> Any:
    """Return the first present, non-null value from a dataset record."""
    for key in keys:
        value = record.get(key)
        if value is not None:
            return value
    return default


def format_tests(record: dict[str, Any]) -> str:
    """Combine MBPP imports and assertions into executable test text."""
    imports = _first_value(record, "test_imports", "imports", default=[])
    tests = _first_value(record, "test_list", "tests", default=[])
    setup = str(_first_value(record, "test_setup_code", default=""))
    import_lines = imports if isinstance(imports, list) else [str(imports)]
    test_lines = tests if isinstance(tests, list) else [str(tests)]
    return "\n".join(str(line) for line in [setup, *import_lines, *test_lines] if line)


def build_prompt(record: dict[str, Any], template: str = DEFAULT_PROMPT_TEMPLATE, include_generic_arguments: bool = False) -> str:
    """Build the text prompt consumed by the GRPO trainer and evaluator."""
    prompt = str(_first_value(record, "text", "prompt", "description", "task", default=""))
    tests = format_tests(record)
    function_name = "the function named in the tests"
    arities: set[int] = set()
    try:
        calls = [node for node in ast.walk(ast.parse(tests)) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)]
        if calls:
            function_name = calls[0].func.id
            arities = {len(call.args) for call in calls if call.func.id == function_name}
    except SyntaxError:
        pass
    formatted = template.format(prompt=prompt, tests=tests, function_name=function_name)
    if len(arities) == 1:
        count = next(iter(arities))
        formatted += (
            f"\n- Define exactly one function named `{function_name}` with exactly {count} positional parameter"
            f"{'s' if count != 1 else ''}. Choose meaningful parameter names.\n"
            "- Return only the complete implementation, beginning with `Code:` and one fenced Python code block.\n"
            "- Do not include reasoning, explanations, `<think>` blocks, test code, placeholder implementations, or text outside the code block.\n"
            "- Implement a general solution. Do not hardcode the listed test inputs or outputs, use a lookup table, or define multiple versions of the function.\n"
        )
    if include_generic_arguments and len(arities) == 1:
        count = next(iter(arities))
        arguments = ", ".join(f"arg{i}" for i in range(1, count + 1))
        formatted += f"\nThe implementation already begins with this exact header:\n```python\ndef {function_name}({arguments}):\n```\nGenerate only the indented function body after this header.\n"
    return formatted


def normalize_record(record: dict[str, Any], include_generic_arguments: bool = False) -> dict[str, Any]:
    """Convert one raw MBPP row into the stable training schema."""
    return {
        "task_id": _first_value(record, "task_id", "id", default=None),
        "prompt": build_prompt(record, include_generic_arguments=include_generic_arguments),
        "test_code": format_tests(record),
        "reference_code": str(_first_value(record, "code", "canonical_solution", default="")),
        "test_setup_code": str(_first_value(record, "test_setup_code", default="")),
        "synthetic_test_count": 0,
    }


def load_synthetic_tests(
    path: str | Path,
    tests_per_task: int = 20,
    timeout_seconds: float = 5.0,
    validate: bool = True,
) -> dict[str, list[str]]:
    """Validate and load generated assertions keyed by task identifier."""
    # Fail closed before exposing any generated assertion to training.
    if validate:
        from synthetic_data.validate_tests import validate_artifact

        summary = validate_artifact(Path(path), tests_per_task, timeout_seconds)
        if not summary["valid"]:
            raise ValueError(f"Synthetic test validation failed with {summary['error_count']} errors: {summary['error_counts']}.")
    tests_by_task: dict[str, list[str]] = {}

    # Parse and validate every nonempty artifact record.
    with Path(path).open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            record = json.loads(line)
            task_id = str(record["task_id"])
            generated_tests = record.get("generated_tests", [])
            if task_id in tests_by_task or not isinstance(generated_tests, list) or not all(isinstance(test, str) for test in generated_tests):
                raise ValueError(f"Invalid synthetic test record on line {line_number}.")
            tests_by_task[task_id] = generated_tests
    return tests_by_task


def add_synthetic_tests(dataset: Any, tests_by_task: dict[str, list[str]], require_all: bool = True) -> Any:
    """Append hidden generated assertions to training test code without changing prompts."""
    def augment(record: dict[str, Any]) -> dict[str, Any]:
        """Attach the generated assertions for one training task."""
        generated_tests = tests_by_task.get(str(record["task_id"]))
        if generated_tests is None:
            if require_all:
                raise ValueError(f"Synthetic tests are missing for task {record['task_id']}.")
            generated_tests = []
        original_test_code = str(record["test_code"])
        return {
            "test_code": "\n".join(part for part in [original_test_code, *generated_tests] if part),
            "synthetic_test_count": len(generated_tests),
        }

    # Preserve the dataset representation used by the caller.
    if hasattr(dataset, "map"):
        return dataset.map(augment)
    return [{**record, **augment(record)} for record in dataset]


def _to_dataset(records: list[dict[str, Any]]) -> Any:
    """Convert normalized records to a Hugging Face Dataset when available."""
    try:
        from datasets import Dataset
    except ImportError:
        return records
    return Dataset.from_list(records)


def load_mbpp(
    dataset_name: str = "google-research-datasets/mbpp",
    dataset_config: str | None = None,
    split: str = "train",
    include_generic_arguments: bool = False,
) -> Any:
    """Load the requested MBPP split from the Hugging Face Hub."""
    try:
        from datasets import load_dataset
    except ImportError as exc:
        raise RuntimeError("Install the 'datasets' package to load MBPP.") from exc
    loaded = load_dataset(dataset_name, dataset_config, split=split) if dataset_config else load_dataset(dataset_name, split=split)
    # Rebuild normalized prompts so prompt-template edits cannot be hidden by a stale datasets cache.
    return loaded.map(lambda record: normalize_record(record, include_generic_arguments), load_from_cache_file=False)


def split_dataset(dataset: Any, train_fraction: float = 0.8, seed: int = 42) -> tuple[Any, Any]:
    """Create a deterministic train/test split without a validation partition."""
    if not 0 < train_fraction < 1:
        raise ValueError("train_fraction must be between zero and one.")
    if hasattr(dataset, "train_test_split"):
        split = dataset.train_test_split(test_size=1.0 - train_fraction, seed=seed)
        return split["train"], split["test"]
    records = list(dataset)
    import random

    indices = list(range(len(records)))
    random.Random(seed).shuffle(indices)
    cutoff = int(len(records) * train_fraction)
    train = [records[index] for index in indices[:cutoff]]
    test = [records[index] for index in indices[cutoff:]]
    return _to_dataset(train), _to_dataset(test)


def prepare_datasets(config: dict[str, Any]) -> tuple[Any, Any]:
    """Load official MBPP training and validation splits and apply optional debug limits."""
    include_generic_arguments = bool(config.get("include_generic_arguments", False))
    train_dataset = load_mbpp(config["dataset_name"], config.get("dataset_config"), config.get("train_split", "train"), include_generic_arguments)
    validation_dataset = load_mbpp(config["dataset_name"], config.get("dataset_config"), config.get("validation_split", "validation"), include_generic_arguments)
    max_train = config.get("max_train_samples")
    max_eval = config.get("max_eval_samples")

    # Limit the official training split for short debugging runs when requested.
    if max_train:
        train_dataset = train_dataset.select(range(min(int(max_train), len(train_dataset))))

    # Limit the official validation split for short debugging runs when requested.
    if max_eval:
        validation_dataset = validation_dataset.select(range(min(int(max_eval), len(validation_dataset))))

    # Add generated tests only to training rewards when explicitly enabled.
    if config.get("synthetic_tests_enabled", False):
        synthetic_path = config.get("synthetic_tests_path")
        if not synthetic_path:
            raise ValueError("synthetic_tests_path is required when synthetic tests are enabled.")
        train_dataset = add_synthetic_tests(
            train_dataset,
            load_synthetic_tests(
                synthetic_path,
                tests_per_task=int(config.get("synthetic_tests_per_task", 20)),
                timeout_seconds=float(config.get("synthetic_tests_validation_timeout_seconds", 5)),
            ),
            require_all=bool(config.get("synthetic_tests_require_all", True)),
        )
    return train_dataset, validation_dataset


def build_sft_dataset(dataset: Any, tokenizer: Any, config: dict[str, Any]) -> Any:
    """Tokenize MBPP demonstrations with loss masked over prompt tokens."""
    max_prompt_length = int(config.get("max_prompt_length", 512))
    max_completion_length = int(config.get("max_completion_length", 512))

    def tokenize_record(record: dict[str, Any]) -> dict[str, list[int]]:
        """Create one response-only language-modeling example."""
        prompt_ids = tokenizer(str(record["prompt"]), add_special_tokens=True, truncation=True, max_length=max_prompt_length)["input_ids"]
        response = f"Code: \n```python\n{record['reference_code'].strip()}\n```"
        response_ids = tokenizer(response, add_special_tokens=False, truncation=True, max_length=max_completion_length)["input_ids"]
        if tokenizer.eos_token_id is not None and len(response_ids) < max_completion_length:
            # End each demonstration with the model's end-of-sequence token.
            response_ids.append(tokenizer.eos_token_id)
        input_ids = [*prompt_ids, *response_ids]
        return {
            "input_ids": input_ids,
            "attention_mask": [1] * len(input_ids),
            "labels": [-100] * len(prompt_ids) + response_ids.copy(),
        }

    # Remove source columns because the language-modeling collator only needs token fields.
    if hasattr(dataset, "map"):
        return dataset.map(tokenize_record, remove_columns=dataset.column_names)
    return _to_dataset([tokenize_record(record) for record in dataset])
