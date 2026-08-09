"""Phase 3 additions

Revision ID: 3a291f09cde8
Revises: 2e90c8a52cf1
Create Date: 2026-08-08 17:15:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3a291f09cde8'
down_revision: Union[str, None] = '2e90c8a52cf1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('document', sa.Column('parser_name', sa.String(), nullable=True))
    op.add_column('document', sa.Column('parsed_storage_key', sa.String(), nullable=True))
    op.add_column('document', sa.Column('parsed_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('processingstep', sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')))
    op.drop_column('document', 'file_path')


def downgrade() -> None:
    op.add_column('document', sa.Column('file_path', sa.String(), nullable=True))
    op.drop_column('processingstep', 'created_at')
    op.drop_column('document', 'parsed_at')
    op.drop_column('document', 'parsed_storage_key')
    op.drop_column('document', 'parser_name')
