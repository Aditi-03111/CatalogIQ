"""Add unique constraint for ProductAttribute (product_id, attribute_name)

Deduplicates any historical duplicate ProductAttribute rows and adds a unique
constraint on (product_id, attribute_name) to enforce idempotency at DB level.

Revision ID: 6f534f03ce89
Revises: 5c423f02bd8e
Create Date: 2026-08-09 18:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '6f534f03ce89'
down_revision: Union[str, None] = '5c423f02bd8e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Clean up any historical duplicate ProductAttribute rows before creating unique index
    # Keeps the latest record (highest created_at / id) per (product_id, attribute_name)
    op.execute(
        """
        DELETE FROM productattribute pa1
        USING productattribute pa2
        WHERE pa1.product_id = pa2.product_id
          AND pa1.attribute_name = pa2.attribute_name
          AND (
            pa1.updated_at < pa2.updated_at
            OR (pa1.updated_at = pa2.updated_at AND pa1.id < pa2.id)
          );
        """
    )

    # 2. Create unique constraint on (product_id, attribute_name)
    op.create_unique_constraint(
        'uq_product_attribute_name',
        'productattribute',
        ['product_id', 'attribute_name']
    )


def downgrade() -> None:
    op.drop_constraint('uq_product_attribute_name', 'productattribute', type_='unique')
