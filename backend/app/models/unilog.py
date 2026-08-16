import uuid
from enum import Enum
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from sqlmodel import SQLModel, Field, Column
import sqlalchemy as sa
from sqlalchemy import JSON, DateTime

class UnilogStatus(str, Enum):
    queued = "queued"
    processing = "processing"
    enriched = "enriched"
    failed = "failed"

class UnilogRecord(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    mfg_part_num: str = Field(index=True, nullable=False)
    part_desc: str = Field(nullable=False)
    e1_brand: str = Field(nullable=False)
    unilog_brand: str = Field(nullable=False)
    dib_brand: str = Field(nullable=False)
    part_manuf: str = Field(nullable=False)
    
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )

class UnilogEnriched(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    record_id: uuid.UUID = Field(index=True, nullable=False, foreign_key="unilogrecord.id")
    status: UnilogStatus = Field(default=UnilogStatus.queued, sa_column=Column(sa.String, nullable=False))
    quality_score: float = Field(default=0.0, index=True, nullable=False)
    needs_review: bool = Field(default=False, index=True, nullable=False)
    
    # Store all 252 columns of the enriched template inside a single JSON object
    enriched_data: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    explainability_trace: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    validation_flags: List[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    error_message: Optional[str] = Field(default=None, nullable=True)

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
