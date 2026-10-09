#!/usr/bin/env bash
# This monitor attaches to an already-running GRPO trainer, checks it every ten minutes, and starts checkpoint recovery only if that trainer exits before the full run and final evaluation finish.
set -u

# Resolve the repository root and the run artifacts before monitoring begins.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
PID="${1:?Pass the active trainer PID.}"
OUTPUT="outputs/grpo-mbpp-fulltrain-8x16-b128-micro2-workers8-0.5b-50000-dual-greedy-evalplus031-visible1-save10-10x-harder-luna-20261009"
LOG="$OUTPUT/supervisor.log"
INTERVAL=600

# Return the newest checkpoint that has model weights and optimizer state.
latest_complete_checkpoint() {
    python - "$OUTPUT" <<'PY'
import json
import re
import sys
from pathlib import Path
root = Path(sys.argv[1])
valid = []
for path in root.glob("checkpoint-*"):
    match = re.fullmatch(r"checkpoint-(\d+)", path.name)
    try:
        state = json.loads((path / "trainer_state.json").read_text())
        step = int(state["global_step"])
    except (OSError, ValueError, KeyError, TypeError):
        continue
    has_weights = any((path / name).is_file() for name in ("adapter_model.safetensors", "adapter_model.bin", "model.safetensors", "pytorch_model.bin"))
    has_optimizer = (path / "optimizer.pt").is_file() and (path / "scheduler.pt").is_file()
    if match and step == int(match.group(1)) and has_weights and has_optimizer:
        valid.append((step, path))
print(max(valid)[1] if valid else "")
PY
}

# Confirm that the watched PID still runs the intended trainer command.
trainer_is_alive() {
    local command_line
    command_line="$(ps -o args= -p "$PID" 2>/dev/null || true)"
    [[ "$command_line" == *"python train.py --config configs/grpo-mbpp-fulltrain-8x16-b128-micro2-workers8-0.5b-50000-dual-greedy-evalplus031-visible1-save10-10x-harder-luna-20261009.yaml"* ]]
}

# Record that this monitor attached without signaling or restarting the live trainer.
printf '[%s] Attached monitor to existing trainer PID %s at ten-minute cadence.\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$PID" | tee -a "$LOG"
while trainer_is_alive; do
    sleep "$INTERVAL"
    checkpoint="$(latest_complete_checkpoint)"
    step=0
    if [[ -n "$checkpoint" ]]; then
        step="$(python - "$checkpoint/trainer_state.json" <<'PY'
import json, sys
print(int(json.load(open(sys.argv[1]))["global_step"]))
PY
)"
    fi
    if trainer_is_alive; then
        printf '[%s] Attached monitor: trainer PID %s is alive; latest complete step %s.\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$PID" "$step" | tee -a "$LOG"
    fi
done

# Let the normal recovery supervisor decide whether completion succeeded or a checkpoint restart is needed.
checkpoint="$(latest_complete_checkpoint)"
step=0
if [[ -n "$checkpoint" ]]; then
    step="$(python - "$checkpoint/trainer_state.json" <<'PY'
import json, sys
print(int(json.load(open(sys.argv[1]))["global_step"]))
PY
)"
fi
if [[ "$step" -ge 50000 && -s "$OUTPUT/evalplus-final-metrics.json" ]]; then
    printf '[%s] Attached monitor observed successful completion at step %s with final EvalPlus metrics.\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$step" | tee -a "$LOG"
    exit 0
fi
printf '[%s] Attached trainer exited before verified completion at step %s; starting checkpoint-based recovery supervisor.\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$step" | tee -a "$LOG"
exec bash analysis/run_grpo_10x_harder_luna_supervisor.sh
