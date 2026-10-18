# This supervisor watches the per-epoch full-pool reference SFT run and hands off to the ten-step evaluation run.
# It reads the stopping epoch from the sampled evaluation records and resumes from the checkpoint of the previous epoch.

from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUN1_CONFIG = "configs/reference-sft-fullpool-perepoch-eval-20261018.yaml"
RUN1_STAGE = ROOT / "outputs/reference-sft-fullpool-perepoch-eval-20261018/full"
RUN1_LOG = ROOT / "logs/sft-fullpool-perepoch-eval-20261018.log"
RUN2_CONFIG = "configs/reference-sft-fullpool-resume-step10-eval-20261018.yaml"
RUN2_LOG = ROOT / "logs/sft-fullpool-resume-step10-eval-20261018.log"
STATUS_PATH = ROOT / "logs/supervise-perepoch-then-step10.json"
MAX_RESTARTS = 5


def write_status(state: str, **extra: object) -> None:
    # Persist the latest supervisor decision for later inspection.
    payload = {"state": state, "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    payload.update(extra)
    STATUS_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def process_alive(pattern: str) -> bool:
    # Report whether any process command line matches the given pattern.
    result = subprocess.run(["pgrep", "-f", pattern], capture_output=True, text=True)
    return result.returncode == 0


def read_records() -> list[dict]:
    # Read every sampled evaluation record written by the per-epoch run.
    path = RUN1_STAGE / "sampled-evaluations.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def checkpoint_root() -> Path:
    # Return the Trainer checkpoint directory of the per-epoch run.
    return RUN1_STAGE / "checkpoints"


def checkpoint_steps() -> list[int]:
    # List every complete checkpoint step in ascending order.
    steps: list[int] = []
    for path in checkpoint_root().glob("checkpoint-*"):
        if not (path / "trainer_state.json").is_file():
            continue
        try:
            steps.append(int(path.name.split("-")[1]))
        except (IndexError, ValueError):
            continue
    return sorted(steps)


def launch(session: str, config: str, log_path: Path, resume: str | None) -> None:
    # Start one training run detached inside a named tmux session.
    command = f"python3 -u experiments/reference_sft.py --config {config}"
    if resume:
        command += f" --resume-from-checkpoint {resume}"
    subprocess.run(["tmux", "kill-session", "-t", session], capture_output=True)
    wrapped = f"PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True {command} > {log_path} 2>&1"
    subprocess.run(["tmux", "new-session", "-d", "-s", session, "-c", str(ROOT), wrapped], check=True)


def main() -> None:
    # Poll the per-epoch run and start the ten-step run from the previous epoch at full coverage.
    restarts = 0
    write_status("watching", run1_config=RUN1_CONFIG)
    while True:
        time.sleep(30)
        if process_alive(RUN1_CONFIG):
            continue
        time.sleep(5)
        if process_alive(RUN1_CONFIG):
            continue
        records = [record for record in read_records() if int(record["optimizer_step"]) > 0]
        if not records:
            restarts += 1
            if restarts > MAX_RESTARTS:
                write_status("blocked", reason="per-epoch run exited without any epoch record", restarts=restarts)
                return
            write_status("restarting_perepoch", restarts=restarts)
            launch("sftper", RUN1_CONFIG, RUN1_LOG, None)
            continue
        last = records[-1]
        coverage = float(last["metrics"].get("coverage", 0.0))
        if coverage < 1.0:
            restarts += 1
            if restarts > MAX_RESTARTS:
                write_status("blocked", reason="per-epoch run exited before full coverage", last_coverage=coverage, restarts=restarts)
                return
            steps = checkpoint_steps()
            resume = str(checkpoint_root() / f"checkpoint-{steps[-1]}") if steps else None
            write_status("restarting_perepoch", restarts=restarts, resume_from_checkpoint=resume, last_coverage=coverage)
            launch("sftper", RUN1_CONFIG, RUN1_LOG, resume)
            continue
        stop_epoch = len(records)
        stop_step = int(last["optimizer_step"])
        previous_epoch = stop_epoch - 1
        previous_step = int(records[-2]["optimizer_step"]) if len(records) >= 2 else 0
        resume = None
        if previous_epoch > 0:
            usable = [step for step in checkpoint_steps() if step <= previous_step]
            if not usable:
                write_status("blocked", reason="no checkpoint at or before the previous epoch", previous_epoch=previous_epoch, previous_step=previous_step, checkpoints=checkpoint_steps())
                return
            resume = str(checkpoint_root() / f"checkpoint-{usable[-1]}")
        write_status(
            "handing_off",
            stop_epoch=stop_epoch,
            stop_step=stop_step,
            stop_coverage=coverage,
            stop_mixed_fraction=last["metrics"].get("mixed_fraction"),
            stop_saturated_fraction=last["metrics"].get("saturated_fraction"),
            previous_epoch=previous_epoch,
            previous_step=previous_step,
            resume_from_checkpoint=resume,
        )
        launch("sftresume", RUN2_CONFIG, RUN2_LOG, resume)
        write_status(
            "handed_off",
            stop_epoch=stop_epoch,
            stop_step=stop_step,
            previous_epoch=previous_epoch,
            resume_from_checkpoint=resume,
            run2_config=RUN2_CONFIG,
        )
        return


if __name__ == "__main__":
    # Run the autonomous per-epoch to ten-step handoff supervisor.
    main()
