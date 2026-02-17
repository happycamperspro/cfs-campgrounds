#!/usr/bin/env bash
# Campfire Campgrounds - Production Startup Script
set -e

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "=== Campfire Campgrounds - Production Mode ==="

# ---- Backend ----
echo "[1/5] Installing backend dependencies..."
cd "$PROJECT_ROOT"
uv pip install -r "$PROJECT_ROOT/backend/requirements.txt" --quiet

# ---- Firebase Functions venv ----
echo "[2/5] Setting up Firebase Functions virtual environment..."
cd "$PROJECT_ROOT/functions"
python3.13 -m venv venv
venv/bin/pip install -r requirements.txt --quiet

# ---- Frontend ----
echo "[3/5] Installing frontend dependencies..."
cd "$PROJECT_ROOT"
npm ci --silent

# ---- Build Frontend ----
echo "[4/5] Building frontend for production..."
npm run build

# ---- Deploy to Firebase ----
echo "[5/5] Deploying to Firebase (hosting + functions)..."
firebase deploy
