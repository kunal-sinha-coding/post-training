#!/usr/bin/env bash
# This supervisor loads local credentials, stages Python code on local storage, and runs the configured OpenCode and MBPP SFT experiment.
# It records progress every 30 minutes and resumes unexpected failures from the newest complete checkpoint without deleting artifacts or changing experiment settings.
set -uo pipefail

# Resolve the repository and immutable experiment settings.
REPO_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG_PATH="${1:?Pass the SFT configuration path.}"
OUTPUT_DIR="${2:?Pass the experiment output directory.}"
INITIAL_RESUME_CHECKPOINT="${3:-}"
cd "$REPO_DIR"
mkdir -p "$OUTPUT_DIR" "$OUTPUT_DIR/tmp"
if [[ -n "$INITIAL_RESUME_CHECKPOINT" ]]; then
    # Preserve the approved initial checkpoint for monitor-triggered supervisor restarts.
    printf '%s\n' "$INITIAL_RESUME_CHECKPOINT" > "$OUTPUT_DIR/initial-resume-checkpoint.txt"
fi

# Load existing credentials without changing or publishing the local environment file.
set -a
source "$REPO_DIR/.env"
set +a
export HF_HOME="$REPO_DIR/$OUTPUT_DIR/hf-cache"
export HF_HUB_CACHE="$HF_HOME/hub"
export HUGGINGFACE_HUB_CACHE="$HF_HUB_CACHE"
export HF_DATASETS_CACHE="/tmp/router-datasets-cache"
export HF_HUB_ENABLE_HF_TRANSFER=0
export HF_HUB_OFFLINE=0
export HF_DATASETS_OFFLINE=0
export TMPDIR="$REPO_DIR/$OUTPUT_DIR/tmp"
export HF_HUB_DOWNLOAD_TIMEOUT=120
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
export TOKENIZERS_PARALLELISM=false
export PYTHONPYCACHEPREFIX=/tmp/sft-python-bytecode-cache
mkdir -p "$HF_HUB_CACHE" "$TMPDIR"

latest_checkpoint() {
    # Select only a checkpoint with all required adapter and optimizer recovery files.
    python - "$OUTPUT_DIR/checkpoints" "$OUTPUT_DIR/initial-resume-checkpoint.txt" <<'PY'
from pathlib import Path
import sys
# Inspect saved Trainer states without changing any training artifact.
required = ('adapter_model.safetensors', 'trainer_state.json', 'optimizer.pt', 'scheduler.pt', 'rng_state.pth')
paths = [p for p in Path(sys.argv[1]).glob('checkpoint-*') if p.name.split('-')[-1].isdigit() and all((p / name).is_file() for name in required)]
if paths:
    print(max(paths, key=lambda p: int(p.name.split('-')[-1])))
else:
    initial = Path(sys.argv[2]).read_text().strip() if Path(sys.argv[2]).is_file() else ''
    if initial and all((Path(initial) / name).is_file() for name in required):
        print(initial)
PY
}

# Retry unexpected exits while retaining one W&B identity and the one-epoch Trainer stop condition.
while [[ ! -f "$OUTPUT_DIR/completed.json" ]]; do
    resume="$(latest_checkpoint)"
    # Mirror committed Python source locally so imports do not wait on workspace directory reads.
    runtime_dir="/tmp/sft-runtime-$$"
    mkdir -p "$runtime_dir"
    if ! git -c safe.directory="$REPO_DIR" archive HEAD -- '*.py' | tar -x -C "$runtime_dir"; then
        printf '%s Local code staging failed; retrying.\n' "$(date -u '+%Y-%m-%d %H:%M:%S UTC')" >> "$OUTPUT_DIR/retry-monitor.log"
        sleep 15
        continue
    fi
    launch=(python -u "$runtime_dir/experiments/sft_mbpp_opencode.py" --config "$CONFIG_PATH")
    if [[ -n "$resume" ]]; then
        launch+=(--resume-from-checkpoint "$resume")
    fi
    printf '%s Launching %s\n' "$(date -u '+%Y-%m-%d %H:%M:%S UTC')" "${launch[*]}" >> "$OUTPUT_DIR/retry-monitor.log"
    "${launch[@]}" >> "$OUTPUT_DIR/run.log" 2>&1 &
    training_pid="$!"
    next_report=$(( $(date +%s) + 1800 ))

    # Observe process health frequently and write a bounded status report every 30 minutes.
    while kill -0 "$training_pid" 2>/dev/null; do
        state="$(ps -o stat= -p "$training_pid" 2>/dev/null || true)"
        if [[ "$state" == *Z* ]]; then
            break
        fi
        if (( $(date +%s) >= next_report )); then
            {
                date -u '+%Y-%m-%d %H:%M:%S UTC'
                ps -p "$training_pid" -o pid=,etime=,stat=,cmd= || true
                tail -n 8 "$OUTPUT_DIR/run.log" || true
                nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader || true
            } >> "$OUTPUT_DIR/retry-monitor.log" 2>&1
            next_report=$(( $(date +%s) + 1800 ))
        fi
        sleep 15
    done
    wait "$training_pid"
    exit_status="$?"
    if [[ -f "$OUTPUT_DIR/completed.json" ]]; then
        break
    fi

    # Record failure evidence before retrying the same configuration and newest complete checkpoint.
    {
        printf '%s SFT exited with status %s; retry follows with unchanged settings.\n' "$(date -u '+%Y-%m-%d %H:%M:%S UTC')" "$exit_status"
        tail -n 100 "$OUTPUT_DIR/run.log"
    } >> "$OUTPUT_DIR/retry-monitor.log" 2>&1
    sleep 15
done
