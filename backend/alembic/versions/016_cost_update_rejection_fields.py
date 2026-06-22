"""Add rejected_by and rejected_at to cost_updates table.

Revision ID: 016_cost_update_rejection_fields
Revises: 015_enrichment_queue_sync
Create Date: 2026-06-22
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision = "016_cost_update_rejection_fields"
down_revision = "015_enrichment_queue_sync"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add rejected_by column (FK to users.id, nullable)
    op.add_column(
        "cost_updates",
        sa.Column(
            "rejected_by",
            sa.UUID(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    # Add rejected_at column (timestamp with timezone, nullable)
    op.add_column(
        "cost_updates",
        sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("cost_updates", "rejected_at")
    op.drop_column("cost_updates", "rejected_by")