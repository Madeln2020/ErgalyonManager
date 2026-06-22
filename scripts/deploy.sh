#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────
# EDM v2.1 — Deploy Script
#   Runs: git pull → install deps → migrate → build frontend → restart
#
# Usage:
#   ./scripts/deploy.sh                   Interactive (asks before restart)
#   ./scripts/deploy.sh --auto            Non-interactive, full auto
#   ./scripts/deploy.sh --dry-run         Show what would be done, don't execute
#
# Config via env vars (or edit defaults below):
#   SERVICE_BACKEND    systemd service name for FastAPI backend
#   SERVICE_CELERY     systemd service name for Celery worker
#   SERVICE_FRONTEND   systemd service name for Next.js
#   DEPLOY_BRANCH      git branch to pull (default: main)
# ──────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

# ── Config (override via env vars) ─────────────────────────────────
SERVICE_BACKEND="${SERVICE_BACKEND:-edm-backend}"
SERVICE_CELERY="${SERVICE_CELERY:-edm-celery}"
SERVICE_FRONTEND="${SERVICE_FRONTEND:-edm-frontend}"
DEPLOY_BRANCH="${DEPLOY_BRANCH:-main}"
AUTO_MODE=false
DRY_RUN=false

# ── Parse args ────────────────────────────────────────────────────
for arg in "$@"; do
  case "$arg" in
    --auto)    AUTO_MODE=true ;;
    --dry-run) DRY_RUN=true ;;
    --help)
      sed -n '2,13p' "$0"
      exit 0
      ;;
  esac
done

# ── Colors ─────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

info()    { echo -e "${CYAN}[INFO]${NC}  $1"; }
success() { echo -e "${GREEN}[OK]${NC}    $1"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $1"; }
error()   { echo -e "${RED}[ERROR]${NC} $1"; }

# ── Helper ─────────────────────────────────────────────────────────
run_step() {
  local label="$1"
  shift
  info "$label"
  if [ "$DRY_RUN" = true ]; then
    echo "         → would run: $*"
    return 0
  fi
  if [ "$AUTO_MODE" = false ]; then
    echo -n "         → Proceed? [Y/n] "
    read -r REPLY
    if [[ "$REPLY" =~ ^[Nn] ]]; then
      warn "Skipped: $label"
      return 0
    fi
  fi
  if "$@"; then
    success "$label"
  else
    error "$label FAILED"
    return 1
  fi
}

restart_service() {
  local svc="$1"
  if systemctl is-active --quiet "$svc" 2>/dev/null; then
    info "Restarting $svc..."
    if [ "$DRY_RUN" = true ]; then
      echo "         → would run: sudo systemctl restart $svc"
    else
      sudo systemctl restart "$svc" && success "Restarted $svc" || warn "Failed to restart $svc"
    fi
  elif supervisorctl status "$svc" 2>/dev/null; then
    info "Restarting $svc (supervisor)..."
    if [ "$DRY_RUN" = true ]; then
      echo "         → would run: supervisorctl restart $svc"
    else
      supervisorctl restart "$svc" && success "Restarted $svc" || warn "Failed to restart $svc"
    fi
  else
    warn "Service $svc not found (systemd or supervisor). Check SERVICE_* env vars."
    warn "You may need to restart it manually via Plesk."
  fi
}

# ═══════════════════════════════════════════════════════════════════
echo -e "${CYAN}══════════════════════════════════════════════════${NC}"
echo -e "${CYAN}  EDM v2.1 — Deploy Script${NC}"
echo -e "${CYAN}  Branch: ${DEPLOY_BRANCH}  |  Dir: ${PROJECT_DIR}${NC}"
echo -e "${CYAN}══════════════════════════════════════════════════${NC}"

# ── Step 1: Git pull ─────────────────────────────────────────────
run_step "1/5 — Pulling latest code from ${DEPLOY_BRANCH}" \
  git pull origin "$DEPLOY_BRANCH"

# ── Step 2: Install backend deps ─────────────────────────────────
run_step "2/5 — Installing Python dependencies" \
  bash -c "cd backend && pip install -r requirements.txt -q"

# ── Step 3: Run Alembic migrations ───────────────────────────────
run_step "3/5 — Running database migrations" \
  bash -c "cd backend && alembic upgrade head"

# ── Step 4: Install frontend deps + build ────────────────────────
run_step "4/5 — Building frontend" \
  bash -c "cd frontend && npm install && npm run build"

# ── Step 5: Restart services ─────────────────────────────────────
info "5/5 — Restarting services..."
if [ "$DRY_RUN" = true ]; then
  echo "         → would restart: ${SERVICE_BACKEND}, ${SERVICE_CELERY}, ${SERVICE_FRONTEND}"
else
  restart_service "$SERVICE_BACKEND"
  restart_service "$SERVICE_CELERY"
  restart_service "$SERVICE_FRONTEND"
fi

# ── Done ──────────────────────────────────────────────────────────
echo -e "${GREEN}══════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  ✅ Deploy complete!${NC}"
echo -e "${GREEN}  Branch: ${DEPLOY_BRANCH}${NC}"
echo -e "${GREEN}  SHA:    $(git rev-parse --short HEAD)${NC}"
echo -e "${GREEN}  Date:   $(date '+%Y-%m-%d %H:%M:%S')${NC}"
echo -e "${GREEN}══════════════════════════════════════════════════${NC}"
