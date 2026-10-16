#!/usr/bin/env bash
# This supervisor attaches to one training run and records a status report every 30 minutes.
# It checks process health every 15 seconds and diagnoses each unexpected exit from recent logs.
# It resumes from the newest complete Trainer checkpoint or restarts from the configured initial adapter.
set -uo pipefail

# Resolve the repository root and read the run-specific settings from the command line.
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG_PATH="${1:?Pass the run configuration path.}"
OUTPUT_DIR="${2:?Pass the run output directory.}"
WANDB_RUN_ID_VALUE="${3:?Pass the W&B run ID.}"
INITIAL_ACCELERATE_PID="${4:-}"
MONITOR_LOG="${MONITOR_LOG:-$OUTPUT_DIR/retry-monitor.log}"

# Load the existing credentials and use the same isolated caches as the training run.
cd "$SCRIPT_DIR"
set -a
source "$SCRIPT_DIR/.env"
set +a
export WANDB_RUN_ID="$WANDB_RUN_ID_VALUE"
export WANDB_RESUME=allow
export HF_HOME="${HF_HOME:-/tmp/post-training-hf-home}"
export HF_HUB_CACHE="${HF_HUB_CACHE:-$HF_HOME/hub}"
# Keep generated Arrow data in writable temporary storage when the shared Hub cache is mounted read-only.
export HF_DATASETS_CACHE="${HF_DATASETS_CACHE:-/tmp/post-training-hf-datasets}"
export HF_HUB_ENABLE_HF_TRANSFER=0
mkdir -p "$OUTPUT_DIR" "$(dirname -- "$MONITOR_LOG")"

# Return the newest checkpoint that has adapter, optimizer, scheduler, RNG, and trainer state files.
latest_complete_checkpoint() {
    local candidate latest=''
    while IFS= read -r candidate; do
        if [[ -s "$candidate/adapter_model.safetensors" && -s "$candidate/optimizer.pt" && -s "$candidate/scheduler.pt" && -s "$candidate/rng_state.pth" && -s "$candidate/trainer_state.json" ]]; then
            latest="$candidate"
        fi
    done < <(find "$OUTPUT_DIR" -mindepth 1 -maxdepth 1 -type d -name 'checkpoint-*' -print | sort -V)
    printf '%s\n' "$latest"
}

# Classify common failure signatures and preserve recent training output for diagnosis.
diagnose_failure() {
    local exit_status="$1"
    {
        printf '%s Training process exited with status %s.\n' "$(date -u '+%Y-%m-%d %H:%M:%S UTC')" "$exit_status"
        if rg -qi 'CUDA out of memory|OutOfMemoryError' "$OUTPUT_DIR/run.log"; then
            printf '%s\n' 'Likely failure class: GPU memory exhaustion.'
        elif rg -qi 'CUBLAS_STATUS|illegal memory access|device-side assert|CUDA error' "$OUTPUT_DIR/run.log"; then
            printf '%s\n' 'Likely failure class: CUDA or GPU kernel error.'
        elif rg -qi 'ConnectionError|ReadTimeout|Temporary failure in name resolution|HTTPError' "$OUTPUT_DIR/run.log"; then
            printf '%s\n' 'Likely failure class: network or service connection error.'
        elif rg -qi 'wandb.*(failed|error)|CommunicationError|failed to upload' "$OUTPUT_DIR/run.log"; then
            printf '%s\n' 'Likely failure class: W&B logging or upload error.'
        elif rg -qi 'Traceback|Error:|Exception:' "$OUTPUT_DIR/run.log"; then
            printf '%s\n' 'Likely failure class: Python exception; inspect the traceback below.'
        else
            printf '%s\n' 'Failure class is not identified by known signatures; inspect recent logs below.'
        fi
        printf '%s\n' 'Recent training log output:'
        tail -n 120 "$OUTPUT_DIR/run.log" 2>/dev/null || true
        printf '%s\n' 'Recent monitor output:'
        tail -n 80 "$MONITOR_LOG" 2>/dev/null || true
        nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader 2>&1 || true
        printf '\n'
    } >> "$MONITOR_LOG" 2>&1
}

# Append the current process, training step, latest checkpoint, and GPU state to the monitor log.
log_status() {
    local active_pid="$1"
    local latest_checkpoint
    {
        date -u '+%Y-%m-%d %H:%M:%S UTC'
        if [[ -n "$active_pid" ]] && kill -0 "$active_pid" 2>/dev/null; then
            ps -p "$active_pid" -o pid=,etime=,stat=,cmd=
        else
            printf '%s\n' 'No active training process is running.'
        fi
        rg 'Training Step [0-9]+/50000' "$OUTPUT_DIR/run.log" | tail -1 || true
        latest_checkpoint="$(latest_complete_checkpoint)"
        if [[ -n "$latest_checkpoint" ]]; then
            printf 'Latest complete checkpoint: %s\n' "$latest_checkpoint"
        else
            printf '%s\n' 'No complete optimizer checkpoint exists yet; the configured initial adapter is available for restart.'
        fi
        nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader 2>&1 || true
        printf '\n'
    } >> "$MONITOR_LOG" 2>&1
}

# Keep polling the active run and restart every unexpected failure without deleting run artifacts.
active_pid="$INITIAL_ACCELERATE_PID"
initial_pid_is_external=1
next_report_at=0
while true; do
    now_seconds="$(date +%s)"
    if (( now_seconds >= next_report_at )); then
        log_status "$active_pid"
        next_report_at=$((now_seconds + 1800))
    fi
    if [[ -n "$active_pid" ]] && kill -0 "$active_pid" 2>/dev/null; then
        sleep 15
        continue
    fi

    # Reap a supervised child and record its exit code before considering a restart.
    if [[ -n "$active_pid" ]] && (( initial_pid_is_external == 0 )); then
        wait "$active_pid"
        exit_status=$?
    else
        exit_status='unknown because the initial process was started externally'
    fi
    active_pid=''
    initial_pid_is_external=0

    # Stop monitoring only when the configured final model artifact proves that training completed.
    if [[ -f "$OUTPUT_DIR/final/adapter_model.safetensors" || -f "$OUTPUT_DIR/final/model.safetensors" ]]; then
        printf '%s Training completed successfully; supervisor stopped.\n' "$(date -u '+%Y-%m-%d %H:%M:%S UTC')" >> "$MONITOR_LOG"
        exit 0
    fi

    # Diagnose the exit and select the newest complete checkpoint for exact recovery.
    diagnose_failure "$exit_status"
    resume_path="$(latest_complete_checkpoint)"
    if [[ -n "$resume_path" ]]; then
        printf '%s Restarting W&B run %s from newest complete checkpoint %s.\n' "$(date -u '+%Y-%m-%d %H:%M:%S UTC')" "$WANDB_RUN_ID_VALUE" "$resume_path" >> "$MONITOR_LOG"
        accelerate launch --num_processes 1 train.py --config "$CONFIG_PATH" --resume-from-checkpoint "$resume_path" >> "$MONITOR_LOG" 2>&1 &
    else
        printf '%s Restarting W&B run %s from the configured initial adapter with fresh optimizer state because no complete checkpoint exists.\n' "$(date -u '+%Y-%m-%d %H:%M:%S UTC')" "$WANDB_RUN_ID_VALUE" >> "$MONITOR_LOG"
        accelerate launch --num_processes 1 train.py --config "$CONFIG_PATH" >> "$MONITOR_LOG" 2>&1 &
    fi
    active_pid="$!"
done
