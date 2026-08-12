from data import build_prompt, build_sft_dataset, normalize_record, split_dataset


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


def test_prompt_template_can_be_overridden():
    assert build_prompt({"prompt": "Do it", "test_list": []}, "TASK: {prompt}\nTESTS: {tests}") == "TASK: Do it\nTESTS: "


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
