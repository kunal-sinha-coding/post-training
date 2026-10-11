#!/usr/bin/env bash
# This supervisor collects original-task solutions once, then monitors and restarts full-data SFT from its newest complete checkpoint.
set -uo pipefail

# Resolve the repository paths and the ten-minute monitoring interval.
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
CONFIG="${CONFIG:-configs/rejection-sampling-sft-original-only-20261011.yaml}"
OUTPUT="${OUTPUT:-outputs/rejection-sampling-sft-original-only-20261011}"
INTERVAL="${CHECK_INTERVAL_SECONDS:-600}"
mkdir -p "$OUTPUT/full-training/checkpoints"
MONITOR="$OUTPUT/monitor.log"
COLLECT_LOG="$OUTPUT/full-collection.log"
TRAIN_DIR="$OUTPUT/full-training"

# Find the newest checkpoint with saved model, optimizer, and Trainer state.
latest_checkpoint() {
    python - "$TRAIN_DIR/checkpoints" <<'PY'
import json
import re
import sys
from pathlib import Path
root = Path(sys.argv[1])
valid = []
for path in root.glob("checkpoint-*") if root.exists() else []:
    match = re.fullmatch(r"checkpoint-(\d+)", path.name)
    state = path / "trainer_state.json"
    if not match or not state.is_file():
        continue
    try:
        step = int(json.loads(state.read_text())["global_step"])
    except (OSError, ValueError, KeyError, TypeError):
        continue
    adapter = any((path / name).is_file() for name in ("adapter_model.safetensors", "adapter_model.bin"))
    if step == int(match.group(1)) and adapter and (path / "optimizer.pt").is_file() and (path / "scheduler.pt").is_file():
        valid.append((step, path))
if valid:
    print(max(valid)[1])
PY
}

# Record a short failure diagnosis without deleting run artifacts.
diagnose() {
    local log="$1"
    local phase="$2"
    python - "$log" "$MONITOR" "$phase" <<'PY'
import re
import sys
from pathlib import Path
lines = Path(sys.argv[1]).read_text(errors="replace").splitlines()[-100:]
text = "\n".join(lines).lower()
signatures = {"GPU or host memory exhaustion": r"out of memory|cuda error|oom-kill", "storage exhaustion": r"no space left|enospc|disk quota", "checkpoint or dataset load failure": r"checkpoint|dataset|file not found|no such file", "W&B communication failure": r"wandb.*(error|exception)|network.*(error|unreachable)"}
found = [name for name, pattern in signatures.items() if re.search(pattern, text)]
with Path(sys.argv[2]).open("a") as output:
    output.write(f"{sys.argv[3]} diagnosis: {', '.join(found) if found else 'unclassified failure'}\n")
    output.write("\n".join(lines) + "\n")
print(", ".join(found) if found else "unclassified failure")
PY
}

# Run one phase until it completes, restarting it with persisted cache and state after failures.
run_phase_until_complete() {
    local phase="$1"
    local log="$2"
    local sentinel="$3"
    local attempt=0
    while [[ ! -s "$sentinel" ]]; do
        attempt=$((attempt + 1))
        printf '[%s] Starting %s attempt %s.\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$phase" "$attempt" | tee -a "$MONITOR"
        HF_HUB_OFFLINE=1 python -u experiments/incremental_rejection_sampling_sft.py --config "$CONFIG" --phase "$phase" >> "$log" 2>&1
        status=$?
        if [[ "$status" -eq 0 && -s "$sentinel" ]]; then
            return 0
        fi
        reason="$(diagnose "$log" "$phase attempt $attempt")"
        printf '[%s] %s exited %s. %s. Retrying with saved state.\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$phase" "$status" "$reason" | tee -a "$MONITOR"
        sleep 15
    done
}

# Finish the one-time collection before starting training.
run_phase_until_complete full-collect "$COLLECT_LOG" "$OUTPUT/full-collection-summary.json"

# Restart training indefinitely from the newest complete checkpoint until the epoch cap is reached.
attempt=0
while [[ ! -s "$TRAIN_DIR/training-complete.json" ]]; do
    attempt=$((attempt + 1))
    checkpoint="$(latest_checkpoint)"
    command=(python -u experiments/incremental_rejection_sampling_sft.py --config "$CONFIG" --phase full-train)
    if [[ -n "$checkpoint" ]]; then command+=(--resume-from-checkpoint "$checkpoint"); fi
    log="$TRAIN_DIR/attempt-${attempt}.log"
    printf '[%s] Starting SFT attempt %s from %s.\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$attempt" "${checkpoint:-base model}" | tee -a "$MONITOR"
    HF_HUB_OFFLINE=1 "${command[@]}" >> "$log" 2>&1 &
    training_pid=$!
    while kill -0 "$training_pid" 2>/dev/null; do
        sleep "$INTERVAL"
        state="$(ps -o stat= -p "$training_pid" 2>/dev/null | tr -d ' ' || true)"
        if [[ -z "$state" || "$state" == Z* ]]; then break; fi
        checkpoint="$(latest_checkpoint)"
        printf '[%s] Monitor check: PID %s is running. Latest complete checkpoint: %s.\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$training_pid" "${checkpoint:-none}" | tee -a "$MONITOR"
    done
    wait "$training_pid"
    status=$?
    if [[ -s "$TRAIN_DIR/training-complete.json" ]]; then
        printf '[%s] Training reached its configured epoch cap.\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" | tee -a "$MONITOR"
        exit 0
    fi
    reason="$(diagnose "$log" "training attempt $attempt")"
    checkpoint="$(latest_checkpoint)"
    printf '[%s] SFT exited %s at %s. %s. Restarting from %s.\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$status" "${checkpoint:-no checkpoint}" "$reason" "${checkpoint:-base model}" | tee -a "$MONITOR"
    sleep 15
done
