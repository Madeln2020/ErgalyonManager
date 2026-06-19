"""Add rag_context column to Product table

Revision ID: 8e479a014f5d
Revises: 004_perf_indexes
Create Date: 2026-06-18 16:29:03.343114
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8e479a014f5d'
down_revision: Union[str, None] = '004_perf_indexes'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add rag_context column to products table
    op.add_column('products', sa.Column('rag_context', sa.JSON(), nullable=True))


def downgrade() -> None:
    # Remove rag_context column from products table
    op.drop_column('products', 'rag_context')
