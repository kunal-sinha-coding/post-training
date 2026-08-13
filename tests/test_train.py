"""Verify training callbacks and the dynamic reward schedule without running a model."""

from types import SimpleNamespace

import train


def test_reward_pass_weight_transitions_smoothly():
    """Use dense reward early and mostly binary pass reward after step 200."""
    assert train.reward_pass_weight(150, 150, 200, 0.9) == 0.0
    assert train.reward_pass_weight(175, 150, 200, 0.9) == 0.45
    assert train.reward_pass_weight(200, 150, 200, 0.9) == 0.9


class FakeModel:
    """Track whether evaluation restores training mode."""

    def __init__(self):
        """Initialize the training call count."""
        self.train_calls = 0

    def train(self):
        """Record one restoration of training mode."""
        self.train_calls += 1


def test_sft_callback_evaluates_completed_epoch(monkeypatch, tmp_path):
    """The SFT callback should save and log one evaluation per epoch."""
    calls = []
    model = FakeModel()
    metrics = {"pass_at_1": 0.5}
    details = [{"task_id": 1}]

    def fake_evaluate(callback_model, tokenizer, dataset, config, name):
        """Return deterministic metrics and record the evaluation name."""
        del callback_model, tokenizer, dataset, config
        calls.append(("evaluate", name))
        return metrics, details

    def fake_save(output_dir, name, saved_metrics, saved_details, config):
        """Record the saved epoch artifacts."""
        calls.append(("save", str(output_dir), name, saved_metrics, saved_details, config["_evaluation_epoch"]))

    def fake_log(wandb, logged_metrics, name, step):
        """Record the W&B evaluation event."""
        del wandb
        calls.append(("log", name, logged_metrics, step))

    monkeypatch.setattr(train, "evaluate_model", fake_evaluate)
    monkeypatch.setattr(train, "save_evaluation", fake_save)
    monkeypatch.setattr(train, "log_evaluation", fake_log)
    config = {"sft_loss_rolling_window": 3}
    callback = train._make_sft_callback(model, object(), [object()], config, None)

    callback.on_epoch_end(
        SimpleNamespace(output_dir=str(tmp_path)),
        SimpleNamespace(epoch=1.0, global_step=10),
        SimpleNamespace(),
    )

    assert calls == [
        ("evaluate", "sft-epoch-1"),
        ("save", str(tmp_path), "sft-epoch-1", metrics, details, 1),
        ("log", "sft-epoch-1", metrics, 10),
    ]
    assert callback.latest_metrics == metrics
    assert callback.latest_details == details
    assert model.train_calls == 1
