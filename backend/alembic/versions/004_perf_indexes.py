"""Add performance indexes for Phase 4 optimization

Revision ID: 004_perf_indexes
Revises:
Create Date: 2026-06-18
"""

from alembic import op
import sqlalchemy as sa

revision = "004_perf_indexes"
down_revision = None  # Set this to the last migration ID
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Supplier agreements ──
    op.create_index(
        "idx_supplier_agreements_supplier",
        "supplier_agreements",
        ["supplier_id"],
    )

    # ── Supplier rules ──
    op.create_index(
        "idx_supplier_rules_supplier",
        "supplier_rules",
        ["supplier_id", "is_active"],
    )

    # ── Products full‑text search ──
    # GIN index on description for fast tsvector lookups
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_products_description_fts
        ON products
        USING gin(to_tsvector('english', description))
        """
    )

    # ── Products description_normalized full‑text ──
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_products_desc_norm_fts
        ON products
        USING gin(to_tsvector('english', description_normalized))
        """
    )

    # ── Audit log ──
    op.create_index(
        "idx_audit_log_entity",
        "audit_log",
        ["entity_type", "entity_id"],
    )

    # ── Products: soft‑delete partial index (only active rows) ──
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_products_active
        ON products (supplier_id, supplier_code)
        WHERE is_deleted = false
        """
    )


def downgrade() -> None:
    op.drop_index("idx_supplier_agreements_supplier", table_name="supplier_agreements")
    op.drop_index("idx_supplier_rules_supplier", table_name="supplier_rules")
    op.execute("DROP INDEX IF EXISTS idx_products_description_fts")
    op.execute("DROP INDEX IF EXISTS idx_products_desc_norm_fts")
    op.drop_index("idx_audit_log_entity", table_name="audit_log")
    op.execute("DROP INDEX IF EXISTS idx_products_active")
