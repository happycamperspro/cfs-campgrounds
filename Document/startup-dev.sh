#!/usr/bin/env bash
# Campfire Campgrounds - Development Startup Script
set -e

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "=== Campfire Campgrounds - Development Mode ==="

# ---- Backend ----
echo "[1/3] Installing backend dependencies..."
cd "$PROJECT_ROOT"
uv pip install -r "$PROJECT_ROOT/backend/requirements.txt" --quiet

# ---- Frontend ----
echo "[2/3] Installing frontend dependencies..."
cd "$PROJECT_ROOT"
npm install --silent

# ---- Firebase Emulators (optional) ----
# Uncomment the following lines to start Firebase emulators for local development:
# echo "[*] Starting Firebase emulators..."
# firebase emulators:start &

# ---- Start Frontend Dev Server ----
echo "[3/3] Starting Vite dev server..."
npm run dev
