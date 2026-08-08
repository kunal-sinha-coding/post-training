#!/usr/bin/env bash
set -euo pipefail

# Install the Codex CLI using the official installer.
curl -fsSL https://chatgpt.com/codex/install.sh | sh

# Install the Python dependencies listed for this repository.
python3 -m pip install -r "$(dirname "$0")/requirements.txt"

# Install GitHub CLI when it is not already available.
if ! command -v gh >/dev/null 2>&1; then
    if command -v apt-get >/dev/null 2>&1; then
        if [[ "$(id -u)" -eq 0 ]]; then
            apt-get update
            apt-get install -y gh
        else
            sudo apt-get update
            sudo apt-get install -y gh
        fi
    else
        echo "GitHub CLI is not installed and apt-get is unavailable." >&2
        exit 1
    fi
fi

# Authenticate GitHub interactively only when this environment is not already authenticated.
if ! gh auth status >/dev/null 2>&1; then
    gh auth login
fi

# Require tmux before creating the two-window development session.
if ! command -v tmux >/dev/null 2>&1; then
    echo "tmux is required but was not found." >&2
    exit 1
fi

# Create a detached session with a shell window followed by a Codex window.
SESSION_NAME="${TMUX_SESSION_NAME:-codex-work}"
if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    echo "tmux session already exists: $SESSION_NAME" >&2
    exit 1
fi
tmux new-session -d -s "$SESSION_NAME" -n shell
tmux new-window -d -t "$SESSION_NAME" -n codex
tmux send-keys -t "$SESSION_NAME:codex" "codex" C-m
tmux select-window -t "$SESSION_NAME:codex"

# Attach to the new session with the Codex window visible.
tmux attach-session -t "$SESSION_NAME"
