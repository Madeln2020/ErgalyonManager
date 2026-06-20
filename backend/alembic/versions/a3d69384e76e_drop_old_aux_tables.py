"""Comprehensive schema sync: drop old aux tables + add missing supplier columns

Revision ID: a3d69384e76e
Revises: a0572c3ff658
Create Date: 2026-06-20 12:37:25.805061
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a3d69384e76e'
down_revision: Union[str, None] = 'a0572c3ff658'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ─── 1. Drop old auxiliary tables ───
    op.drop_table('scrape_configs')
    op.drop_table('export_logs')
    op.drop_table('enrichment_queue')
    # Note: parser_configs is dropped after we handle its FK references

    # ─── 2. Alter suppliers table ───
    # Add new columns
    op.add_column('suppliers', sa.Column('legal_name', sa.VARCHAR(255), nullable=True))
    op.add_column('suppliers', sa.Column('afm', sa.VARCHAR(20), nullable=True, unique=True))
    op.add_column('suppliers', sa.Column('aade_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('suppliers', sa.Column('website', sa.VARCHAR(255), nullable=True))
    op.add_column('suppliers', sa.Column('contact_persons', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('suppliers', sa.Column('payment_terms', sa.VARCHAR(100), nullable=True))
    op.add_column('suppliers', sa.Column('notes', sa.Text(), nullable=True))
    op.add_column('suppliers', sa.Column('status', sa.VARCHAR(20),
                                         sa.CheckConstraint("status IN ('ACTIVE','INACTIVE','BLACKLISTED')"),
                                         server_default='ACTIVE', nullable=False))
    op.add_column('suppliers', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('suppliers', sa.Column('code_normalization_rules', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('suppliers', sa.Column('default_parser_id', postgresql.UUID(as_uuid=True), nullable=True))

    # Migrate old status if needed (is_active -> ACTIVE/INACTIVE)
    op.execute("UPDATE suppliers SET status = CASE WHEN is_active = true THEN 'ACTIVE' ELSE 'INACTIVE' END")

    # Drop old columns
    op.drop_column('suppliers', 'vat_number')
    op.drop_column('suppliers', 'country')
    op.drop_column('suppliers', 'rules_json')
    op.drop_column('suppliers', 'parsing_profile')
    op.drop_column('suppliers', 'default_category_k1_id')
    op.drop_column('suppliers', 'is_active')

    # ─── 3. Recreate parser_configs ───
    op.drop_table('parser_configs')
    op.create_table('parser_configs',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id'), nullable=False),
        sa.Column('name', sa.VARCHAR(255), nullable=False),
        sa.Column('parser_type', sa.VARCHAR(50), nullable=False),
        sa.Column('config_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_parser_configs_organization_id'), 'parser_configs', ['organization_id'], unique=False)

    # Add FK from suppliers to parser_configs
    op.create_foreign_key('fk_suppliers_default_parser_id', 'suppliers', 'parser_configs', ['default_parser_id'], ['id'])

    # ─── 4. Recreate enrichment_queue ───
    op.create_table('enrichment_queue',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('product_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('products.id', ondelete='CASCADE'), nullable=False),
        sa.Column('enrichment_level', sa.VARCHAR(20),
                  sa.CheckConstraint("enrichment_level IN ('XML','CATALOG','PRODUCT_LIST','MANUAL','WEB_SCRAPING')"),
                  nullable=False),
        sa.Column('source', sa.VARCHAR(50), nullable=True),
        sa.Column('status', sa.VARCHAR(20),
                  sa.CheckConstraint("status IN ('PENDING','PROCESSING','COMPLETED','FAILED')"),
                  server_default='PENDING'),
        sa.Column('priority', sa.Integer(), server_default=sa.text('0')),
        sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('result', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )

    # ─── 5. Recreate export_logs ───
    op.create_table('export_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id'), nullable=False),
        sa.Column('export_type', sa.VARCHAR(20), nullable=False),
        sa.Column('file_format', sa.VARCHAR(10), nullable=False),
        sa.Column('file_path', sa.VARCHAR(500), nullable=True),
        sa.Column('status', sa.VARCHAR(20),
                  sa.CheckConstraint("status IN ('PENDING','PROCESSING','COMPLETED','FAILED')"),
                  nullable=False),
        sa.Column('total_rows', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('requested_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )

    # ─── 6. Recreate scrape_configs ───
    op.create_table('scrape_configs',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id'), nullable=False),
        sa.Column('supplier_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('suppliers.id', ondelete='CASCADE'), nullable=False),
        sa.Column('strategy', sa.VARCHAR(20),
                  sa.CheckConstraint("strategy IN ('CRAWL4AI','PLAYWRIGHT','SCRAPY','MANUAL')"),
                  nullable=False),
        sa.Column('config', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    # Reverse the upgrade
    op.drop_table('scrape_configs')
    op.drop_table('export_logs')
    op.drop_table('enrichment_queue')

    # Restore suppliers old columns
    op.drop_constraint('fk_suppliers_default_parser_id', 'suppliers', type_='foreignkey')
    op.drop_column('suppliers', 'default_parser_id')
    op.drop_column('suppliers', 'code_normalization_rules')
    op.drop_column('suppliers', 'deleted_at')
    op.drop_column('suppliers', 'status')
    op.drop_column('suppliers', 'notes')
    op.drop_column('suppliers', 'payment_terms')
    op.drop_column('suppliers', 'contact_persons')
    op.drop_column('suppliers', 'website')
    op.drop_column('suppliers', 'aade_data')
    op.drop_column('suppliers', 'afm')
    op.drop_column('suppliers', 'legal_name')

    op.add_column('suppliers', sa.Column('is_active', sa.Boolean(), server_default=sa.text('true')))
    op.add_column('suppliers', sa.Column('parsing_profile', sa.VARCHAR(50), nullable=True))
    op.add_column('suppliers', sa.Column('rules_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('suppliers', sa.Column('country', sa.VARCHAR(10), server_default='GR'))
    op.add_column('suppliers', sa.Column('vat_number', sa.VARCHAR(20), nullable=True, unique=True))
    op.add_column('suppliers', sa.Column('default_category_k1_id', postgresql.UUID(as_uuid=True), nullable=True))

    # Restore old parser_configs
    op.create_table('parser_configs',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('supplier_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('suppliers.id'), nullable=False),
        sa.Column('name', sa.VARCHAR(255), nullable=False),
        sa.Column('parser_type', sa.VARCHAR(20), nullable=False),
        sa.Column('config', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )

    # Restore old enrichment_queue
    op.create_table('enrichment_queue',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('product_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('products.id'), nullable=False),
        sa.Column('missing_fields', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('priority', sa.Integer(), server_default=sa.text('0')),
        sa.Column('source_requested', sa.VARCHAR(20), nullable=False),
        sa.Column('status', sa.VARCHAR(20), server_default=sa.text("'PENDING'")),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )

    # Restore old export_logs
    op.create_table('export_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id'), nullable=False),
        sa.Column('export_type', sa.VARCHAR(20), nullable=False),
        sa.Column('filters', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('status', sa.VARCHAR(20), nullable=False),
        sa.Column('file_path', sa.VARCHAR(500), nullable=False),
        sa.Column('record_count', sa.Integer(), nullable=False),
        sa.Column('requested_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('requested_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )

