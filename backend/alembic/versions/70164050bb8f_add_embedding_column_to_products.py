"""add_embedding_column_to_products

Revision ID: 70164050bb8f
Revises: 8e479a014f5d
Create Date: 2026-06-18 22:44:24.672684
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '70164050bb8f'
down_revision: Union[str, None] = '8e479a014f5d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ONLY add the embedding column — no index drops, no type changes
    op.add_column('products', sa.Column('embedding', postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    # ONLY drop the embedding column
    op.drop_column('products', 'embedding')
