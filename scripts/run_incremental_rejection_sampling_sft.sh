#!/usr/bin/env bash
# This runner performs the eight-task plateau pilot, collects full-data passing solutions, and supervises isolated SFT checkpoints until one million optimizer steps.
set -u

# Resolve the repository and experiment paths before starting any phase.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
CONFIG="${CONFIG:-configs/rejection-sampling-sft-incremental.yaml}"
OUTPUT="${OUTPUT:-outputs/rejection-sampling-sft-incremental-20261011}"
MONITOR_LOG="$OUTPUT/training-monitor.log"
TARGET_STEPS="${TARGET_STEPS:-1000000}"
CHECK_INTERVAL_SECONDS="${CHECK_INTERVAL_SECONDS:-600}"

# Create only this rejection-sampling output directory.
mkdir -p "$OUTPUT"

# Return the latest complete checkpoint from this experiment's isolated SFT directory.
latest_complete_checkpoint() {
    python - "$OUTPUT/full-training/checkpoints" <<'PY'
import json
import re
import sys
from pathlib import Path

root = Path(sys.argv[1])
checkpoints = []
for path in root.glob("checkpoint-*") if root.exists() else []:
    match = re.fullmatch(r"checkpoint-(\d+)", path.name)
    state_path = path / "trainer_state.json"
    if not match or not state_path.is_file():
        continue
    try:
        step = int(json.loads(state_path.read_text())["global_step"])
    except (OSError, ValueError, KeyError, TypeError):
        continue
    has_adapter = any((path / name).is_file() for name in ("adapter_model.safetensors", "adapter_model.bin", "model.safetensors", "pytorch_model.bin"))
    has_optimizer = (path / "optimizer.pt").is_file() and (path / "scheduler.pt").is_file()
    if step == int(match.group(1)) and has_adapter and has_optimizer:
        checkpoints.append((step, path))
if checkpoints:
    print(max(checkpoints)[1])
PY
}

# Read the global step from a checkpoint that passed the completeness check.
checkpoint_step() {
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

# Save a compact diagnosis and the final error lines from a failed attempt.
diagnose_attempt() {
    local log_path="$1"
    local attempt="$2"
    python - "$log_path" "$OUTPUT/attempt-${attempt}-diagnosis.txt" <<'PY'
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
    "Storage exhaustion": r"no space left|disk quota|enospc",
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

# Retry pilot and full-data collection failures while preserving the append-only solution map.
run_collection_phase() {
    local phase="$1"
    local log_path="$2"
    local attempt=0
    while true; do
        attempt=$((attempt + 1))
        printf '[%s] Starting %s attempt %s.\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$phase" "$attempt" | tee -a "$MONITOR_LOG"
        HF_HUB_OFFLINE=1 python experiments/incremental_rejection_sampling_sft.py --config "$CONFIG" --phase "$phase" >>"$log_path" 2>&1
        local status=$?
        if [[ "$status" -eq 0 ]]; then
            return 0
        fi
        local diagnosis
        diagnosis="$(diagnose_attempt "$log_path" "$phase-$attempt")"
        printf '[%s] %s attempt %s exited %s. Diagnosis: %s. Retrying with persisted state.\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$phase" "$attempt" "$status" "$diagnosis" | tee -a "$MONITOR_LOG"
        sleep 15
    done
}

# Skip the already completed pilot when the user explicitly starts full-data work.
if [[ "${SKIP_PILOT:-0}" != "1" ]]; then
    run_collection_phase pilot "$OUTPUT/pilot.log"
fi
# Collect passing solutions for the full task pool before starting resumable SFT.
run_collection_phase full-collect "$OUTPUT/full-collection.log"

# Monitor the full-data Trainer at ten-minute intervals and resume from its newest complete checkpoint.
attempt=0
while true; do
    attempt=$((attempt + 1))
    checkpoint="$(latest_complete_checkpoint)"
    step="$(checkpoint_step "$checkpoint")"
    attempt_log="$OUTPUT/full-training/attempt-${attempt}.log"
    mkdir -p "$OUTPUT/full-training"
    command=(python experiments/incremental_rejection_sampling_sft.py --config "$CONFIG" --phase full-train)
    if [[ -n "$checkpoint" ]]; then
        command+=(--resume-from-checkpoint "$checkpoint")
    fi
    printf '[%s] Starting full SFT attempt %s from step %s.\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$attempt" "$step" | tee -a "$MONITOR_LOG"
    HF_HUB_OFFLINE=1 "${command[@]}" >>"$attempt_log" 2>&1 &
    training_pid=$!
    while true; do
        sleep "$CHECK_INTERVAL_SECONDS"
        process_state="$(ps -o stat= -p "$training_pid" 2>/dev/null | awk '{print $1}')"
        if [[ -z "$process_state" || "$process_state" == Z* ]]; then
            break
        fi
        checkpoint="$(latest_complete_checkpoint)"
        step="$(checkpoint_step "$checkpoint")"
        printf '[%s] Monitor check: SFT is alive at PID %s; latest complete step %s.\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$training_pid" "$step" | tee -a "$MONITOR_LOG"
    done
    wait "$training_pid"
    status=$?
    checkpoint="$(latest_complete_checkpoint)"
    step="$(checkpoint_step "$checkpoint")"
    if [[ "$status" -eq 0 && "$step" -ge "$TARGET_STEPS" && -s "$OUTPUT/full-training/training-complete.json" ]]; then
        printf '[%s] SUCCESS: reached step %s and saved the completion record.\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$step" | tee -a "$MONITOR_LOG"
        exit 0
    fi
    diagnosis="$(diagnose_attempt "$attempt_log" "training-$attempt")"
    printf '[%s] SFT attempt %s exited %s at step %s. Diagnosis: %s. Restarting from %s.\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$attempt" "$status" "$step" "$diagnosis" "${checkpoint:-base model}" | tee -a "$MONITOR_LOG"
    sleep 15
done
