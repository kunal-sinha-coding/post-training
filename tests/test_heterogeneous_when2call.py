"""Check heterogeneous metric, selection, and frozen artifact boundaries.

The tests use synthetic probabilities and mocked training rows to verify all-class metrics,
question-disjoint partitions, fixed selection roles, early failure records, and rejection
of changed model weights before any official data loader or model execution can run.
"""
import argparse
import json
import sys
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
import torch

from experiments import heterogeneous_when2call as worker


# Include absent classes in primary metrics while preserving the historical diagnostic.
def test_absent_class_macro_is_four_class():
    result = worker.metrics(torch.tensor([0, 1, 2]), torch.eye(4)[:3])
    assert result["accuracy"] == 1.0
    assert result["macro_f1"] == 0.75
    assert result["macro_precision"] == 0.75
    assert result["macro_recall"] == 0.75
    assert result["macro_f1_present_classes"] == 1.0


# Keep every method normalized and verify that entropy gating chooses the sharpest member.
def test_combination_rules_are_normalized():
    probabilities = torch.tensor([[[0.7, 0.1, 0.1, 0.1], [0.01, 0.97, 0.01, 0.01], [0.25, 0.25, 0.25, 0.25]], [[0.1, 0.1, 0.1, 0.7], [0.25, 0.25, 0.25, 0.25], [0.01, 0.01, 0.97, 0.01]]])
    labels = torch.tensor([1, 2])
    stacker = worker.fit_stacker(probabilities, labels)
    for name in ("uniform", "gate", "stacker"):
        values = worker.combine(probabilities, name, stacker)
        assert values.shape == (2, 4)
        assert torch.isfinite(values).all()
        assert torch.allclose(values.sum(-1), torch.ones(2), atol=1e-6)
    assert worker.combine(probabilities, "gate", stacker).argmax(-1).tolist() == [1, 2]
    assert torch.allclose(worker.combine(probabilities, "uniform", stacker), probabilities.mean(1))


# Remove development questions that match training despite case or whitespace changes.
def test_shared_partition_excludes_training_questions(monkeypatch):
    prompts = ["Question: Shared query\nAvailable tools:\n{}", "Question: Train only\nAvailable tools:\n{}", "Question: SHARED   query\nAvailable tools:\n{}", "Question: Fresh query\nAvailable tools:\n{}"]
    prepared = [SimpleNamespace(prompt=prompt, label=index % 3) for index, prompt in enumerate(prompts)]
    encoder_rows = [SimpleNamespace(text=prompt, label=index % 3) for index, prompt in enumerate(prompts)]
    monkeypatch.setattr(worker, "load_rows", lambda: list(range(4)))
    monkeypatch.setattr(worker, "prepare_rows", lambda raw: prepared)
    monkeypatch.setattr(worker, "prepare_train_examples", lambda raw: encoder_rows)
    monkeypatch.setattr(worker, "split_rows", lambda rows, seed: (rows[:2], rows[2:]))
    training, encoder_dev, qwen_dev, provenance = worker.partitions()
    assert training == encoder_rows[:2]
    assert encoder_dev == [encoder_rows[3]]
    assert qwen_dev == [prepared[3]]
    assert provenance["excluded_shared_questions"] == 1
    assert provenance["development_row_indices"] == [3]
    assert not {worker.question_key(row.prompt) for row in prepared[:2]} & {worker.question_key(row.prompt) for row in qwen_dev}


# Assign duplicate questions to one development role and freeze each predeclared rule.
def test_selection_roles_keep_question_groups_together(tmp_path, monkeypatch):
    output = tmp_path / "selection"
    work = tmp_path / "shared"
    work.mkdir()
    (work / "encoder").mkdir()
    (work / "encoder" / "model_state.pt").write_bytes(b"encoder")
    members = []
    for name in ("rpo", "sft"):
        checkpoint = tmp_path / name
        checkpoint.mkdir()
        (checkpoint / "adapter_model.safetensors").write_bytes(name.encode())
        members.append({"name": name, "checkpoint": str(checkpoint), "model": "mock"})
    rows = [SimpleNamespace(prompt=f"Question: Group {index // 2}\nAvailable tools:\n{{}}", label=index % 3) for index in range(8)]
    provenance = {"test_loaded": False}
    worker.save_json(work / "encoder-metrics.json", {"provenance": provenance, "max_length": 32})
    probabilities = torch.full((8, 3, 4), 0.25)
    monkeypatch.setattr(worker, "MEMBERS", members)
    monkeypatch.setattr(worker, "partitions", lambda: ([], [], rows, provenance))
    monkeypatch.setattr(worker, "member_probabilities", lambda *args: probabilities)
    run = SimpleNamespace(log=Mock())
    result = worker.select(argparse.Namespace(output_dir=output, work_dir=work), run, torch.device("cpu"))
    fit_questions = {worker.question_key(rows[index].prompt) for index in result["fitting_indices"]}
    select_questions = {worker.question_key(rows[index].prompt) for index in result["selection_indices"]}
    assert fit_questions and select_questions and not fit_questions & select_questions
    assert set(result["fitting_indices"] + result["selection_indices"]) == set(range(8))
    assert set(result["candidates"]) == {"uniform", "gate", "stacker"}
    assert all(candidate["test_status"] == "pending" and candidate["viable"] for candidate in result["candidates"].values())
    assert result["qwen_output_permutation"] == [0, 1, 2, 3]


# Reject changed frozen weights before the official dataset loader can be invoked.
def test_changed_artifact_blocks_official_loading(tmp_path, monkeypatch):
    from experiments import evaluate_qwen_when2call_test as official
    loader = Mock(side_effect=AssertionError("Official data must remain unopened."))
    monkeypatch.setattr(official, "load_official_rows", loader)
    weights = tmp_path / "weights"
    weights.write_bytes(b"changed")
    worker.save_json(tmp_path / "frozen-config.json", {"selection_complete": True, "members": worker.MEMBERS, "candidates": {"uniform": {"viable": True}}, "artifact_sha256": {str(weights): "wrong"}})
    args = argparse.Namespace(work_dir=tmp_path, output_dir=tmp_path, candidate="uniform")
    with pytest.raises(ValueError, match="Frozen model artifact changed"):
        worker.test(args, SimpleNamespace(), torch.device("cpu"))
    loader.assert_not_called()


# Reject a changed standalone encoder before loading its model or official examples.
def test_changed_standalone_encoder_blocks_execution(tmp_path, monkeypatch):
    checkpoint = tmp_path / "encoder"
    checkpoint.mkdir()
    (checkpoint / "model_state.pt").write_bytes(b"changed")
    worker.save_json(tmp_path / "encoder-metrics.json", {"checkpoint": str(checkpoint), "checkpoint_sha256": "wrong"})
    loader = Mock(side_effect=AssertionError("Model loading must not begin."))
    monkeypatch.setattr(worker, "raw_encoder", loader)
    with pytest.raises(ValueError, match="standalone encoder weights changed"):
        worker.test_encoder(argparse.Namespace(work_dir=tmp_path), SimpleNamespace(), torch.device("cpu"))
    loader.assert_not_called()


# Preserve the original startup exception and write complete failure metadata.
def test_early_failure_metadata_preserves_original_error(tmp_path, monkeypatch):
    run = SimpleNamespace(id="mock-run", url="mock-url", summary={}, finish=Mock())
    monkeypatch.setitem(sys.modules, "wandb", SimpleNamespace(init=lambda **kwargs: run))
    monkeypatch.setenv("WANDB_API_KEY", "mock-key")
    monkeypatch.setattr(sys, "argv", ["heterogeneous_when2call", "train-encoder", "--output-dir", str(tmp_path)])
    monkeypatch.setattr(worker.subprocess, "check_output", lambda *args, **kwargs: "mock-commit\n")
    monkeypatch.setattr(worker.torch.cuda, "is_available", lambda: False)
    monkeypatch.setattr(worker.threading, "Thread", lambda **kwargs: SimpleNamespace(start=lambda: None))
    def fail_startup(*args):
        # Simulate a model startup failure before the result payload is assigned.
        raise RuntimeError("original model failure")
    monkeypatch.setattr(worker, "train_encoder", fail_startup)
    with pytest.raises(RuntimeError, match="original model failure"):
        worker.main()
    result = json.loads((tmp_path / "metrics.json").read_text())
    assert result["status"] == "failed"
    assert result["error"] == "RuntimeError('original model failure')"
    assert result["git_commit"] == "mock-commit"
    assert result["wandb_run_id"] == "mock-run"
    assert json.loads((tmp_path / "heartbeat.json").read_text())["phase"] == "failed"
    run.finish.assert_called_once()
