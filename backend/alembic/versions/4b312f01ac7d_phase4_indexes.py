"""Phase 4 extraction indexes

Adds performance indexes for Phase 4 AI extraction queries.
No schema changes are required since all Phase 4 models (ProductAttribute,
AttributeEvidence, Source) already exist from Phase 2 migrations.

These indexes optimize:
  - Attribute lookup by source_type (extraction method analytics)
  - Evidence lookup by extraction_method (observability queries)
  - ProductAttribute confidence ordering (high-confidence attribute queries)

Revision ID: 4b312f01ac7d
Revises: 3a291f09cde8
Create Date: 2026-08-08 19:47:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4b312f01ac7d'
down_revision: Union[str, None] = '3a291f09cde8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Index on source_type for extraction analytics queries
    op.create_index(
        'ix_productattribute_source_type',
        'productattribute',
        ['source_type'],
        unique=False
    )

    # Index on extraction_method for evidence observability
    op.create_index(
        'ix_attributeevidence_extraction_method',
        'attributeevidence',
        ['extraction_method'],
        unique=False
    )

    # Composite index for confidence-ordered attribute queries per product
    op.create_index(
        'ix_productattribute_product_confidence',
        'productattribute',
        ['product_id', 'confidence'],
        unique=False
    )

    # Index on attribute_name for attribute lookup queries
    op.create_index(
        'ix_productattribute_product_name',
        'productattribute',
        ['product_id', 'attribute_name'],
        unique=False
    )

    # Add parser_version column to document table (Phase 3 omission)
    # Check if column already exists to handle re-runs gracefully
    conn = op.get_bind()
    insp = sa.inspect(conn)
    cols = [c['name'] for c in insp.get_columns('document')]
    if 'parser_version' not in cols:
        op.add_column('document', sa.Column('parser_version', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_index('ix_productattribute_product_name', table_name='productattribute')
    op.drop_index('ix_productattribute_product_confidence', table_name='productattribute')
    op.drop_index('ix_attributeevidence_extraction_method', table_name='attributeevidence')
    op.drop_index('ix_productattribute_source_type', table_name='productattribute')
