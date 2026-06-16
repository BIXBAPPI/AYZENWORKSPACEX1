#!/bin/bash
set -e

echo "=== AYZEN Build Script ==="

# Step 1: Create Python virtual environment
echo "--- Creating Python venv ---"
python3 -m venv .venv

echo "--- Installing Python dependencies ---"
# Use pip from within the venv — installs to .venv/lib, NOT the Nix store
.venv/bin/pip install --no-cache-dir --no-user -r requirements.txt

echo "--- Installing Node.js dependencies ---"
pnpm install --frozen-lockfile

echo "--- Building dashboard ---"
BASE_PATH=/ PORT=3000 pnpm --filter @workspace/dashboard run build

echo "--- Building API server ---"
pnpm --filter @workspace/api-server run build

echo "=== Build complete ==="
