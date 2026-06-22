#!/usr/bin/env bash
set -e
set -o pipefail

# ===== EDM v2.1 Deploy Script (Plesk + Direct) =====
# This script is designed to work from either:
#   A) Plesk document root  — /var/www/vhosts/econsulting.services/pylon.ergalyon.com/
#   B) EDM service path      — /var/www/vhosts/pylon.ergalyon.com/edm/
#
# It auto-detects which location it's running from and acts accordingly.
# In mode A, it first rsyncs the pulled code to the EDM service path.
# Then it runs deploy steps (deps, migrate, build, restart, healthcheck).

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
EDM_BASE="/var/www/vhosts/pylon.ergalyon.com/edm"
DOCROOT="/var/www/vhosts/econsulting.services/pylon.ergalyon.com"
LOG="$SCRIPT_DIR/deploy.log"
BACKEND_HOST="127.0.0.1"
BACKEND_PORT=3005

exec > >(tee -a "$LOG") 2>&1
echo "=== Deploy started $(date +%F_%T) ==="
echo "Script dir: $SCRIPT_DIR"

# ── Determine actual EDM base ──────────────────────────────────
if [ "$SCRIPT_DIR" = "$DOCROOT" ]; then
    RUNNING_FROM_PLESK=true
    echo "Mode: Plesk document root → will sync to $EDM_BASE"
    ACTUAL_BASE="$EDM_BASE"

    # Rsync code from document root to EDM service path
    echo "--- Syncing code ---"
    rsync -a --delete \
        --exclude=".env" --exclude="venv/" --exclude="uploads/" --exclude="backups/" \
        --exclude="data/" --exclude="deploy.log" --exclude=".git" \
        "$DOCROOT/" "$EDM_BASE/"
    echo "   Sync done"

    # Also sync .env if missing in EDM path
    [ -f "$DOCROOT/.env" ] && [ ! -f "$EDM_BASE/.env" ] && cp "$DOCROOT/.env" "$EDM_BASE/.env"
else
    RUNNING_FROM_PLESK=false
    echo "Mode: EDM service path (direct)"
    ACTUAL_BASE="$SCRIPT_DIR"
fi

cd "$ACTUAL_BASE"

# 1. Git pull (in case EDM path has its own git repo, or Plesk version)
echo "--- Git pull ---"
GIT_DIR="$ACTUAL_BASE/.git"
if [ -d "$GIT_DIR" ]; then
    git pull origin main 2>/dev/null || true
else
    echo "   No .git directory at $ACTUAL_BASE, skipping pull"
fi

# 2. Backend — install deps + migrate
echo "--- Backend update ---"
export PATH="$ACTUAL_BASE/venv/bin:$PATH"
DB_URL=$(grep "^DATABASE_URL" "$ACTUAL_BASE/.env" | cut -d= -f2-)
cd "$ACTUAL_BASE/backend"
"$ACTUAL_BASE/venv/bin/pip" install -r "$ACTUAL_BASE/requirements.txt" -q
echo "   Running migrations..."
DATABASE_URL="$DB_URL" "$ACTUAL_BASE/venv/bin/alembic" upgrade head
echo "   Backend OK"

# 3. Frontend — install + build
echo "--- Frontend build ---"
export PATH="/opt/plesk/node/23/bin:$PATH"
cd "$ACTUAL_BASE/frontend"
npm install --no-fund --no-progress
npm run build
echo "   Frontend OK"

# 4. Restart all services
echo "--- Restarting services ---"
for svc in edm-backend edm-celery edm-frontend; do
    if systemctl list-units --type=service --all 2>/dev/null | grep -q "$svc"; then
        systemctl restart "$svc" && echo "   $svc restarted" || echo "   WARNING: $svc restart failed"
    else
        echo "   WARNING: $svc not found, skipping"
    fi
done

# 5. Health check
echo "--- Health check ---"
sleep 3
BACKEND_OK=false
for i in 1 2 3; do
    if curl -sf "http://$BACKEND_HOST:$BACKEND_PORT/health" > /dev/null 2>&1; then
        echo "   Backend health check OK (attempt $i)"
        BACKEND_OK=true
        break
    fi
    echo "   Backend not ready yet... (attempt $i)"
    sleep 2
done
[ "$BACKEND_OK" = false ] && echo "   WARNING: Backend health check FAILED"

echo "=== Deploy finished $(date +%F_%T) ==="
