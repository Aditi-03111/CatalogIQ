import uuid
from enum import Enum
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlmodel import SQLModel, Field, Column
import sqlalchemy as sa
from sqlalchemy import JSON, DateTime, UniqueConstraint

class CacheType(str, Enum):
    document = "document"
    ocr = "ocr"
    extraction = "extraction"
    embedding = "embedding"
    enrichment = "enrichment"

class CacheStatus(str, Enum):
    valid = "valid"
    expired = "expired"
    invalidated = "invalidated"

class ProductVersion(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    product_id: uuid.UUID = Field(
        sa_column=Column(sa.Uuid, sa.ForeignKey("product.id", ondelete="CASCADE"), index=True, nullable=False)
    )
    version_number: int = Field(nullable=False)
    snapshot: Dict[str, Any] = Field(sa_column=Column(JSON, nullable=False))  # Complete state snapshot
    change_summary: Optional[str] = Field(default=None, nullable=True)
    pipeline_version: str = Field(nullable=False)
    schema_version: str = Field(nullable=False)
    model_metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, sa_column=Column(JSON))
    
    created_by: str = Field(nullable=False)  # AI, system, or specific user
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )

class CacheEntry(SQLModel, table=True):
    # Unique constraint on cache_key to ensure clean single lookups
    __table_args__ = (
        UniqueConstraint("cache_key", name="uq_cache_entry_key"),
    )
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    cache_key: str = Field(index=True, nullable=False)
    cache_type: CacheType = Field(sa_column=Column(sa.String, nullable=False))
    input_hash: str = Field(index=True, nullable=False)
    result_reference: str = Field(nullable=False)  # Ref to file path or database primary key
    
    model: Optional[str] = Field(default=None, nullable=True)
    prompt_version: Optional[str] = Field(default=None, nullable=True)
    schema_version: Optional[str] = Field(default=None, nullable=True)
    pipeline_version: Optional[str] = Field(default=None, nullable=True)
    
    cache_status: CacheStatus = Field(default=CacheStatus.valid, sa_column=Column(sa.String, nullable=False))
    
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    expires_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    metadata_json: Optional[Dict[str, Any]] = Field(default_factory=dict, sa_column=Column("metadata", JSON))

class EmbeddingMetadata(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    product_id: uuid.UUID = Field(
        sa_column=Column(sa.Uuid, sa.ForeignKey("product.id", ondelete="CASCADE"), index=True, nullable=False)
    )
    vector_id: str = Field(nullable=False)  # Corresponding ID in Qdrant collection
    collection_name: str = Field(nullable=False)
    embedding_model: str = Field(nullable=False)
    content_hash: str = Field(nullable=False)
    dimensions: int = Field(nullable=False)
    
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
