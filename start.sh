#!/usr/bin/env bash
set -euo pipefail

# Install the Codex CLI using the official installer.
curl -fsSL https://chatgpt.com/codex/install.sh | sh

# Register every skill from the shared skills repository with Codex.
CODEX_HOME_DIR="${CODEX_HOME:-${HOME}/.codex}"
CODEX_SKILLS_DIR="${CODEX_HOME_DIR}/skills"
SKILLS_REPOSITORY_URL="${SKILLS_REPOSITORY_URL:-https://github.com/kunal-sinha-coding/skills.git}"
SKILLS_REPOSITORY_DIR="${CODEX_HOME_DIR}/skills-repository"
mkdir -p "$CODEX_SKILLS_DIR"
if [[ -d "$SKILLS_REPOSITORY_DIR/.git" ]]; then
    git -C "$SKILLS_REPOSITORY_DIR" pull --ff-only
else
    rm -rf "$SKILLS_REPOSITORY_DIR"
    git clone "$SKILLS_REPOSITORY_URL" "$SKILLS_REPOSITORY_DIR"
fi
while IFS= read -r -d '' skill_file; do
    skill_dir="$(dirname "$skill_file")"
    skill_name="$(basename "$skill_dir")"
    ln -sfn "$skill_dir" "$CODEX_SKILLS_DIR/$skill_name"
done < <(find "$SKILLS_REPOSITORY_DIR" -mindepth 2 -maxdepth 2 -type f -name SKILL.md -print0)

# Install the Python dependencies listed for this repository.
python3 -m pip install -r "$(dirname "$0")/requirements.txt"

# Authenticate W&B with the API key supplied through the environment.
if [[ -z "${WANDB_API_KEY:-}" ]]; then
    echo "WANDB_API_KEY is required to authenticate with Weights & Biases." >&2
    exit 1
fi
wandb login --cloud --verify

# Configure the Git identity while allowing environment-specific overrides.
GIT_USER_NAME="${GIT_USER_NAME:-Kunal Sinha}"
GIT_USER_EMAIL="${GIT_USER_EMAIL:-kunalsinha@live.com}"
git config --global user.name "$GIT_USER_NAME"
git config --global user.email "$GIT_USER_EMAIL"

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

# Require tmux before creating or reusing the development session.
if ! command -v tmux >/dev/null 2>&1; then
    echo "tmux is required but was not found." >&2
    exit 1
fi

# Create the session and windows only when they do not already exist.
SESSION_NAME="${TMUX_SESSION_NAME:-codex-work}"
if ! tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    tmux new-session -d -s "$SESSION_NAME" -n shell
    tmux new-window -d -t "$SESSION_NAME" -n codex
    tmux send-keys -t "$SESSION_NAME:codex" "codex" C-m
elif ! tmux list-windows -t "$SESSION_NAME" -F '#{window_name}' | grep -Fxq codex; then
    tmux new-window -d -t "$SESSION_NAME" -n codex
    tmux send-keys -t "$SESSION_NAME:codex" "codex" C-m
fi
tmux select-window -t "$SESSION_NAME:codex"

# Attach to the new session with the Codex window visible.
tmux attach-session -t "$SESSION_NAME"
