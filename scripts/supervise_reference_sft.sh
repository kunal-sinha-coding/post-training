#!/usr/bin/env bash
# This supervisor checks full reference SFT every ten minutes, repairs recognized memory failures, and restarts from the newest intact epoch checkpoint until completion.
set -uo pipefail

# Resolve the repository, source config, and isolated run paths from the command line.
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE_CONFIG="${1:?Pass the SFT YAML config path.}"
OUTPUT_DIR="${2:?Pass the isolated SFT output directory.}"
INITIAL_PID="${3:-}"
CHECK_INTERVAL_SECONDS="${CHECK_INTERVAL_SECONDS:-600}"
RUN_DIR="${OUTPUT_DIR}/full"
CHECKPOINT_DIR="${RUN_DIR}/checkpoints"
RUNTIME_CONFIG="${RUN_DIR}/runtime-config.yaml"
UTILIZATION_FILE="${RUN_DIR}/vllm-gpu-memory-utilization"
RUN_LOG="${RUN_DIR}/supervised-sft.log"
MONITOR_LOG="${RUN_DIR}/monitor.log"
mkdir -p "$RUN_DIR" "$CHECKPOINT_DIR"
cd "$SCRIPT_DIR"
if [[ ! -f "$RUNTIME_CONFIG" ]]; then
    cp "$SOURCE_CONFIG" "$RUNTIME_CONFIG"
fi

# Find the newest complete Trainer checkpoint without changing any checkpoint files.
latest_checkpoint() {
    find "$CHECKPOINT_DIR" -mindepth 1 -maxdepth 1 -type d -name 'checkpoint-*' -printf '%f\n' | sort -V | tail -1
}

# Record process health, latest optimizer progress, GPU use, and checkpoint state.
write_heartbeat() {
    {
        date -u '+%Y-%m-%d %H:%M:%S UTC'
        if [[ -n "${TRAIN_PID:-}" ]]; then
            ps -p "$TRAIN_PID" -o pid=,etime=,stat=,cmd= || true
        fi
        rg 'optimizer_step|Completed epoch|Saving model checkpoint' "$RUN_DIR/training-metrics.jsonl" "$RUN_LOG" 2>/dev/null | tail -3 || true
        printf 'Latest checkpoint: %s\n' "$(latest_checkpoint)"
        nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader 2>/dev/null || true
        printf '\n'
    } >> "$MONITOR_LOG" 2>&1
}

# Keep effective batch size eight while reducing token lengths and then per-device microbatch after a CUDA OOM.
repair_training_oom() {
    python3 - "$RUNTIME_CONFIG" "$MONITOR_LOG" <<'PY'
from pathlib import Path
import sys
import yaml

path = Path(sys.argv[1])
log = Path(sys.argv[2])
config = yaml.safe_load(path.read_text(encoding="utf-8"))
changes = []
for key in ("max_prompt_length", "max_completion_length"):
    current = int(config.get(key, 512))
    if current > 256:
        updated = max(256, (current * 3 // 4 // 8) * 8)
        config[key] = updated
        changes.append(f"{key} {current}->{updated}")
if not changes:
    microbatch = int(config.get("sft_per_device_train_batch_size", 8))
    accumulation = int(config.get("gradient_accumulation_steps", 1))
    effective_batch = microbatch * accumulation
    if microbatch > 1:
        updated = max(1, microbatch // 2)
        config["sft_per_device_train_batch_size"] = updated
        config["gradient_accumulation_steps"] = max(1, effective_batch // updated)
        changes.append(f"per-device batch {microbatch}->{updated}, accumulation {accumulation}->{config['gradient_accumulation_steps']}, effective batch remains {effective_batch}")
if changes:
    path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    with log.open("a", encoding="utf-8") as handle:
        handle.write("Applied CUDA OOM recovery: " + "; ".join(changes) + "\n")
else:
    with log.open("a", encoding="utf-8") as handle:
        handle.write("CUDA OOM persisted at minimum token limits and microbatch one; no safe automatic adjustment remains.\n")
PY
}

# Lower vLLM's reserved GPU fraction when a full evaluation runs out of memory.
repair_vllm_oom() {
    local current="0.90"
    if [[ -f "$UTILIZATION_FILE" ]]; then
        current="$(cat "$UTILIZATION_FILE")"
    fi
    local updated
    updated="$(python3 -c 'print(max(0.50, float(__import__("sys").argv[1]) - 0.10))' "$current")"
    printf '%s\n' "$updated" > "$UTILIZATION_FILE"
    printf 'Applied vLLM evaluation OOM recovery: gpu_memory_utilization %s->%s.\n' "$current" "$updated" >> "$MONITOR_LOG"
}

# Start or resume training and keep checking it at the requested ten-minute interval.
TRAIN_PID="$INITIAL_PID"
external_pid=1
while [[ ! -f "$RUN_DIR/completed.json" ]]; do
    if [[ -z "$TRAIN_PID" ]]; then
        latest="$(latest_checkpoint)"
        resume_args=()
        if [[ -n "$latest" ]]; then
            resume_args=(--resume-from-checkpoint "$CHECKPOINT_DIR/$latest")
            printf '%s Restarting from %s.\n' "$(date -u '+%Y-%m-%d %H:%M:%S UTC')" "$CHECKPOINT_DIR/$latest" >> "$MONITOR_LOG"
        else
            printf '%s Starting from the original base model because no SFT checkpoint exists yet.\n' "$(date -u '+%Y-%m-%d %H:%M:%S UTC')" >> "$MONITOR_LOG"
        fi
        if [[ -f "$UTILIZATION_FILE" ]]; then
            export VLLM_GPU_MEMORY_UTILIZATION="$(cat "$UTILIZATION_FILE")"
        fi
        python3 -u experiments/reference_sft.py --config "$RUNTIME_CONFIG" "${resume_args[@]}" >> "$RUN_LOG" 2>&1 &
        TRAIN_PID="$!"
        external_pid=0
        printf '%s Started training PID %s.\n' "$(date -u '+%Y-%m-%d %H:%M:%S UTC')" "$TRAIN_PID" >> "$MONITOR_LOG"
    fi

    while kill -0 "$TRAIN_PID" 2>/dev/null; do
        sleep "$CHECK_INTERVAL_SECONDS"
        process_state="$(ps -o stat= -p "$TRAIN_PID" 2>/dev/null | tr -d ' ' || true)"
        if [[ -z "$process_state" || "$process_state" == Z* ]]; then
            break
        fi
        write_heartbeat
    done
    if (( external_pid == 0 )); then
        wait "$TRAIN_PID"
        exit_status=$?
    else
        exit_status='attached process exited'
    fi
    TRAIN_PID=''
    external_pid=0
    if [[ -f "$RUN_DIR/completed.json" ]]; then
        printf '%s Training completed successfully.\n' "$(date -u '+%Y-%m-%d %H:%M:%S UTC')" >> "$MONITOR_LOG"
        exit 0
    fi

    # Classify each failure from recent logs and apply a bounded fix before restarting.
    failure_summary="$(tail -160 "$RUN_LOG" | rg -i 'out of memory|cuda error|traceback|error:|exception|killed|no space left|connection|timeout|kv cache' | tail -16 || true)"
    {
        printf '%s Training exited with status %s.\n' "$(date -u '+%Y-%m-%d %H:%M:%S UTC')" "$exit_status"
        printf 'Diagnosis evidence:\n%s\n' "${failure_summary:-No standard error signature found; inspect the complete run log.}"
        printf 'Preserving every checkpoint. Latest resumable checkpoint: %s\n' "$(latest_checkpoint)"
    } >> "$MONITOR_LOG"
    if grep -Eiq 'vllm|kv cache|cache blocks' <<< "$failure_summary" && grep -Eiq 'out of memory|cuda error|memory' <<< "$failure_summary"; then
        repair_vllm_oom
    elif grep -Eiq 'out of memory|cuda error' <<< "$failure_summary"; then
        repair_training_oom
    else
        printf '%s No safe automatic config repair matched this failure; retrying with the same config after recording evidence.\n' "$(date -u '+%Y-%m-%d %H:%M:%S UTC')" >> "$MONITOR_LOG"
    fi
    printf '%s\n\n' 'The supervisor will repeat this check, diagnosis, repair, and restart cycle after every failure.' >> "$MONITOR_LOG"
    sleep 10
 done
