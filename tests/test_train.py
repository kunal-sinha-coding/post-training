"""Verify training callbacks and fixed dense rewards without running a model."""

from types import SimpleNamespace

import train


def test_reward_stays_dense(monkeypatch, tmp_path):
    """Pass zero binary weight to the sandbox at every training step."""
    captured = {}

    # Capture the pass weight without executing candidate code.
    def fake_reward_function(completions, test_code, timeout, **kwargs):
        """Return a fixed reward after recording the configured pass weight."""
        del completions, test_code, timeout
        captured["pass_weight"] = kwargs["pass_weight"]
        return [0.0]

    monkeypatch.setattr(train, "reward_function", fake_reward_function)
    reward = train._make_reward({"log_path": str(tmp_path / "logs.txt"), "num_generations": 1})
    reward(["completion"], ["assert solve() == 1"])

    assert captured["pass_weight"] == 0.5


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


def test_checkpoint_callback_stops_after_patience(monkeypatch, tmp_path):
    """Stop training after three checkpoint evaluations without a pass rate improvement."""
    from pathlib import Path

    class CallbackModel:
        """Provide the model object required by the checkpoint callback."""

    metrics = {"pass_at_1": 0.25}

    def fake_evaluate(*_args):
        """Return the same evaluation metric for every checkpoint."""
        return metrics, []

    def fake_save(*_args):
        """Avoid writing evaluation artifacts during the callback test."""

    def fake_log(*_args):
        """Avoid sending test metrics to W&B."""

    monkeypatch.setattr(train, "evaluate_model", fake_evaluate)
    monkeypatch.setattr(train, "save_evaluation", fake_save)
    monkeypatch.setattr(train, "log_evaluation", fake_log)
    config = {"run_intermediate_evals": True, "best_checkpoint_metric": "pass@1", "checkpoint_eval_patience": 3}
    callback = train._make_callback(CallbackModel(), object(), [], config, None)
    args = SimpleNamespace(output_dir=str(tmp_path))

    for step in range(1, 5):
        checkpoint = Path(args.output_dir) / f"checkpoint-{step}"
        checkpoint.mkdir()
        control = SimpleNamespace(should_training_stop=False)
        callback.on_save(args, SimpleNamespace(global_step=step, epoch=1.0), control)
        assert control.should_training_stop is (step == 4)
