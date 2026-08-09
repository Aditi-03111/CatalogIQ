import uuid
from enum import Enum
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlmodel import SQLModel, Field, Column
import sqlalchemy as sa
from sqlalchemy import JSON, DateTime, Text

class AttributeDataType(str, Enum):
    text = "text"
    numeric = "numeric"
    boolean = "boolean"
    category = "category"
    structured = "structured"

class AttributeStatus(str, Enum):
    extracted = "extracted"
    inferred = "inferred"
    verified = "verified"
    needs_review = "needs_review"
    conflicting = "conflicting"
    missing = "missing"

class ProductAttribute(SQLModel, table=True):
    __table_args__ = (
        sa.UniqueConstraint("product_id", "attribute_name", name="uq_product_attribute_name"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    product_id: uuid.UUID = Field(
        sa_column=Column(sa.Uuid, sa.ForeignKey("product.id", ondelete="CASCADE"), index=True, nullable=False)
    )
    attribute_name: str = Field(index=True, nullable=False)
    display_name: str = Field(nullable=False)
    raw_value: str = Field(sa_column=Column(Text, nullable=False))  # Text value as extracted originally
    normalized_value: Optional[Any] = Field(default=None, sa_column=Column(JSON, nullable=True))  # JSONB representation for single/list values
    unit: Optional[str] = Field(default=None, nullable=True)
    data_type: AttributeDataType = Field(sa_column=Column(sa.String, nullable=False))
    confidence: float = Field(default=1.0, nullable=False)
    status: AttributeStatus = Field(default=AttributeStatus.extracted, sa_column=Column(sa.String, nullable=False))
    source_type: str = Field(nullable=False)  # Provenance source classification
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )

class AttributeEvidence(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    attribute_id: uuid.UUID = Field(
        sa_column=Column(sa.Uuid, sa.ForeignKey("productattribute.id", ondelete="CASCADE"), index=True, nullable=False)
    )
    source_id: Optional[uuid.UUID] = Field(
        default=None,
        sa_column=Column(sa.Uuid, sa.ForeignKey("source.id", ondelete="SET NULL"), nullable=True)
    )
    document_id: Optional[uuid.UUID] = Field(
        default=None,
        sa_column=Column(sa.Uuid, sa.ForeignKey("document.id", ondelete="SET NULL"), nullable=True)
    )
    page_number: Optional[int] = Field(default=None, nullable=True)
    evidence_text: str = Field(sa_column=Column(Text, nullable=False))
    bbox_metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, sa_column=Column("bbox", JSON))
    extraction_method: str = Field(default="llm", nullable=False)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
