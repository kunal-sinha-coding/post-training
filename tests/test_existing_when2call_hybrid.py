"""Check fixed existing-model hybrids without loading data or model artifacts.

The tests preserve raw-logit encoder averaging, distinguish it from probability averaging,
verify normalized hybrid rules and entropy decisions, and reject altered frozen artifacts.
"""
import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
import torch

from experiments import existing_when2call_hybrid as hybrid


# Preserve the historical weighted raw-logit baseline before forming family probabilities.
def test_encoder_family_uses_raw_logit_average():
    logits = torch.tensor([[[9., 0., 0., 0.]], [[0., 1., 0., 0.]], [[0., 0., 3., 0.]]])
    single, ensemble = hybrid.encoder_families(logits, hybrid.WEIGHTS)
    expected = (logits * torch.tensor(hybrid.WEIGHTS).view(3, 1, 1)).sum(0).softmax(-1)
    wrong = (logits.softmax(-1) * torch.tensor(hybrid.WEIGHTS).view(3, 1, 1)).sum(0)
    assert torch.allclose(single, logits[2].softmax(-1))
    assert torch.allclose(ensemble, expected)
    assert not torch.allclose(ensemble, wrong)


# Keep fixed blends normalized and select the more confident family independently per row.
def test_fixed_hybrid_rules():
    encoder = torch.tensor([[.97, .01, .01, .01], [.25, .25, .25, .25]])
    qwen = torch.tensor([[.25, .25, .25, .25], [.01, .01, .97, .01]])
    average = hybrid.hybrid_probabilities(encoder, qwen, "average")
    gate = hybrid.hybrid_probabilities(encoder, qwen, "gate")
    assert torch.allclose(average, (encoder + qwen) / 2)
    assert torch.allclose(gate, torch.stack((encoder[0], qwen[1])))
    for values in (average, gate):
        assert torch.isfinite(values).all()
        assert torch.allclose(values.sum(-1), torch.ones(2))
    with pytest.raises(ValueError, match="Unknown frozen"):
        hybrid.hybrid_probabilities(encoder, qwen, "unfrozen")


# Reject changed weights before the official data loader can run.
def test_changed_artifact_blocks_official_loader(tmp_path, monkeypatch):
    from experiments import evaluate_qwen_when2call_test as official
    loader = Mock(side_effect=AssertionError("Official examples must remain unopened."))
    monkeypatch.setattr(official, "load_official_rows", loader)
    weights = tmp_path / "weights"
    weights.write_bytes(b"changed")
    config = {"selection_complete": True, "encoders": hybrid.ENCODERS, "qwen_checkpoint": hybrid.QWEN, "methods": list(hybrid.METHODS), "encoder_logit_weights": hybrid.WEIGHTS, "primary_method": "ensemble_average", "artifact_sha256": {str(weights): "wrong"}}
    (tmp_path / "frozen-config.json").write_text(json.dumps(config))
    with pytest.raises(ValueError, match="artifact changed"):
        hybrid.test(SimpleNamespace(work_dir=tmp_path), SimpleNamespace())
    loader.assert_not_called()


# Restore original row alignment after the shared encoder collector sorts unequal input lengths.
def test_encoder_scoring_restores_original_row_order(tmp_path, monkeypatch):
    lengths = {"row0": 5, "row1": 1, "row2": 3}
    def tokenize(text, **kwargs):
        # Assign distinct token lengths without invoking a real tokenizer.
        return {"input_ids": [1] * lengths[text]}
    def collect(model, tokenizer, examples, device, batch_size):
        # Simulate the shared collector's stable sort and encode source identity in each output.
        ordered = sorted(examples, key=lambda row: len(row.token_ids))
        return torch.tensor([[float(row.source_id)] * 4 for row in ordered]), torch.zeros(len(ordered), dtype=torch.long)
    monkeypatch.setattr(hybrid, "load_checkpoint", lambda *args: (object(), tokenize))
    monkeypatch.setattr(hybrid, "collect_logits", collect)
    monkeypatch.setattr(hybrid, "assert_size", lambda model: 1)
    monkeypatch.setattr(hybrid, "free_gpu", lambda: None)
    monkeypatch.setattr(hybrid, "write_heartbeat", lambda *args: None)
    examples = [hybrid.Example("row" + str(index), 0, str(index)) for index in range(3)]
    result = hybrid.encoder_logits("mock", examples, SimpleNamespace(output_dir=tmp_path, batch_size=2), torch.device("cpu"))
    assert result[:, 0].tolist() == [0., 1., 2.]
