"""Load official MBPP splits, normalize prompts, and prepare GRPO and SFT datasets."""

from __future__ import annotations

from typing import Any


DEFAULT_PROMPT_TEMPLATE = (
    "You are an expert Python programmer. Implement the function described below.\n\n"
    "Task:\n{prompt}\n\nTests:\n{tests}\n\n"
    "Your entire response must follow this exact format:\n\n"
    "Code: \n```python\ndef example():\n    pass\n```\n\n"
    "Output only one Python code block. Do not include reasoning, explanations, <think> blocks, or text outside the code block.\n"
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
    import_lines = imports if isinstance(imports, list) else [str(imports)]
    test_lines = tests if isinstance(tests, list) else [str(tests)]
    return "\n".join(str(line) for line in [*import_lines, *test_lines] if line)


def build_prompt(record: dict[str, Any], template: str = DEFAULT_PROMPT_TEMPLATE) -> str:
    """Build the text prompt consumed by the GRPO trainer and evaluator."""
    prompt = str(_first_value(record, "text", "prompt", "description", "task", default=""))
    return template.format(prompt=prompt, tests=format_tests(record))


def normalize_record(record: dict[str, Any]) -> dict[str, Any]:
    """Convert one raw MBPP row into the stable training schema."""
    return {
        "task_id": _first_value(record, "task_id", "id", default=None),
        "prompt": build_prompt(record),
        "test_code": format_tests(record),
        "reference_code": str(_first_value(record, "code", "canonical_solution", default="")),
    }


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
) -> Any:
    """Load the requested MBPP split from the Hugging Face Hub."""
    try:
        from datasets import load_dataset
    except ImportError as exc:
        raise RuntimeError("Install the 'datasets' package to load MBPP.") from exc
    loaded = load_dataset(dataset_name, dataset_config, split=split) if dataset_config else load_dataset(dataset_name, split=split)
    return loaded.map(normalize_record)


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
    train_dataset = load_mbpp(config["dataset_name"], config.get("dataset_config"), config.get("train_split", "train"))
    validation_dataset = load_mbpp(config["dataset_name"], config.get("dataset_config"), config.get("validation_split", "validation"))
    max_train = config.get("max_train_samples")
    max_eval = config.get("max_eval_samples")

    # Limit the official training split for short debugging runs when requested.
    if max_train:
        train_dataset = train_dataset.select(range(min(int(max_train), len(train_dataset))))

    # Limit the official validation split for short debugging runs when requested.
    if max_eval:
        validation_dataset = validation_dataset.select(range(min(int(max_eval), len(validation_dataset))))
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
