#!/usr/bin/env bash
# This supervisor launches the batch-normalized vLLM GRPO experiment, checks it hourly, and resumes failed runs from the newest complete optimizer checkpoint.
set -uo pipefail

# Resolve the repository and experiment paths from the required arguments.
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG_PATH="${1:?Pass the experiment configuration path.}"
OUTPUT_DIR="${2:?Pass the experiment output directory.}"
MONITOR_LOG="${3:?Pass the monitor log path.}"

# Load credentials and pin every restart to the same new W&B run.
cd "$SCRIPT_DIR"
set -a
source "$SCRIPT_DIR/.env"
set +a
export WANDB_RUN_ID="c712c322d5b740ec"
export WANDB_RESUME=allow
export HF_HOME="/tmp/post-training-grpo-batchnorm-hf"
export HF_HUB_CACHE="$HF_HOME/hub"
export HUGGINGFACE_HUB_CACHE="$HF_HOME/hub"
export HF_DATASETS_CACHE="$HF_HOME/datasets"
export HF_HUB_ENABLE_HF_TRANSFER=0
mkdir -p "$HF_HUB_CACHE" "$HF_DATASETS_CACHE"

# Find the newest complete Trainer checkpoint without changing or removing any checkpoint.
latest_complete_checkpoint() {
    python - "$OUTPUT_DIR" <<'PY'
import pathlib
import re
import sys

root = pathlib.Path(sys.argv[1])
complete = []
required = ("trainer_state.json", "optimizer.pt", "scheduler.pt", "rng_state.pth", "adapter_model.safetensors")
for path in root.glob("checkpoint-*"):
    match = re.fullmatch(r"checkpoint-(\d+)", path.name)
    if match and all((path / name).is_file() for name in required):
        complete.append((int(match.group(1)), path))
if complete:
    print(max(complete)[1])
PY
}

# Record process health, optimizer progress, and GPU use once per hourly check.
log_hourly_status() {
    local pid="$1"
    {
        date -u '+%Y-%m-%d %H:%M:%S UTC'
        ps -p "$pid" -o pid=,etime=,stat=,cmd= || true
        rg 'Training Step [0-9]+/50000|Training evaluation uses|scale_rewards|vLLM' "$OUTPUT_DIR/run.log" | tail -5 || true
        nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader || true
        printf '\n'
    } >> "$MONITOR_LOG" 2>&1
}

# Run until training finishes cleanly or a failed process is restarted from its latest complete checkpoint.
resume_checkpoint=""
while true; do
    launch_args=(accelerate launch --num_processes 1 train.py --config "$CONFIG_PATH")
    if [[ -n "$resume_checkpoint" ]]; then
        launch_args+=(--resume-from-checkpoint "$resume_checkpoint")
    fi
    printf '%s Launching: %s\n' "$(date -u '+%Y-%m-%d %H:%M:%S UTC')" "${launch_args[*]}" >> "$MONITOR_LOG"
    "${launch_args[@]}" >> "$OUTPUT_DIR/run.log" 2>&1 &
    training_pid="$!"
    while true; do
        sleep 3600 &
        timer_pid="$!"
        completed_pid=""
        wait -n -p completed_pid "$training_pid" "$timer_pid"
        child_status="$?"
        if [[ "$completed_pid" == "$timer_pid" ]]; then
            log_hourly_status "$training_pid"
            continue
        fi
        kill "$timer_pid" 2>/dev/null || true
        wait "$timer_pid" 2>/dev/null || true
        exit_status="$child_status"
        break
    done

    # Treat the final saved adapter and run configuration as proof of normal completion.
    if [[ -f "$OUTPUT_DIR/config.json" ]] && [[ -f "$OUTPUT_DIR/final/adapter_model.safetensors" || -f "$OUTPUT_DIR/final/model.safetensors" ]]; then
        printf '%s Training completed successfully; hourly supervisor stopped.\n' "$(date -u '+%Y-%m-%d %H:%M:%S UTC')" >> "$MONITOR_LOG"
        exit 0
    fi

    # Keep a short failure excerpt for diagnosis before selecting a safe restart point.
    {
        printf '%s Training exited with status %s. Recent output follows.\n' "$(date -u '+%Y-%m-%d %H:%M:%S UTC')" "$exit_status"
        tail -100 "$OUTPUT_DIR/run.log"
    } >> "$MONITOR_LOG" 2>&1
    resume_checkpoint="$(latest_complete_checkpoint)"
    if [[ -n "$resume_checkpoint" ]]; then
        printf '%s Restarting from newest complete checkpoint %s. All checkpoint directories are retained.\n' "$(date -u '+%Y-%m-%d %H:%M:%S UTC')" "$resume_checkpoint" >> "$MONITOR_LOG"
    else
        printf '%s No complete checkpoint exists yet; restarting from the configured base model. Existing files are retained.\n' "$(date -u '+%Y-%m-%d %H:%M:%S UTC')" >> "$MONITOR_LOG"
    fi
    sleep 15
done
