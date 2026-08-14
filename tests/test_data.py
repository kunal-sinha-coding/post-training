"""Verify MBPP normalization, split loading, synthetic tests, prompting, and SFT tokenization."""

import json

from data import add_synthetic_tests, load_synthetic_tests, build_prompt, build_sft_dataset, normalize_record, prepare_datasets, split_dataset


def test_normalize_record_builds_prompt_and_tests():
    record = {"task_id": 1, "text": "Add two numbers.", "test_list": ["assert add(1, 2) == 3"]}
    normalized = normalize_record(record)
    assert normalized["task_id"] == 1
    assert "Add two numbers." in normalized["prompt"]
    assert normalized["test_code"] == "assert add(1, 2) == 3"


def test_split_dataset_is_deterministic():
    records = [{"id": index} for index in range(10)]
    first_train, first_test = split_dataset(records, 0.8, 42)
    second_train, second_test = split_dataset(records, 0.8, 42)
    assert first_train[:] == second_train[:]
    assert first_test[:] == second_test[:]
    assert len(first_train) == 8
    assert len(first_test) == 2


def test_prepare_datasets_loads_official_train_and_validation_splits(monkeypatch):
    """Dataset preparation should preserve the official MBPP split boundaries."""
    calls = []

    class Dataset(list):
        """Provide the subset selection method used by dataset preparation."""

        def select(self, indices):
            """Return the selected records in their original order."""
            return Dataset(self[index] for index in indices)

    def fake_load_mbpp(dataset_name, dataset_config, split):
        """Record each requested split and return its expected number of examples."""
        calls.append((dataset_name, dataset_config, split))
        size = 374 if split == "train" else 90
        return Dataset({"id": index} for index in range(size))

    monkeypatch.setattr("data.load_mbpp", fake_load_mbpp)
    train, validation = prepare_datasets({"dataset_name": "mbpp", "train_split": "train", "validation_split": "validation"})

    assert calls == [("mbpp", None, "train"), ("mbpp", None, "validation")]
    assert len(train) == 374
    assert len(validation) == 90


def test_prompt_template_can_be_overridden():
    assert build_prompt({"prompt": "Do it", "test_list": []}, "TASK: {prompt}\nTESTS: {tests}") == "TASK: Do it\nTESTS: "


def test_synthetic_tests_are_hidden_from_prompts(tmp_path):
    """Generated assertions should extend rewards without leaking into prompts."""
    artifact = tmp_path / "tests.jsonl"
    artifact.write_text(json.dumps({"task_id": 1, "generated_tests": ["assert add(2, 3) == 5"]}) + "\n", encoding="utf-8")
    dataset = [{"task_id": 1, "prompt": "Visible prompt", "test_code": "assert add(1, 2) == 3", "synthetic_test_count": 0}]

    # Load and attach the generated assertions.
    augmented = add_synthetic_tests(dataset, load_synthetic_tests(artifact))

    assert augmented[0]["prompt"] == "Visible prompt"
    assert augmented[0]["test_code"].splitlines() == ["assert add(1, 2) == 3", "assert add(2, 3) == 5"]
    assert augmented[0]["synthetic_test_count"] == 1


def test_build_sft_dataset_masks_prompt_tokens():
    """SFT labels should ignore the prompt and supervise the reference response."""
    class Tokenizer:
        """Provide deterministic token IDs for the focused dataset test."""

        eos_token_id = 99

        def __call__(self, text, add_special_tokens, truncation, max_length):
            """Return distinct IDs for prompt and response text."""
            del truncation, max_length
            if add_special_tokens:
                return {"input_ids": [1, 2]}
            assert "def solve" in text
            return {"input_ids": [3, 4]}

    dataset = [{"prompt": "Task", "reference_code": "def solve():\n    return 1"}]
    result = build_sft_dataset(dataset, Tokenizer(), {"max_prompt_length": 8, "max_completion_length": 8})

    assert result[0]["input_ids"] == [1, 2, 3, 4, 99]
    assert result[0]["labels"] == [-100, -100, 3, 4, 99]
    assert result[0]["attention_mask"] == [1, 1, 1, 1, 1]
