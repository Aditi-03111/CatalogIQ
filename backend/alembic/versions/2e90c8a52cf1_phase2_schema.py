"""Phase 2 schema

Revision ID: 2e90c8a52cf1
Revises: 1e39a2b5fb9d
Create Date: 2026-08-08 15:15:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2e90c8a52cf1'
down_revision: Union[str, None] = '1e39a2b5fb9d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Update existing 'document' table fields to match refined Phase 2 model
    op.add_column('document', sa.Column('storage_backend', sa.String(), nullable=False, server_default='local'))
    op.add_column('document', sa.Column('storage_key', sa.String(), nullable=True))
    op.add_column('document', sa.Column('content_hash', sa.String(), nullable=True))
    op.add_column('document', sa.Column('page_count', sa.Integer(), nullable=True))
    op.add_column('document', sa.Column('parser_version', sa.String(), nullable=True))
    op.add_column('document', sa.Column('metadata', sa.JSON(), nullable=True))
    op.create_index(op.f('ix_document_content_hash'), 'document', ['content_hash'], unique=False)
    
    # In SQLite we might not have server_default, but storage_key is key in postgres.
    # Set storage_key equal to file_path to migrate existing document data safely.
    op.execute("UPDATE document SET storage_key = file_path")
    # Alter storage_key to non-nullable now that data is populated
    op.alter_column('document', 'storage_key', nullable=False)

    # 2. Update existing 'processingjob' to include needs_review_items and metadata columns
    op.add_column('processingjob', sa.Column('completed_items', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('processingjob', sa.Column('failed_items', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('processingjob', sa.Column('needs_review_items', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('processingjob', sa.Column('current_stage', sa.String(), nullable=True))
    op.add_column('processingjob', sa.Column('error_message', sa.String(), nullable=True))
    op.add_column('processingjob', sa.Column('started_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('processingjob', sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('processingjob', sa.Column('metadata', sa.JSON(), nullable=True))

    # 3. Update existing 'processingstep' to include attempt_count, worker_id, input_hash, output_hash, and metadata columns
    op.add_column('processingstep', sa.Column('attempt_count', sa.Integer(), nullable=False, server_default='1'))
    op.add_column('processingstep', sa.Column('worker_id', sa.String(), nullable=True))
    op.add_column('processingstep', sa.Column('input_hash', sa.String(), nullable=True))
    op.add_column('processingstep', sa.Column('output_hash', sa.String(), nullable=True))
    op.add_column('processingstep', sa.Column('metadata', sa.JSON(), nullable=True))
    op.add_column('processingstep', sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')))

    # 4. Update existing 'product' table to add attributes and composite unique constraint
    # (Note: In Phase 1 we already had attributes, features, applications, certifications, keywords sa.JSON.
    # We add the Brand + SKU uniqueness constraint here)
    op.create_unique_constraint('uq_product_brand_sku', 'product', ['brand', 'sku'])

    # 5. Create new tables
    # 5a. Create 'source' table
    op.create_table(
        'source',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('source_type', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('uri', sa.String(), nullable=True),
        sa.Column('document_id', sa.Uuid(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('trust_level', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['document_id'], ['document.id'], name='fk_source_document_id', ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )

    # 5b. Create 'product_document_association' junction table
    op.create_table(
        'product_document_association',
        sa.Column('product_id', sa.Uuid(), nullable=False),
        sa.Column('document_id', sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(['document_id'], ['document.id'], name='fk_pda_document_id', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['product_id'], ['product.id'], name='fk_pda_product_id', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('product_id', 'document_id')
    )

    # 5c. Create 'productattribute' table (replacing attribute-level metadata in Product)
    op.create_table(
        'productattribute',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('product_id', sa.Uuid(), nullable=False),
        sa.Column('attribute_name', sa.String(), nullable=False),
        sa.Column('display_name', sa.String(), nullable=False),
        sa.Column('raw_value', sa.Text(), nullable=False),
        sa.Column('normalized_value', sa.JSON(), nullable=True),
        sa.Column('unit', sa.String(), nullable=True),
        sa.Column('data_type', sa.String(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('source_type', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['product_id'], ['product.id'], name='fk_pa_product_id', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_productattribute_product_id'), 'productattribute', ['product_id'], unique=False)
    op.create_index(op.f('ix_productattribute_attribute_name'), 'productattribute', ['attribute_name'], unique=False)

    # 5d. Create 'attributeevidence' table
    op.create_table(
        'attributeevidence',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('attribute_id', sa.Uuid(), nullable=False),
        sa.Column('source_id', sa.Uuid(), nullable=True),
        sa.Column('document_id', sa.Uuid(), nullable=True),
        sa.Column('page_number', sa.Integer(), nullable=True),
        sa.Column('evidence_text', sa.Text(), nullable=False),
        sa.Column('bbox', sa.JSON(), nullable=True),
        sa.Column('extraction_method', sa.String(), nullable=False, server_default='llm'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['attribute_id'], ['productattribute.id'], name='fk_ae_attribute_id', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['document_id'], ['document.id'], name='fk_ae_document_id', ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['source_id'], ['source.id'], name='fk_ae_source_id', ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_attributeevidence_attribute_id'), 'attributeevidence', ['attribute_id'], unique=False)

    # 5e. Create 'validationresult' table
    op.create_table(
        'validationresult',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('product_id', sa.Uuid(), nullable=False),
        sa.Column('attribute_id', sa.Uuid(), nullable=True),
        sa.Column('validation_type', sa.String(), nullable=False),
        sa.Column('severity', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('expected_value', sa.JSON(), nullable=True),
        sa.Column('actual_value', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolved_by', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['attribute_id'], ['productattribute.id'], name='fk_vr_attribute_id', ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['product_id'], ['product.id'], name='fk_vr_product_id', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_validationresult_product_id'), 'validationresult', ['product_id'], unique=False)

    # 5f. Create 'enrichmentresult' table
    op.create_table(
        'enrichmentresult',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('product_id', sa.Uuid(), nullable=False),
        sa.Column('enrichment_type', sa.String(), nullable=False),
        sa.Column('generated_value', sa.Text(), nullable=False),
        sa.Column('model', sa.String(), nullable=False),
        sa.Column('prompt_version', sa.String(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('approved_by', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['product_id'], ['product.id'], name='fk_er_product_id', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_enrichmentresult_product_id'), 'enrichmentresult', ['product_id'], unique=False)

    # 5g. Create 'productversion' table
    op.create_table(
        'productversion',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('product_id', sa.Uuid(), nullable=False),
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.Column('snapshot', sa.JSON(), nullable=False),
        sa.Column('change_summary', sa.String(), nullable=True),
        sa.Column('pipeline_version', sa.String(), nullable=False),
        sa.Column('schema_version', sa.String(), nullable=False),
        sa.Column('model_metadata', sa.JSON(), nullable=True),
        sa.Column('created_by', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['product_id'], ['product.id'], name='fk_pv_product_id', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_productversion_product_id'), 'productversion', ['product_id'], unique=False)

    # 5h. Create 'cacheentry' table
    op.create_table(
        'cacheentry',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('cache_key', sa.String(), nullable=False),
        sa.Column('cache_type', sa.String(), nullable=False),
        sa.Column('input_hash', sa.String(), nullable=False),
        sa.Column('result_reference', sa.String(), nullable=False),
        sa.Column('model', sa.String(), nullable=True),
        sa.Column('prompt_version', sa.String(), nullable=True),
        sa.Column('schema_version', sa.String(), nullable=True),
        sa.Column('pipeline_version', sa.String(), nullable=True),
        sa.Column('cache_status', sa.String(), nullable=False, server_default='valid'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('cache_key', name='uq_cache_entry_key')
    )
    op.create_index(op.f('ix_cacheentry_cache_key'), 'cacheentry', ['cache_key'], unique=True)
    op.create_index(op.f('ix_cacheentry_input_hash'), 'cacheentry', ['input_hash'], unique=False)

    # 5i. Create 'embeddingmetadata' table
    op.create_table(
        'embeddingmetadata',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('product_id', sa.Uuid(), nullable=False),
        sa.Column('vector_id', sa.String(), nullable=False),
        sa.Column('collection_name', sa.String(), nullable=False),
        sa.Column('embedding_model', sa.String(), nullable=False),
        sa.Column('content_hash', sa.String(), nullable=False),
        sa.Column('dimensions', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['product_id'], ['product.id'], name='fk_em_product_id', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_embeddingmetadata_product_id'), 'embeddingmetadata', ['product_id'], unique=False)

    # 5j. Create 'auditlog' table
    op.create_table(
        'auditlog',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('entity_type', sa.String(), nullable=False),
        sa.Column('entity_id', sa.Uuid(), nullable=False),
        sa.Column('action', sa.String(), nullable=False),
        sa.Column('actor_type', sa.String(), nullable=False),
        sa.Column('actor_id', sa.Uuid(), nullable=True),
        sa.Column('before', sa.JSON(), nullable=True),
        sa.Column('after', sa.JSON(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # 5k. Create 'duplicatecandidate' table
    op.create_table(
        'duplicatecandidate',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('product_id', sa.Uuid(), nullable=False),
        sa.Column('candidate_product_id', sa.Uuid(), nullable=False),
        sa.Column('similarity_score', sa.Float(), nullable=False),
        sa.Column('detection_method', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False, server_default='pending'),
        sa.Column('evidence', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('reviewed_by', sa.String(), nullable=True),
        sa.CheckConstraint('product_id < candidate_product_id', name='chk_duplicate_order'),
        sa.ForeignKeyConstraint(['candidate_product_id'], ['product.id'], name='fk_dc_candidate_product_id', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['product_id'], ['product.id'], name='fk_dc_product_id', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('product_id', 'candidate_product_id', name='uq_duplicate_pair')
    )
    op.create_index(op.f('ix_duplicatecandidate_product_id'), 'duplicatecandidate', ['product_id'], unique=False)
    op.create_index(op.f('ix_duplicatecandidate_candidate_product_id'), 'duplicatecandidate', ['candidate_product_id'], unique=False)


def downgrade() -> None:
    # Drop tables in reverse topological order
    op.drop_table('duplicatecandidate')
    op.drop_table('auditlog')
    op.drop_table('embeddingmetadata')
    op.drop_table('cacheentry')
    op.drop_table('productversion')
    op.drop_table('enrichmentresult')
    op.drop_table('validationresult')
    op.drop_table('attributeevidence')
    op.drop_table('productattribute')
    op.drop_table('product_document_association')
    op.drop_table('source')

    # Remove composite SKU constraints from product
    op.drop_constraint('uq_product_brand_sku', 'product', type_='unique')

    # Revert processingstep additions
    op.drop_column('processingstep', 'updated_at')
    op.drop_column('processingstep', 'metadata')
    op.drop_column('processingstep', 'output_hash')
    op.drop_column('processingstep', 'input_hash')
    op.drop_column('processingstep', 'worker_id')
    op.drop_column('processingstep', 'attempt_count')

    # Revert processingjob additions
    op.drop_column('processingjob', 'metadata')
    op.drop_column('processingjob', 'completed_at')
    op.drop_column('processingjob', 'started_at')
    op.drop_column('processingjob', 'error_message')
    op.drop_column('processingjob', 'current_stage')
    op.drop_column('processingjob', 'needs_review_items')
    op.drop_column('processingjob', 'failed_items')
    op.drop_column('processingjob', 'completed_items')

    # Revert document additions
    op.drop_index(op.f('ix_document_content_hash'), table_name='document')
    op.drop_column('document', 'metadata')
    op.drop_column('document', 'parser_version')
    op.drop_column('document', 'page_count')
    op.drop_column('document', 'content_hash')
    op.drop_column('document', 'storage_key')
    op.drop_column('document', 'storage_backend')
