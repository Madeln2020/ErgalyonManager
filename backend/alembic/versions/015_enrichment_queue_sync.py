"""Sync enrichment_queue table to match EnrichmentQueueItem model

- Rename enrichment_queue → enrichment_queue_items
- Add missing columns: company_id, source_ref
- Add check constraints for status and enrichment_level
- Add indexes
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "015_enrichment_queue_sync"
down_revision = "de6baf320a77"
branch_labels = None
depends_on = None


def upgrade():
    # 1. Rename table
    op.rename_table("enrichment_queue", "enrichment_queue_items")

    # 2. Add company_id column (nullable for now, will backfill)
    op.add_column(
        "enrichment_queue_items",
        sa.Column("company_id", UUID(as_uuid=True), nullable=True),
    )

    # 3. Backfill company_id from products table
    op.execute("""
        UPDATE enrichment_queue_items eq
        SET company_id = p.company_id
        FROM products p
        WHERE eq.product_id = p.id
    """)

    # 4. Make company_id NOT NULL and add FK
    op.alter_column("enrichment_queue_items", "company_id", nullable=False)
    op.create_foreign_key(
        "eqi_company_id_fkey",
        "enrichment_queue_items",
        "companies",
        ["company_id"],
        ["id"],
    )

    # 5. Add source_ref column
    op.add_column(
        "enrichment_queue_items",
        sa.Column("source_ref", sa.String(255), nullable=True),
    )

    # 6. Add updated_at column (TimestampMixin)
    op.add_column(
        "enrichment_queue_items",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    # 7. Add indexes
    op.create_index(
        "eqi_company_status", "enrichment_queue_items", ["company_id", "status"]
    )
    op.create_index(
        "eqi_product_status", "enrichment_queue_items", ["product_id", "status"]
    )
    op.create_index(
        "eqi_source_level", "enrichment_queue_items", ["source", "enrichment_level"]
    )

    # 8. Add FK to products
    op.create_foreign_key(
        "eqi_product_id_fkey",
        "enrichment_queue_items",
        "products",
        ["product_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade():
    op.drop_constraint("eqi_product_id_fkey", "enrichment_queue_items", type_="foreignkey")
    op.drop_constraint("eqi_company_id_fkey", "enrichment_queue_items", type_="foreignkey")
    op.drop_index("eqi_source_level", table_name="enrichment_queue_items")
    op.drop_index("eqi_product_status", table_name="enrichment_queue_items")
    op.drop_index("eqi_company_status", table_name="enrichment_queue_items")
    op.drop_column("enrichment_queue_items", "updated_at")
    op.drop_column("enrichment_queue_items", "source_ref")
    op.drop_column("enrichment_queue_items", "company_id")
    op.rename_table("enrichment_queue_items", "enrichment_queue")
