#!/usr/bin/env bash
# Sync nermes from source repo to runtime directory
# Usage: ./sync_nermes.sh

set -euo pipefail

SOURCE="/home/elliot/projects/nermes-core"
RUNTIME="/home/elliot/.nermes/nermes-agent"
VENV_PIP="$RUNTIME/venv/bin/pip"

echo "=== Syncing nermes ==="
echo "Source:  $SOURCE"
echo "Runtime: $RUNTIME"
echo ""

# Step 1: rsync source to runtime (exclude .git, venv, __pycache__, .pytest_cache, etc.)
echo "[1/3] Rsyncing files..."
rsync -av --delete \
    --exclude '.git' \
    --exclude 'venv' \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    --exclude '.pytest_cache' \
    --exclude '.mypy_cache' \
    --exclude '.ruff_cache' \
    --exclude 'node_modules' \
    --exclude '.env' \
    --exclude '*.egg-info' \
    "$SOURCE/" "$RUNTIME/"

# Step 2: Reinstall in editable mode (handles any compilation/build steps)
echo ""
echo "[2/3] Reinstalling in venv..."
"$VENV_PIP" install -e "$RUNTIME" --quiet

# Step 3: Verify
echo ""
echo "[3/3] Verifying..."
echo "Installed version: $("$VENV_PIP" show hermes-agent 2>/dev/null | grep Version)"
echo ""
echo "=== Sync complete ==="
