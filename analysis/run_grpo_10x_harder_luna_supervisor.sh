#!/usr/bin/env bash
# This supervisor runs the matched 50,000-step harder-data GRPO experiment, checks the worker every ten minutes, diagnoses every failed attempt, and resumes from the latest complete checkpoint until training and final EvalPlus evaluation succeed.
set -u

# Resolve the repository root and all durable run paths before starting work.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
CONFIG="configs/grpo-mbpp-fulltrain-8x16-b128-micro2-workers8-0.5b-50000-dual-greedy-evalplus031-visible1-save10-10x-harder-luna-20261009.yaml"
OUTPUT="outputs/grpo-mbpp-fulltrain-8x16-b128-micro2-workers8-0.5b-50000-dual-greedy-evalplus031-visible1-save10-10x-harder-luna-20261009"
SUPERVISOR_LOG="$OUTPUT/supervisor.log"
TARGET_STEPS=50000
CHECK_INTERVAL_SECONDS=600

# Create the output directory before recording the first launch.
mkdir -p "$OUTPUT"

# Return the newest checkpoint with matching step metadata, adapter weights, and optimizer state.
latest_complete_checkpoint() {
    python - "$OUTPUT" <<'PY'
import json
import re
import sys
from pathlib import Path

root = Path(sys.argv[1])
checkpoints = []
for path in root.glob("checkpoint-*"):
    match = re.fullmatch(r"checkpoint-(\d+)", path.name)
    state_path = path / "trainer_state.json"
    if not match or not state_path.is_file():
        continue
    try:
        state = json.loads(state_path.read_text())
        step = int(state["global_step"])
    except (OSError, ValueError, KeyError, TypeError):
        continue
    has_model = any((path / name).is_file() for name in ("adapter_model.safetensors", "adapter_model.bin", "model.safetensors", "pytorch_model.bin"))
    has_optimizer = (path / "optimizer.pt").is_file() and (path / "scheduler.pt").is_file()
    if step == int(match.group(1)) and has_model and has_optimizer:
        checkpoints.append((step, path))
if checkpoints:
    print(max(checkpoints)[1])
PY
}

# Read a checkpoint's saved global step without trusting its directory name.
latest_checkpoint_step() {
    local checkpoint="$1"
    if [[ -z "$checkpoint" ]]; then
        printf '0\n'
        return
    fi
    python - "$checkpoint/trainer_state.json" <<'PY'
import json
import sys
from pathlib import Path
print(int(json.loads(Path(sys.argv[1]).read_text())["global_step"]))
PY
}

# Classify a failed attempt from its final log lines and preserve the evidence for review.
diagnose_attempt() {
    local attempt_log="$1"
    local attempt_number="$2"
    python - "$attempt_log" "$OUTPUT/attempt-${attempt_number}-diagnosis.txt" <<'PY'
import re
import sys
from pathlib import Path

source = Path(sys.argv[1])
target = Path(sys.argv[2])
lines = source.read_text(errors="replace").splitlines() if source.exists() else []
tail = lines[-160:]
text = "\n".join(tail).lower()
patterns = {
    "CUDA or host memory exhaustion": r"out of memory|cuda error: memory|oom-kill|killed process",
    "Storage exhaustion or quota": r"no space left|disk quota|enospc",
    "Dataset or checkpoint loading error": r"arrow|dataset|checkpoint|file not found|no such file|invalid data",
    "Distributed runtime failure": r"nccl|collective|distributed|rank [0-9]+ failed",
    "Non-finite training values": r"nan|not finite|infinite",
}
matches = [label for label, pattern in patterns.items() if re.search(pattern, text)]
diagnosis = ", ".join(matches) if matches else "No known failure signature matched the attempt log."
target.write_text("Diagnosis: " + diagnosis + "\n\nLast attempt log lines:\n" + "\n".join(tail) + "\n")
print(diagnosis)
PY
}

# Retry failed attempts from the newest complete checkpoint without deleting recovery files.
attempt=0
while true; do
    attempt=$((attempt + 1))
    checkpoint="$(latest_complete_checkpoint)"
    current_step="$(latest_checkpoint_step "$checkpoint")"
    attempt_log="$OUTPUT/attempt-${attempt}.log"
    command=(python train.py --config "$CONFIG")
    if [[ -n "$checkpoint" ]]; then
        command+=(--resume-from-checkpoint "$checkpoint")
    fi

    # Save the resume point and start one worker under the durable supervisor.
    printf '[%s] Starting attempt %s from step %s with checkpoint %s.\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$attempt" "$current_step" "${checkpoint:-base model}" | tee -a "$SUPERVISOR_LOG"
    HF_HOME=/tmp/mbpp-qwen05-hf-home HF_HUB_ENABLE_HF_TRANSFER=0 HF_DATASETS_CACHE=/tmp/post-training-hf-datasets "${command[@]}" >>"$attempt_log" 2>&1 &
    training_pid=$!

    # Inspect worker liveness at the requested ten-minute cadence.
    while true; do
        sleep "$CHECK_INTERVAL_SECONDS"
        process_state="$(ps -o stat= -p "$training_pid" 2>/dev/null | awk '{print $1}')"
        if [[ -z "$process_state" || "$process_state" == Z* ]]; then
            break
        fi
        checkpoint="$(latest_complete_checkpoint)"
        current_step="$(latest_checkpoint_step "$checkpoint")"
        printf '[%s] Monitor check: attempt %s is alive at PID %s; latest complete step %s.\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$attempt" "$training_pid" "$current_step" | tee -a "$SUPERVISOR_LOG"
    done

    # Record the exit status and diagnose failures before choosing the next checkpoint.
    wait "$training_pid"
    exit_status=$?
    checkpoint="$(latest_complete_checkpoint)"
    current_step="$(latest_checkpoint_step "$checkpoint")"
    final_eval="$OUTPUT/evalplus-final-metrics.json"
    if [[ "$exit_status" -eq 0 && "$current_step" -ge "$TARGET_STEPS" && -s "$final_eval" ]]; then
        printf '[%s] SUCCESS: training reached step %s and final EvalPlus metrics exist at %s.\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$current_step" "$final_eval" | tee -a "$SUPERVISOR_LOG"
        exit 0
    fi

    # Keep the diagnosis, checkpoint, and attempt log so the recovery decision is auditable.
    diagnosis="$(diagnose_attempt "$attempt_log" "$attempt")"
    printf '[%s] Restarting after exit status %s at step %s. Diagnosis: %s. Checkpoint: %s. Attempt log: %s.\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$exit_status" "$current_step" "$diagnosis" "${checkpoint:-none; next attempt starts from base}" "$attempt_log" | tee -a "$SUPERVISOR_LOG"
    sleep 15
done
