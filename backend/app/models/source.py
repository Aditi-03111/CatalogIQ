import uuid
from enum import Enum
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlmodel import SQLModel, Field, Column
import sqlalchemy as sa
from sqlalchemy import JSON, DateTime

class SourceType(str, Enum):
    document = "document"
    manufacturer_website = "manufacturer_website"
    catalog = "catalog"
    manual = "manual"
    ai_inference = "ai_inference"
    human = "human"

class Source(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    source_type: SourceType = Field(sa_column=Column(sa.String, nullable=False))
    name: str = Field(nullable=False)
    uri: Optional[str] = Field(default=None, nullable=True)
    document_id: Optional[uuid.UUID] = Field(
        default=None, 
        sa_column=Column(sa.Uuid, sa.ForeignKey("document.id", ondelete="SET NULL"), nullable=True)
    )
    metadata_json: Optional[Dict[str, Any]] = Field(default_factory=dict, sa_column=Column("metadata", JSON))
    trust_level: float = Field(default=1.0, nullable=False)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
