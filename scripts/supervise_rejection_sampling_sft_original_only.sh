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
    local checkpoint_root="${1:-$TRAIN_DIR/checkpoints}"
    python - "$checkpoint_root" <<'PY'
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
    shift 3
    local extra_args=("$@")
    local attempt=0
    while [[ ! -s "$sentinel" ]]; do
        attempt=$((attempt + 1))
        printf '[%s] Starting %s attempt %s.\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$phase" "$attempt" | tee -a "$MONITOR"
        HF_HUB_OFFLINE=1 python -u experiments/incremental_rejection_sampling_sft.py --config "$CONFIG" --phase "$phase" "${extra_args[@]}" >> "$log" 2>&1
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

# Stop after collection when training is explicitly disabled for this supervisor run.
if [[ "${SKIP_TRAINING:-0}" == "1" ]]; then
    printf '[%s] Collection completed; training is disabled by SKIP_TRAINING.\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" | tee -a "$MONITOR"
    exit 0
fi

# Run one complete SFT epoch and one unresolved-task collection cycle at a time when configured.
CYCLE_ENABLED="$(python - "$CONFIG" <<'PY'
import sys, yaml
with open(sys.argv[1], encoding="utf-8") as handle:
    print(int(bool((yaml.safe_load(handle) or {}).get("collection_after_each_epoch", False))))
PY
)"
if [[ "$CYCLE_ENABLED" == "1" ]]; then
    TARGET_EPOCHS="$(python - "$CONFIG" <<'PY'
import sys, yaml
with open(sys.argv[1], encoding="utf-8") as handle:
    print(int((yaml.safe_load(handle) or {}).get("target_epochs", 1)))
PY
)"
    for ((epoch = 1; epoch <= TARGET_EPOCHS; epoch++)); do
        cycle_name="epoch-$(printf '%06d' "$epoch")"
        cycle_dir="$TRAIN_DIR/cycles/$cycle_name"
        train_sentinel="$cycle_dir/training-complete.json"
        mkdir -p "$cycle_dir/checkpoints"
        previous_adapter=""
        if (( epoch > 1 )); then
            previous_adapter="$TRAIN_DIR/cycles/epoch-$(printf '%06d' "$((epoch - 1))")/final-model"
        fi
        attempt=0
        while [[ ! -s "$train_sentinel" ]]; do
            attempt=$((attempt + 1))
            checkpoint="$(latest_checkpoint "$cycle_dir/checkpoints")"
            command=(python -u experiments/incremental_rejection_sampling_sft.py --config "$CONFIG" --phase full-train --cycle-index "$epoch")
            if [[ -d "$previous_adapter" ]]; then command+=(--adapter-path "$previous_adapter"); fi
            if [[ -n "$checkpoint" ]]; then command+=(--resume-from-checkpoint "$checkpoint"); fi
            log="$cycle_dir/attempt-${attempt}.log"
            printf '[%s] Starting SFT epoch %s attempt %s from %s.\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$epoch" "$attempt" "${checkpoint:-${previous_adapter:-base model}}" | tee -a "$MONITOR"
            HF_HUB_OFFLINE=1 "${command[@]}" >> "$log" 2>&1 &
            training_pid=$!
            while kill -0 "$training_pid" 2>/dev/null; do
                sleep "$INTERVAL"
                state="$(ps -o stat= -p "$training_pid" 2>/dev/null | tr -d ' ' || true)"
                if [[ -z "$state" || "$state" == Z* ]]; then break; fi
                checkpoint="$(latest_checkpoint "$cycle_dir/checkpoints")"
                printf '[%s] Monitor check: epoch %s PID %s is running. Latest complete checkpoint: %s.\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$epoch" "$training_pid" "${checkpoint:-none}" | tee -a "$MONITOR"
            done
            wait "$training_pid"
            status=$?
            if [[ -s "$train_sentinel" ]]; then break; fi
            reason="$(diagnose "$log" "SFT epoch $epoch attempt $attempt")"
            checkpoint="$(latest_checkpoint "$cycle_dir/checkpoints")"
            printf '[%s] SFT epoch %s exited %s. %s. Restarting from %s.\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$epoch" "$status" "$reason" "${checkpoint:-previous epoch adapter or base model}" | tee -a "$MONITOR"
            sleep 15
        done
        if [[ "$(python - "$CONFIG" <<'PY'
import sys, yaml
with open(sys.argv[1], encoding="utf-8") as handle:
    print(int((yaml.safe_load(handle) or {}).get("collection_after_each_epoch", False)))
PY
)" == "1" ]]; then
            collection_sentinel="$OUTPUT/full-collection-cycles/$cycle_name/full-collection-summary.json"
            adapter_for_collection=""
            if [[ "$(python - "$CONFIG" <<'PY'
import sys, yaml
with open(sys.argv[1], encoding="utf-8") as handle:
    print((yaml.safe_load(handle) or {}).get("collection_generation_source", "base_model"))
PY
)" == "current_sft_checkpoint" ]]; then
                adapter_for_collection="$cycle_dir/final-model"
            fi
            collection_args=(--collection-cycle-index "$epoch")
            if [[ -d "$adapter_for_collection" ]]; then collection_args+=(--generation-adapter-path "$adapter_for_collection"); fi
            run_phase_until_complete full-collect "$COLLECT_LOG" "$collection_sentinel" "${collection_args[@]}"
        fi
    done
    python - "$TRAIN_DIR/training-complete.json" "$TARGET_EPOCHS" <<'PY'
import json, sys
from pathlib import Path
path = Path(sys.argv[1])
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps({"target_epochs": int(sys.argv[2]), "cycle_mode": True}, indent=2) + "\n")
PY
    printf '[%s] Completed all configured collection and SFT cycles.\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" | tee -a "$MONITOR"
    exit 0
fi

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
