"""Phase 5 validation and enrichment indexes

Adds performance indexes for Phase 5 validation results, enrichment records,
and product quality filtering queries.

Revision ID: 5c423f02bd8e
Revises: 4b312f01ac7d
Create Date: 2026-08-09 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '5c423f02bd8e'
down_revision: Union[str, None] = '4b312f01ac7d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Index on product_id and status for validation lookup
    op.create_index(
        'ix_validationresult_product_status',
        'validationresult',
        ['product_id', 'status'],
        unique=False
    )

    # Index on validation severity for issue filtering
    op.create_index(
        'ix_validationresult_severity',
        'validationresult',
        ['severity'],
        unique=False
    )

    # Index on enrichment product_id and status
    op.create_index(
        'ix_enrichmentresult_product_status',
        'enrichmentresult',
        ['product_id', 'status'],
        unique=False
    )

    # Index on product category and status for catalog dashboard filtering
    op.create_index(
        'ix_product_category_status',
        'product',
        ['category', 'status'],
        unique=False
    )


def downgrade() -> None:
    op.drop_index('ix_product_category_status', table_name='product')
    op.drop_index('ix_enrichmentresult_product_status', table_name='enrichmentresult')
    op.drop_index('ix_validationresult_severity', table_name='validationresult')
    op.drop_index('ix_validationresult_product_status', table_name='validationresult')
