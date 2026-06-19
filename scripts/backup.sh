#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────
# EDM v2 — Backup & Restore Utility
#
# Usage:
#   ./scripts/backup.sh backup                    Dump DB + config
#   ./scripts/backup.sh restore FILE              Restore from dump
#   ./scripts/backup.sh list                      List available backups
#
# Environment variables (can also be set in .env):
#   PGHOST, PGPORT, PGDATABASE, PGUSER, PGPASSWORD
#   BACKUP_DIR  (default: ./backups)
# ──────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# ── Configuration ────────────────────────────────────────────────────
BACKUP_DIR="${BACKUP_DIR:-$PROJECT_DIR/backups}"
PGHOST="${PGHOST:-localhost}"
PGPORT="${PGPORT:-5432}"
PGDATABASE="${PGDATABASE:-edm_v2}"
PGUSER="${PGUSER:-edm}"
PGPASSWORD="${PGPASSWORD:-edm_password}"
export PGPASSWORD

mkdir -p "$BACKUP_DIR"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# ── Help ─────────────────────────────────────────────────────────────
usage() {
    sed -n '2,10p' "$0"
    exit 1
}

# ── Functions ─────────────────────────────────────────────────────────
do_backup() {
    local dump_file="$BACKUP_DIR/edm_v2_${TIMESTAMP}.sql.gz"
    echo "→ Backing up database $PGDATABASE @ $PGHOST:$PGPORT …"
    pg_dump -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" \
        --no-owner --no-acl --format=c | gzip > "$dump_file"
    echo "✓ Backup saved: $dump_file ($(du -h "$dump_file" | cut -f1))"

    # Copy config backup (no secrets)
    cp "$PROJECT_DIR/.env" "$BACKUP_DIR/.env.backup.${TIMESTAMP}" 2>/dev/null || true

    # Keep last 14 backups, remove older
    find "$BACKUP_DIR" -name 'edm_v2_*.sql.gz' -mtime +14 -delete 2>/dev/null || true
    echo "→ Pruned backups older than 14 days."
}

do_restore() {
    local dump_file="${1:-}"
    if [ -z "$dump_file" ] || [ ! -f "$dump_file" ]; then
        echo "✗ Usage: $0 restore <dump_file>"
        exit 1
    fi

    echo "⚠  RESTORING $PGDATABASE from $dump_file …"
    echo "   This will DROP the existing database!"
    echo -n "   Are you sure? (yes/no) "
    read -r confirm
    if [ "$confirm" != "yes" ]; then
        echo "Aborted."
        exit 0
    fi

    # Drop & recreate
    psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d postgres \
        -c "DROP DATABASE IF EXISTS $PGDATABASE;" \
        -c "CREATE DATABASE $PGDATABASE OWNER $PGUSER;"

    # Restore
    gunzip -c "$dump_file" | pg_restore -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE"
    echo "✓ Restore complete: $dump_file"
}

do_list() {
    echo "Available backups in $BACKUP_DIR:"
    echo ""
    if [ "$(find "$BACKUP_DIR" -name 'edm_v2_*.sql.gz' 2>/dev/null | wc -l)" -eq 0 ]; then
        echo "  (no backups found)"
        exit 0
    fi
    ls -lhSr "$BACKUP_DIR"/edm_v2_*.sql.gz 2>/dev/null | awk '{printf "  %s  %s\n", $5, $NF}'
}

# ── Dispatch ─────────────────────────────────────────────────────────
case "${1:-help}" in
    backup)   do_backup ;;
    restore)  do_restore "${2:-}" ;;
    list)     do_list ;;
    *)        usage ;;
esac
