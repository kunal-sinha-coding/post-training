from data import build_prompt, normalize_record, split_dataset


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
