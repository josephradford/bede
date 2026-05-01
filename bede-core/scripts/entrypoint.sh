#!/bin/bash
set -e

# Ensure persona file exists
if [ ! -f /app/CLAUDE.md ]; then
    echo "ERROR: CLAUDE.md not found. Bind-mount it to /app/CLAUDE.md"
    exit 1
fi

# Configure SSH key for private vault repos
if [ -f "/home/bede/.ssh/vault_key" ] && [ -s "/home/bede/.ssh/vault_key" ]; then
    chmod 600 /home/bede/.ssh/vault_key
    ssh-keyscan github.com gitlab.com bitbucket.org >> /home/bede/.ssh/known_hosts 2>/dev/null || true
    export GIT_SSH_COMMAND="ssh -i /home/bede/.ssh/vault_key -o StrictHostKeyChecking=no"
fi

# Pull Obsidian vault if VAULT_REPO is configured
if [ -n "${VAULT_REPO}" ]; then
    if [ -d "/vault/.git" ]; then
        echo "[entrypoint] Pulling vault..."
        git -C /vault pull --ff-only || echo "[entrypoint] Vault pull failed — continuing with existing state"
    else
        echo "[entrypoint] Cloning vault..."
        git clone "${VAULT_REPO}" /vault
    fi
fi

echo "[entrypoint] Starting bede-core..."
exec uv run python -m bede_core.main
