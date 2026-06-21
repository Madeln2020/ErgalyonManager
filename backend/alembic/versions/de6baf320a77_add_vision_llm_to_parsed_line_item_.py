"""add_vision_llm_to_parsed_line_item_extraction_source

Revision ID: de6baf320a77
Revises: 2d4e37fb6571
Create Date: 2026-06-21 02:07:56.960317
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'de6baf320a77'
down_revision: Union[str, None] = '2d4e37fb6571'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add 'vision' and 'llm' values to parsed_line_items.extraction_source constraint
    op.execute("ALTER TABLE parsed_line_items DROP CONSTRAINT chk_pli_source")
    op.create_check_constraint(
        "chk_pli_source",
        "parsed_line_items",
        "extraction_source IN ('xml','pdf_ocr','pdf_table','manual','vision','llm')"
    )


def downgrade() -> None:
    # Revert constraint to original values
    op.execute("ALTER TABLE parsed_line_items DROP CONSTRAINT chk_pli_source")
    op.create_check_constraint(
        "chk_pli_source",
        "parsed_line_items",
        "extraction_source IN ('xml','pdf_ocr','pdf_table','manual')"
    )
