#!/usr/bin/env bash
set -e

# ───── Config ─────────────────────────────────────────────────────────────
REPO="/home/admin/edm-v2"
FRONTEND="$REPO/frontend"
BACKEND="$REPO/backend"
LOG="$REPO/deploy.log"
HOST="0.0.0.0"
PORT_BACKEND=8887
PORT_FRONTEND=3000
# ───── Logging ─────────────────────────────────────────────────────────────
exec > >(tee -a "$LOG") 2>&1

echo "=== Deploy started $(date +%F_%T) ==="

# ───── 1. Pull Git ───────────────────────────────────────────────────────
cd "$REPO"
git pull origin main

# ───── 2. Frontend ───────────────────────────────────────────────────────
cd "$FRONTEND"
npm install --no-fund --no-progress
npm run build
[ -x "$(command -v pm2)" ] && pm2 reload next-frontend || echo "pm2 not found – skip restart"

# ───── 3. Backend ───────────────────────────────────────────────────────
cd "$BACKEND"
source "$REPO/.venv/bin/activate"
pip install -r requirements.txt
alembic upgrade head
sudo systemctl restart edm-backend.service || echo "service not enabled"

# ───── 4. Health check ───────────────────────────────────────────────────
sleep 3
curl -sf http://$HOST:$PORT_BACKEND/health || echo "⚠️ Backend health check failed"

echo "=== Deploy finished $(date +%F_%T) ==="
