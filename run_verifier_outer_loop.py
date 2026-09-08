"""Run autonomous CodeBERT verifier fine-tuning cycles with metric-based restarts.

The flow launches the verifier trainer on the saved balanced candidate data, parses
each quarter-epoch evaluation, stops a run after two non-improving validation-AUC
evaluations, records the observed metrics and diagnosis, changes one targeted
optimization setting, and repeats until validation AUC is near one or ten outer
cycles have completed.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parent
LOG_DIR = ROOT / "outputs" / "verifier-outer-loop"
MAX_CYCLES = 10


def command_for_cycle(cycle: int, output_dir: Path, run_name: str) -> list[str]:
    """Build one fine-tuning command with a targeted schedule per outer cycle."""
    # Increase adaptation strength first, then vary regularization and sequence length if needed.
    learning_rates = [1e-5, 2e-5, 5e-5, 1e-5, 2e-5, 5e-6, 1e-5, 2e-5, 5e-5, 1e-5]
    weight_decays = [0.01, 0.01, 0.01, 0.0, 0.0, 0.01, 0.001, 0.001, 0.0, 0.01]
    max_lengths = [512, 512, 512, 512, 256, 512, 512, 256, 512, 512]
    return [
        "python",
        "train_verifier.py",
        "--train-data",
        "outputs/verifier-training/synthetic-clean-original-generated.jsonl",
        "--validation-data",
        "outputs/qwen-evalplus-full-10-temp02/verifier/base.jsonl",
        "--ranking-eval-data",
        "outputs/qwen-evalplus-full-10-temp02/verifier/base.jsonl",
        "--ranking-eval-plus-data",
        "outputs/qwen-evalplus-full-10-temp02/verifier/mbpp_plus.jsonl",
        "--output-dir",
        str(output_dir),
        "--balance-train-classes",
        "--unfreeze-encoder",
        "--epochs",
        "10",
        "--batch-size",
        "16",
        "--positive-class-weight",
        "1.0",
        "--learning-rate",
        str(learning_rates[cycle - 1]),
        "--weight-decay",
        str(weight_decays[cycle - 1]),
        "--max-length",
        str(max_lengths[cycle - 1]),
        "--wandb-run-name",
        run_name,
    ]


def diagnose(metrics: list[dict[str, float]]) -> str:
    """Describe the strongest evidence from a stalled run."""
    # Distinguish representation failure from optimization or generalization failure.
    if not metrics:
        return "No evaluation snapshot was emitted, so the run likely failed before evaluation."
    first = metrics[0]
    last = metrics[-1]
    train_auc = last.get("train/auc", 0.0)
    validation_auc = last.get("validation/auc", last.get("eval/auc", 0.0))
    if train_auc < 0.65 and validation_auc < 0.65:
        return "Both train and validation AUC remain near random, indicating insufficient optimization or weak representation adaptation."
    if train_auc >= 0.8 and validation_auc < 0.65:
        return "Training AUC is high while validation AUC remains low, indicating overfitting or train and validation distribution mismatch."
    if last.get("eval/auc", 0.0) <= first.get("eval/auc", 0.0):
        return "Validation AUC is flat or declining despite training, indicating an optimization or regularization mismatch."
    return "The run plateaued without reaching the target, so the next scheduled optimization setting will test a different adaptation strength."


def finish_wandb_run(run_id: str | None, return_code: int) -> None:
    """Mark a terminated W&B run finished before the next cycle starts."""
    # Use the public API because SIGTERM can bypass the trainer's normal wandb.finish call.
    if not run_id:
        return
    import wandb

    try:
        wandb.Api().run(f"kunal-personal/mbpp-verifier/{run_id}").update_state("finished" if return_code == 0 else "crashed")
    except Exception as error:
        print(f"Could not finalize W&B run {run_id}: {error}", flush=True)


def run_cycle(cycle: int) -> tuple[str, list[dict[str, float]], int]:
    """Run one trainer process and stop it after two consecutive AUC plateaus."""
    # Create an isolated log and output directory so every outer cycle is auditable.
    output_dir = LOG_DIR / f"cycle-{cycle:02d}"
    output_dir.mkdir(parents=True, exist_ok=True)
    log_path = output_dir / "training.log"
    command = command_for_cycle(cycle, output_dir, f"verifier-outer-cycle-{cycle:02d}")
    metrics: list[dict[str, float]] = []
    run_id: str | None = None
    best_auc = float("-inf")
    stale_evaluations = 0
    with log_path.open("w", encoding="utf-8") as log:
        log.write(json.dumps({"cycle": cycle, "command": command}) + "\n")
        log.flush()
        process = subprocess.Popen(command, cwd=ROOT, env={**os.environ, "WANDB_MODE": "online", "PYTHONUNBUFFERED": "1"}, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        assert process.stdout is not None
        for line in process.stdout:
            print(f"[cycle {cycle:02d}] {line}", end="", flush=True)
            log.write(line)
            log.flush()
            run_match = re.search(r"/runs/([A-Za-z0-9]+)", line)
            if run_match:
                run_id = run_match.group(1)
            try:
                snapshot = json.loads(line)
            except json.JSONDecodeError:
                continue
            if "eval/auc" not in snapshot:
                continue
            metrics.append({key: float(value) for key, value in snapshot.items() if isinstance(value, (int, float))})
            validation_auc = float(snapshot["eval/auc"])
            if validation_auc > best_auc + 1e-4:
                best_auc = validation_auc
                stale_evaluations = 0
            else:
                stale_evaluations += 1
            if validation_auc >= 0.99:
                process.terminate()
                break
            if stale_evaluations >= 2:
                process.terminate()
                break
        process.wait(timeout=120)
        return_code = process.returncode
    finish_wandb_run(run_id, return_code)
    (output_dir / "diagnosis.json").write_text(json.dumps({"cycle": cycle, "metrics": metrics, "diagnosis": diagnose(metrics), "return_code": return_code}, indent=2) + "\n", encoding="utf-8")
    return diagnose(metrics), metrics, return_code


def main() -> None:
    """Run up to ten autonomous diagnosis and fine-tuning cycles."""
    # Keep a durable outer-loop summary so progress survives terminal disconnects.
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    summary_path = LOG_DIR / "summary.jsonl"
    completed_cycles = []
    if summary_path.exists():
        # Resume after the last fully recorded cycle instead of duplicating completed work.
        completed_cycles = [json.loads(line) for line in summary_path.open(encoding="utf-8") if line.strip()]
    start_cycle = max((int(record["cycle"]) for record in completed_cycles), default=0) + 1
    for cycle in range(start_cycle, MAX_CYCLES + 1):
        diagnosis, metrics, return_code = run_cycle(cycle)
        final_auc = metrics[-1].get("eval/auc", 0.0) if metrics else 0.0
        record = {"cycle": cycle, "final_eval_auc": final_auc, "diagnosis": diagnosis, "return_code": return_code}
        with summary_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record) + "\n")
        if final_auc >= 0.99:
            print(json.dumps({"status": "target_reached", **record}), flush=True)
            return
    print(json.dumps({"status": "maximum_outer_cycles_reached"}), flush=True)


if __name__ == "__main__":
    main()
