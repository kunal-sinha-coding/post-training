#!/usr/bin/env bash
set -euo pipefail

# Resolve the repository directory so the local environment file is independent of the current directory.
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/.env"

# Load local environment values before any setup commands use them.
if [[ -f "$ENV_FILE" ]]; then
    set -a
    # shellcheck disable=SC1090
    source "$ENV_FILE"
    set +a
fi

# Prompt for the W&B key and persist it in the local environment file when it is absent.
ensure_wandb_api_key() {
    if ! grep -qE "^WANDB_API_KEY=[^[:space:]]+$" "$ENV_FILE" 2>/dev/null; then
        read -r -s -p "Enter your WANDB_API_KEY: " WANDB_API_KEY
        printf '\n' >&2
        if [[ -z "$WANDB_API_KEY" ]]; then
            echo "WANDB_API_KEY is required to authenticate with Weights & Biases." >&2
            return 1
        fi

        umask 077
        local temporary_env_file
        temporary_env_file="$(mktemp "${ENV_FILE}.XXXXXX")"
        if [[ -f "$ENV_FILE" ]]; then
            awk -v key="$WANDB_API_KEY" '
                BEGIN { replaced = 0 }
                /^WANDB_API_KEY=/ {
                    if (!replaced) {
                        print "WANDB_API_KEY=" key
                        replaced = 1
                    }
                    next
                }
                { print }
                END {
                    if (!replaced) print "WANDB_API_KEY=" key
                }
            ' "$ENV_FILE" > "$temporary_env_file"
        else
            printf 'WANDB_API_KEY=%s\n' "$WANDB_API_KEY" > "$temporary_env_file"
        fi
        mv "$temporary_env_file" "$ENV_FILE"
        export WANDB_API_KEY
    fi
}

# Require a local W&B key before installing and configuring external services.
ensure_wandb_api_key

# Persist each valid .env variable in .bashrc before any tmux windows are created.
sync_env_to_bashrc() {
    local bashrc_file="${BASHRC_FILE:-${HOME}/.bashrc}"
    local variable_name
    local exported_value

    touch "$bashrc_file"
    while IFS= read -r variable_name; do
        if ! grep -qE "^[[:space:]]*export[[:space:]]+${variable_name}(=|[[:space:]]|$)" "$bashrc_file"; then
            printf -v exported_value '%q' "${!variable_name}"
            printf 'export %s=%s\n' "$variable_name" "$exported_value" >> "$bashrc_file"
        fi
    done < <(sed -nE 's/^[[:space:]]*(export[[:space:]]+)?([A-Za-z_][A-Za-z0-9_]*)=.*/\2/p' "$ENV_FILE" | sort -u)
}

# Make the loaded .env values available to every shell started by tmux.
sync_env_to_bashrc

# Install the Codex CLI using the official installer.
curl -fsSL https://chatgpt.com/codex/install.sh | sh

# Register every skill from the shared skills repository with Codex.
CODEX_HOME_DIR="${CODEX_HOME:-${HOME}/.codex}"
export CODEX_HOME="$CODEX_HOME_DIR"
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

# Authenticate W&B with the API key loaded from or saved to the local environment file.
export WANDB_API_KEY
wandb login --cloud --verify

# Register the hosted W&B MCP server with Codex when it is not configured.
WANDB_MCP_URL="${WANDB_MCP_URL:-https://mcp.withwandb.com/mcp}"
if ! codex mcp get wandb >/dev/null 2>&1; then
    codex mcp add wandb --url "$WANDB_MCP_URL" --bearer-token-env-var WANDB_API_KEY
fi

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
SKILLS_WORKSPACE_DIR="${SKILLS_WORKSPACE_DIR:-/workspace/skills}"
SKILLS_WORKSPACE_SETUP_COMMAND="if [[ -d \"${SKILLS_WORKSPACE_DIR}/.git\" ]]; then git -C \"${SKILLS_WORKSPACE_DIR}\" pull --ff-only origin main; else git clone \"${SKILLS_REPOSITORY_URL}\" \"${SKILLS_WORKSPACE_DIR}\"; fi; cd \"${SKILLS_WORKSPACE_DIR}\"; exec bash"
PERSONAL_WEBSITE_REPOSITORY_URL="${PERSONAL_WEBSITE_REPOSITORY_URL:-https://github.com/kunal-sinha-coding/personal-website.git}"
PERSONAL_WEBSITE_WORKSPACE_DIR="${PERSONAL_WEBSITE_WORKSPACE_DIR:-/workspace/personal-website}"
PERSONAL_WEBSITE_WORKSPACE_SETUP_COMMAND="if [[ -d \"${PERSONAL_WEBSITE_WORKSPACE_DIR}/.git\" ]]; then git -C \"${PERSONAL_WEBSITE_WORKSPACE_DIR}\" pull --ff-only origin main; else git clone \"${PERSONAL_WEBSITE_REPOSITORY_URL}\" \"${PERSONAL_WEBSITE_WORKSPACE_DIR}\"; fi; cd \"${PERSONAL_WEBSITE_WORKSPACE_DIR}\"; exec bash"

# Create a tmux window only when the requested window does not already exist.
ensure_tmux_window() {
    local window_name="$1"
    local startup_command="$2"

    if tmux list-windows -t "$SESSION_NAME" -F '#{window_name}' | grep -Fxq "$window_name"; then
        return 0
    fi

    tmux new-window -d -t "$SESSION_NAME" -n "$window_name"
    tmux send-keys -t "$SESSION_NAME:$window_name" "$startup_command" C-m
}

# Create the tmux session before checking each requested window.
if ! tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    tmux new-session -d -s "$SESSION_NAME" -n shell
fi

# Open the development windows while reusing any existing windows.
ensure_tmux_window codex "codex"
ensure_tmux_window skills "$SKILLS_WORKSPACE_SETUP_COMMAND"
ensure_tmux_window personal-website "$PERSONAL_WEBSITE_WORKSPACE_SETUP_COMMAND"
tmux select-window -t "$SESSION_NAME:codex"

# Attach to the new session with the Codex window visible.
tmux attach-session -t "$SESSION_NAME"
