import uuid
from enum import Enum
from datetime import datetime, timezone
from typing import Optional
from sqlmodel import SQLModel, Field, Column
import sqlalchemy as sa
from sqlalchemy import DateTime, Text

class EnrichmentType(str, Enum):
    description = "description"
    seo_title = "seo_title"
    seo_description = "seo_description"
    feature_bullets = "feature_bullets"
    applications = "applications"
    keywords = "keywords"
    attribute_suggestion = "attribute_suggestion"

class EnrichmentStatus(str, Enum):
    pending = "pending"
    completed = "completed"
    failed = "failed"
    approved = "approved"
    rejected = "rejected"

class EnrichmentResult(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    product_id: uuid.UUID = Field(
        sa_column=Column(sa.Uuid, sa.ForeignKey("product.id", ondelete="CASCADE"), index=True, nullable=False)
    )
    enrichment_type: EnrichmentType = Field(sa_column=Column(sa.String, nullable=False))
    generated_value: str = Field(sa_column=Column(Text, nullable=False))
    model: str = Field(nullable=False)
    prompt_version: str = Field(nullable=False)
    confidence: float = Field(default=1.0, nullable=False)
    status: EnrichmentStatus = Field(default=EnrichmentStatus.pending, sa_column=Column(sa.String, nullable=False))
    
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    approved_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    approved_by: Optional[str] = Field(default=None, nullable=True)
