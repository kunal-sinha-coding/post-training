#!/usr/bin/env bash
# This supervisor checks a full reference-SFT process every ten minutes, diagnoses each failure, and restarts from the latest intact epoch checkpoint until completion.
set -uo pipefail

# Resolve the repository, config, and isolated run paths from the command line.
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG_PATH="${1:?Pass the SFT YAML config path.}"
OUTPUT_DIR="${2:?Pass the isolated SFT output directory.}"
CHECK_INTERVAL_SECONDS="${CHECK_INTERVAL_SECONDS:-600}"
RUN_DIR="${OUTPUT_DIR}/full"
CHECKPOINT_DIR="${RUN_DIR}/checkpoints"
RUN_LOG="${RUN_DIR}/supervised-sft.log"
MONITOR_LOG="${RUN_DIR}/monitor.log"
mkdir -p "$RUN_DIR" "$CHECKPOINT_DIR"
cd "$SCRIPT_DIR"

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

# Start or resume training and keep checking it at the requested ten-minute interval.
while [[ ! -f "$RUN_DIR/completed.json" ]]; do
    latest="$(latest_checkpoint)"
    resume_args=()
    if [[ -n "$latest" ]]; then
        resume_args=(--resume-from-checkpoint "$CHECKPOINT_DIR/$latest")
        printf '%s Restarting from %s.\n' "$(date -u '+%Y-%m-%d %H:%M:%S UTC')" "$CHECKPOINT_DIR/$latest" >> "$MONITOR_LOG"
    else
        printf '%s Starting from the original base model because no SFT checkpoint exists yet.\n' "$(date -u '+%Y-%m-%d %H:%M:%S UTC')" >> "$MONITOR_LOG"
    fi
    python3 -u experiments/reference_sft.py --config "$CONFIG_PATH" "${resume_args[@]}" >> "$RUN_LOG" 2>&1 &
    TRAIN_PID="$!"
    printf '%s Started training PID %s.\n' "$(date -u '+%Y-%m-%d %H:%M:%S UTC')" "$TRAIN_PID" >> "$MONITOR_LOG"

    while kill -0 "$TRAIN_PID" 2>/dev/null; do
        sleep "$CHECK_INTERVAL_SECONDS"
        process_state="$(ps -o stat= -p "$TRAIN_PID" 2>/dev/null | tr -d ' ' || true)"
        if [[ -z "$process_state" || "$process_state" == Z* ]]; then
            break
        fi
        write_heartbeat
    done
    wait "$TRAIN_PID"
    exit_status=$?
    TRAIN_PID=''
    if [[ -f "$RUN_DIR/completed.json" ]]; then
        printf '%s Training completed successfully.\n' "$(date -u '+%Y-%m-%d %H:%M:%S UTC')" >> "$MONITOR_LOG"
        exit 0
    fi

    # Classify the failure from the latest log tail and preserve the diagnosis before retrying.
    failure_summary="$(tail -120 "$RUN_LOG" | rg -i 'out of memory|cuda error|traceback|error:|exception|killed|no space left|connection|timeout' | tail -12 || true)"
    {
        printf '%s Training exited with status %s.\n' "$(date -u '+%Y-%m-%d %H:%M:%S UTC')" "$exit_status"
        printf 'Diagnosis evidence:\n%s\n' "${failure_summary:-No standard error signature found; inspect the complete run log.}"
        printf 'Preserving every checkpoint. Latest resumable checkpoint: %s\n' "$(latest_checkpoint)"
        printf '%s\n' 'The supervisor will restart and repeat this diagnostic cycle after each failure.'
        printf '\n'
    } >> "$MONITOR_LOG"
    sleep 10
 done
