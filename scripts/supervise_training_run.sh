#!/usr/bin/env bash
# This script watches one training run, records status every 30 minutes, and restarts an unexpectedly exited process from the best evaluated saved checkpoint.
set -uo pipefail

# Resolve the repository root and read the run-specific settings from the command line.
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG_PATH="${1:?Pass the run configuration path.}"
OUTPUT_DIR="${2:?Pass the run output directory.}"
WANDB_RUN_ID_VALUE="${3:?Pass the W&B run ID.}"
INITIAL_ACCELERATE_PID="${4:-}"
MONITOR_LOG="${MONITOR_LOG:-/tmp/post-training-progress-monitor.log}"

# Load the run's existing credentials and isolated cache settings before any restart.
cd "$SCRIPT_DIR"
set -a
source "$SCRIPT_DIR/.env"
set +a
export WANDB_RUN_ID="$WANDB_RUN_ID_VALUE"
export WANDB_RESUME=allow
export HF_HOME="${HF_HOME:-/tmp/post-training-resume-hf}"
export HF_DATASETS_CACHE="${HF_DATASETS_CACHE:-$HF_HOME/datasets}"
export HUGGINGFACE_HUB_CACHE="${HUGGINGFACE_HUB_CACHE:-$HF_HOME/hub}"
export HF_HUB_ENABLE_HF_TRANSFER=0

# Return the highest-scoring completed MBPP+ evaluation that has a complete trainer checkpoint.
select_best_checkpoint() {
    python - "$OUTPUT_DIR" <<'PY'
import pathlib
import sys

root = pathlib.Path(sys.argv[1])
scored = []
for result_file in (root / "evalplus").glob("step-*/mbpp_results.txt"):
    lines = result_file.read_text().splitlines()
    marker = next((index for index, line in enumerate(lines) if line.startswith("mbpp+ (base + extra tests)")), None)
    if marker is None or marker + 1 >= len(lines):
        continue
    step = int(result_file.parent.name.removeprefix("step-"))
    checkpoint = root / f"checkpoint-{step}"
    if not (checkpoint / "optimizer.pt").is_file() or not (checkpoint / "adapter_model.safetensors").is_file():
        continue
    score = float(lines[marker + 1].split(":", 1)[1].strip())
    scored.append((score, step))
if scored:
    score, step = max(scored)
    print(f"{step}\t{score:.3f}")
PY
}

# Append a compact process, progress, best-checkpoint, and GPU snapshot to the monitor log.
log_status() {
    local active_pid="$1"
    local best_row
    {
        date -u '+%Y-%m-%d %H:%M:%S UTC'
        if [[ -n "$active_pid" ]] && kill -0 "$active_pid" 2>/dev/null; then
            ps -p "$active_pid" -o pid=,etime=,stat=,cmd=
        else
            printf '%s\n' 'No active training process is running.'
        fi
        rg 'Training Step [0-9]+/50000' "$OUTPUT_DIR/run.log" | tail -1 || true
        best_row="$(select_best_checkpoint)"
        if [[ -n "$best_row" ]]; then
            local best_step best_score
            IFS=$'\t' read -r best_step best_score <<< "$best_row"
            printf 'Best completed MBPP+ pass@1: %s at step %s; checkpoint: %s/checkpoint-%s\n' "$best_score" "$best_step" "$OUTPUT_DIR" "$best_step"
        else
            printf '%s\n' 'No completed MBPP+ evaluation with a saved checkpoint is available yet.'
        fi
        find "$OUTPUT_DIR" -maxdepth 1 -type d -name 'checkpoint-*' -printf '%f\n' | sort -V | tail -1 | sed 's/^/Latest saved checkpoint: /'
        nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader
        printf '\n'
    } >> "$MONITOR_LOG" 2>&1
}

# Keep a live supervisor loop that checks health frequently and writes periodic progress snapshots.
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

    # Reap a supervised child and record its exit status before considering a restart.
    if [[ -n "$active_pid" ]] && (( initial_pid_is_external == 0 )); then
        wait "$active_pid"
        exit_status=$?
    else
        exit_status='external process exited'
    fi
    active_pid=''
    initial_pid_is_external=0

    # Stop the loop after a completed run has written its final model artifact.
    if [[ -f "$OUTPUT_DIR/config.json" ]] && { [[ -f "$OUTPUT_DIR/final/adapter_model.safetensors" ]] || [[ -f "$OUTPUT_DIR/final/model.safetensors" ]]; }; then
        printf '%s Run completed successfully; supervisor stopped.\n' "$(date -u '+%Y-%m-%d %H:%M:%S UTC')" >> "$MONITOR_LOG"
        exit 0
    fi

    # Choose the best checkpoint with a completed MBPP+ score before resuming.
    best_row="$(select_best_checkpoint)"
    if [[ -n "$best_row" ]]; then
        IFS=$'\t' read -r best_step best_score <<< "$best_row"
        resume_path="$OUTPUT_DIR/checkpoint-$best_step"
        printf '%s Training process exited (%s); restarting from best checkpoint %s with MBPP+ pass@1 %s.\n' "$(date -u '+%Y-%m-%d %H:%M:%S UTC')" "$exit_status" "$best_step" "$best_score" >> "$MONITOR_LOG"
        sleep 15
        accelerate launch train.py --config "$CONFIG_PATH" --resume-from-checkpoint "$resume_path" >> "$MONITOR_LOG" 2>&1 &
    else
        printf '%s Training process exited (%s); no scored checkpoint is available, restarting from the configured base model.\n' "$(date -u '+%Y-%m-%d %H:%M:%S UTC')" "$exit_status" >> "$MONITOR_LOG"
        sleep 15
        accelerate launch train.py --config "$CONFIG_PATH" >> "$MONITOR_LOG" 2>&1 &
    fi
    active_pid="$!"
done
