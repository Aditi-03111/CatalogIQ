"""
AttributeRepository — data access layer for ProductAttribute and AttributeEvidence.

Follows the same pattern as ProductRepository:
  - Direct SQLModel Session usage (no ORM relationships)
  - Returns model instances or None
  - No business logic — only persistence concerns
"""
import uuid
import logging
from datetime import datetime, timezone
from typing import List, Optional

from sqlmodel import Session, select, and_

from app.models import (
    ProductAttribute,
    AttributeEvidence,
    AttributeDataType,
    AttributeStatus,
    ValidationResult,
    ValidationType,
    ValidationSeverity,
    ValidationStatus,
)

logger = logging.getLogger(__name__)


class AttributeRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    # -----------------------------------------------------------------------
    # ProductAttribute
    # -----------------------------------------------------------------------

    def get_attribute(
        self, product_id: uuid.UUID, attribute_name: str
    ) -> Optional[ProductAttribute]:
        """
        Returns the first ProductAttribute matching product_id + attribute_name.
        Multiple values for the same attribute name are supported (no unique constraint).
        Returns the highest-confidence one for conflict detection purposes.
        """
        stmt = (
            select(ProductAttribute)
            .where(
                and_(
                    ProductAttribute.product_id == product_id,
                    ProductAttribute.attribute_name == attribute_name,
                )
            )
            .order_by(ProductAttribute.confidence.desc())
        )
        return self.session.exec(stmt).first()

    def get_all_attributes_for_name(
        self, product_id: uuid.UUID, attribute_name: str
    ) -> List[ProductAttribute]:
        """Returns all ProductAttributes for a given product and attribute name."""
        stmt = select(ProductAttribute).where(
            and_(
                ProductAttribute.product_id == product_id,
                ProductAttribute.attribute_name == attribute_name,
            )
        )
        return list(self.session.exec(stmt).all())

    def create_attribute(self, attribute: ProductAttribute) -> ProductAttribute:
        """Persist a new ProductAttribute and return refreshed."""
        self.session.add(attribute)
        self.session.commit()
        self.session.refresh(attribute)
        return attribute

    def update_attribute(self, attribute: ProductAttribute) -> ProductAttribute:
        """Persist changes to an existing ProductAttribute."""
        attribute.updated_at = datetime.now(timezone.utc)
        self.session.add(attribute)
        self.session.commit()
        self.session.refresh(attribute)
        return attribute

    def upsert_attribute(self, attribute: ProductAttribute) -> ProductAttribute:
        """
        Idempotently creates or updates a ProductAttribute record based on
        (product_id, attribute_name). Preserves existing ID and created_at timestamps.
        """
        existing = self.get_attribute(attribute.product_id, attribute.attribute_name)
        now = datetime.now(timezone.utc)
        if existing:
            existing.display_name = attribute.display_name
            existing.raw_value = attribute.raw_value
            existing.normalized_value = attribute.normalized_value
            existing.unit = attribute.unit
            existing.data_type = attribute.data_type
            existing.confidence = attribute.confidence
            existing.status = attribute.status
            existing.source_type = attribute.source_type
            existing.updated_at = now
            self.session.add(existing)
            return existing
        else:
            attribute.created_at = now
            attribute.updated_at = now
            self.session.add(attribute)
            return attribute

    def list_by_product(self, product_id: uuid.UUID) -> List[ProductAttribute]:
        """Returns all attributes for a product, ordered by attribute_name."""
        stmt = (
            select(ProductAttribute)
            .where(ProductAttribute.product_id == product_id)
            .order_by(ProductAttribute.attribute_name)
        )
        return list(self.session.exec(stmt).all())

    # -----------------------------------------------------------------------
    # AttributeEvidence
    # -----------------------------------------------------------------------

    def add_evidence(self, evidence: AttributeEvidence) -> AttributeEvidence:
        """Persist a new AttributeEvidence record and return refreshed."""
        self.session.add(evidence)
        self.session.commit()
        self.session.refresh(evidence)
        return evidence

    def upsert_evidence(self, evidence: AttributeEvidence) -> AttributeEvidence:
        """
        Idempotently creates or updates an AttributeEvidence record based on
        (attribute_id, document_id).
        """
        stmt = select(AttributeEvidence).where(
            and_(
                AttributeEvidence.attribute_id == evidence.attribute_id,
                AttributeEvidence.document_id == evidence.document_id,
            )
        )
        existing = self.session.exec(stmt).first()
        if existing:
            existing.page_number = evidence.page_number
            existing.evidence_text = evidence.evidence_text
            existing.bbox_metadata = evidence.bbox_metadata
            existing.extraction_method = evidence.extraction_method
            if evidence.source_id:
                existing.source_id = evidence.source_id
            self.session.add(existing)
            return existing
        else:
            self.session.add(evidence)
            return evidence

    def get_evidence_for_attribute(
        self, attribute_id: uuid.UUID
    ) -> List[AttributeEvidence]:
        """Returns all evidence records for a given attribute."""
        stmt = select(AttributeEvidence).where(
            AttributeEvidence.attribute_id == attribute_id
        )
        return list(self.session.exec(stmt).all())

    def get_evidence_for_product(
        self, product_id: uuid.UUID
    ) -> List[AttributeEvidence]:
        """
        Returns all AttributeEvidence for all attributes of a product.
        Uses a join through ProductAttribute.
        """
        stmt = (
            select(AttributeEvidence)
            .join(ProductAttribute, ProductAttribute.id == AttributeEvidence.attribute_id)
            .where(ProductAttribute.product_id == product_id)
        )
        return list(self.session.exec(stmt).all())

    # -----------------------------------------------------------------------
    # Conflict / ValidationResult helpers
    # -----------------------------------------------------------------------

    def create_conflict_validation(
        self,
        product_id: uuid.UUID,
        attribute_id: uuid.UUID,
        existing_value: str,
        new_value: str,
        existing_confidence: float,
        new_confidence: float,
    ) -> ValidationResult:
        """
        Creates a ValidationResult record for a cross-source attribute conflict.
        This does NOT overwrite either value — it flags the discrepancy for human review.
        """
        validation = ValidationResult(
            product_id=product_id,
            attribute_id=attribute_id,
            validation_type=ValidationType.cross_source_conflict,
            severity=ValidationSeverity.warning,
            status=ValidationStatus.open,
            message=(
                f"Attribute value conflict detected. "
                f"Existing: '{existing_value}' (confidence={existing_confidence:.2f}). "
                f"New: '{new_value}' (confidence={new_confidence:.2f}). "
                f"Human review required."
            ),
            expected_value=existing_value,
            actual_value=new_value,
        )
        self.session.add(validation)
        self.session.commit()
        self.session.refresh(validation)
        return validation
