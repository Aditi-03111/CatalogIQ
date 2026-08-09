import uuid
from enum import Enum
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlmodel import SQLModel, Field, Column
import sqlalchemy as sa
from sqlalchemy import JSON, DateTime, CheckConstraint, UniqueConstraint

class ActorType(str, Enum):
    system = "system"
    ai = "ai"
    user = "user"
    worker = "worker"

class DuplicateStatus(str, Enum):
    pending = "pending"
    confirmed = "confirmed"
    rejected = "rejected"

class DuplicateMethod(str, Enum):
    sku_match = "sku_match"
    normalized_name = "normalized_name"
    attribute_similarity = "attribute_similarity"
    embedding_similarity = "embedding_similarity"
    hybrid = "hybrid"

class AuditLog(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    entity_type: str = Field(nullable=False)  # e.g., "product", "productattribute", "document"
    entity_id: uuid.UUID = Field(nullable=False)
    action: str = Field(nullable=False)  # e.g., "created", "updated", "deleted"
    
    actor_type: ActorType = Field(sa_column=Column(sa.String, nullable=False))
    actor_id: Optional[uuid.UUID] = Field(default=None, nullable=True)  # User UUID or process UUID
    
    before_state: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column("before", JSON, nullable=True))
    after_state: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column("after", JSON, nullable=True))
    metadata_json: Optional[Dict[str, Any]] = Field(default_factory=dict, sa_column=Column("metadata", JSON))
    
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )

class DuplicateCandidate(SQLModel, table=True):
    # Enforce canonical ordering (product_id < candidate_product_id) to prevent duplicate pairs
    # like A -> B and B -> A from co-existing. Enforces product_id != candidate_product_id.
    __table_args__ = (
        CheckConstraint("product_id < candidate_product_id", name="chk_duplicate_order"),
        UniqueConstraint("product_id", "candidate_product_id", name="uq_duplicate_pair"),
    )
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    product_id: uuid.UUID = Field(
        sa_column=Column(sa.Uuid, sa.ForeignKey("product.id", ondelete="CASCADE"), index=True, nullable=False)
    )
    candidate_product_id: uuid.UUID = Field(
        sa_column=Column(sa.Uuid, sa.ForeignKey("product.id", ondelete="CASCADE"), index=True, nullable=False)
    )
    similarity_score: float = Field(nullable=False)
    detection_method: DuplicateMethod = Field(sa_column=Column(sa.String, nullable=False))
    status: DuplicateStatus = Field(default=DuplicateStatus.pending, sa_column=Column(sa.String, nullable=False))
    evidence_json: Optional[Dict[str, Any]] = Field(default_factory=dict, sa_column=Column("evidence", JSON))
    
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    reviewed_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    reviewed_by: Optional[str] = Field(default=None, nullable=True)

