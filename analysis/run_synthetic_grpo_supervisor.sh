#!/usr/bin/env bash
# This supervisor starts synthetic-only GRPO, checks it every ten minutes, and resumes from the latest complete checkpoint until 1,500 steps and final EvalPlus both succeed.
set -u

# Resolve all run paths from the repository root, independent of the caller's directory.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
CONFIG="configs/grpo-mbpp-synthetic-pilot100-qwen05.yaml"
OUTPUT="outputs/grpo-mbpp-synthetic-pilot100-qwen05"
SUPERVISOR_LOG="$OUTPUT/supervisor.log"
TARGET_STEPS=1500
CHECK_INTERVAL_SECONDS=60

# Create the persistent output directory before launching any attempt.
mkdir -p "$OUTPUT"

# Return the latest checkpoint that has model weights, optimizer state, scheduler state, and trainer state.
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
    if not match or not (path / "trainer_state.json").is_file():
        continue
    has_model = any((path / name).is_file() for name in ("adapter_model.safetensors", "adapter_model.bin", "model.safetensors", "pytorch_model.bin"))
    if has_model and (path / "optimizer.pt").is_file() and (path / "scheduler.pt").is_file():
        checkpoints.append((int(match.group(1)), path))
if checkpoints:
    print(max(checkpoints)[1])
PY
}

# Read the global step from the newest complete checkpoint when one exists.
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
print(int(json.loads(Path(sys.argv[1]).read_text())['global_step']))
PY
}

# Keep retrying only after the monitor observes an exited or incomplete attempt.
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

    # Record the timestamp and resume point before starting this training attempt.
    printf '[%s] Starting attempt %s from step %s with checkpoint %s.\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$attempt" "$current_step" "${checkpoint:-base model}" | tee -a "$SUPERVISOR_LOG"
    HF_HOME=/tmp/mbpp-qwen05-hf-home HF_HUB_ENABLE_HF_TRANSFER=0 HF_DATASETS_CACHE=/tmp/post-training-hf-datasets "${command[@]}" >>"$attempt_log" 2>&1 &
    training_pid=$!

    # Check process state at the configured interval and keep the worker active during long runs.
    while true; do
        sleep "$CHECK_INTERVAL_SECONDS"
        process_state="$(ps -o stat= -p "$training_pid" 2>/dev/null | awk '{print $1}')"
        if [[ -z "$process_state" || "$process_state" == Z* ]]; then
            break
        fi
        printf '[%s] Monitor check: attempt %s is running at PID %s.\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$attempt" "$training_pid" | tee -a "$SUPERVISOR_LOG"
    done

    # Capture the worker exit status and current durable checkpoint before deciding whether to resume.
    wait "$training_pid"
    exit_status=$?
    checkpoint="$(latest_complete_checkpoint)"
    current_step="$(latest_checkpoint_step "$checkpoint")"
    final_eval="$OUTPUT/evalplus-final-metrics.json"
    if [[ "$exit_status" -eq 0 && "$current_step" -ge "$TARGET_STEPS" && -s "$final_eval" ]]; then
        printf '[%s] SUCCESS: training reached step %s and final EvalPlus metrics exist at %s.\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$current_step" "$final_eval" | tee -a "$SUPERVISOR_LOG"
        exit 0
    fi

    # Restart incomplete or failed attempts from the latest complete checkpoint and retain the same W&B run ID.
    printf '[%s] Restarting after exit status %s at step %s. Checkpoint: %s. Attempt log: %s.\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$exit_status" "$current_step" "${checkpoint:-none; next attempt starts from base}" "$attempt_log" | tee -a "$SUPERVISOR_LOG"
    sleep 15
done
