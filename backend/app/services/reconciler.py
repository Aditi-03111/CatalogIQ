"""
MultiSourceReconciler — Multi-Source Product Attribute Reconciliation Service.

Aggregates specification claims from multiple authoritative sources (PDF datasheets,
websites, distributor catalogs) for a product, normalizes units and values, compares
claims, and evaluates agreement, equivalence, missing non-conflicts, and cross-source conflicts.

Key Principles:
  1. AGREEMENT: Multiple sources provide identical/equivalent values.
  2. EQUIVALENT: Values differ textually or in units (11 kW vs 11000 W) but normalize to same SI value.
  3. MISSING: Attribute is present in 1 source but unmentioned in another (NON-CONFLICTING).
  4. CONFLICTING: Multiple sources provide genuinely incompatible values (11 kW vs 7.5 kW).
  5. PROVENANCE: Every claim preserves source_id, source_name, source_type, trust_level, evidence.
  6. SAFETY: Lower-trust claims NEVER silently overwrite higher-trust canonical values.
  7. IDEMPOTENCY: Re-running reconciliation updates existing ValidationResult records without duplicating.
"""
import uuid
import logging
from enum import Enum
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field
from sqlmodel import Session, select, and_

from app.models import (
    Product,
    ProductAttribute,
    AttributeEvidence,
    Source,
    SourceType,
    ValidationResult,
    ValidationType,
    ValidationSeverity,
    ValidationStatus,
    AttributeStatus,
)
from app.repositories import ProductRepository, AttributeRepository
from app.services.normalizer import AttributeNormalizer, repair_mojibake

logger = logging.getLogger(__name__)


class ReconciliationStatus(str, Enum):
    AGREEMENT = "AGREEMENT"
    EQUIVALENT = "EQUIVALENT"
    MISSING = "MISSING"
    CONFLICTING = "CONFLICTING"
    REVIEW = "REVIEW"


class SourceClaim(BaseModel):
    source_id: Optional[str] = None
    source_name: str = "Unknown Source"
    source_type: str = "document"
    trust_level: float = 1.0
    document_id: Optional[str] = None
    page_number: Optional[int] = None
    evidence_text: str = ""
    attribute_id: Optional[str] = None
    raw_value: str = ""
    normalized_value: Optional[Any] = None
    unit: Optional[str] = None
    extraction_method: str = "llm"


class AttributeReconciliationResult(BaseModel):
    attribute_name: str
    display_name: str
    canonical_value: Optional[str] = None
    canonical_unit: Optional[str] = None
    canonical_normalized_value: Optional[Any] = None
    status: ReconciliationStatus = ReconciliationStatus.MISSING
    confidence_score: float = 1.0
    winning_source_name: Optional[str] = None
    winning_source_trust: Optional[float] = None
    claims: List[SourceClaim] = Field(default_factory=list)
    competing_claims: List[SourceClaim] = Field(default_factory=list)
    explanation: str = ""


class ProductReconciliationSummary(BaseModel):
    product_id: str
    product_name: str
    total_attributes: int = 0
    agreements_count: int = 0
    equivalents_count: int = 0
    missing_count: int = 0
    conflicts_count: int = 0
    review_count: int = 0
    overall_confidence: float = 1.0
    reconciled_attributes: Dict[str, AttributeReconciliationResult] = Field(default_factory=dict)


# SI base unit conversions dictionary
_SI_CONVERSIONS: Dict[str, Tuple[float, str]] = {
    # Power (Base: W)
    "W": (1.0, "W"), "WATTS": (1.0, "W"), "WATT": (1.0, "W"),
    "KW": (1000.0, "W"), "KILOWATT": (1000.0, "W"), "KILOWATTS": (1000.0, "W"),
    "MW": (1000000.0, "W"),
    "HP": (745.7, "W"), "HORSEPOWER": (745.7, "W"),
    # Voltage (Base: V)
    "V": (1.0, "V"), "VOLT": (1.0, "V"), "VOLTS": (1.0, "V"), "VAC": (1.0, "V"),
    "KV": (1000.0, "V"), "MV": (0.001, "V"),
    # Frequency (Base: Hz)
    "HZ": (1.0, "Hz"), "HERTZ": (1.0, "Hz"),
    "KHZ": (1000.0, "Hz"), "MHZ": (1000000.0, "Hz"),
    # Mass (Base: kg)
    "KG": (1.0, "kg"), "KILOGRAM": (1.0, "kg"), "KILOGRAMS": (1.0, "kg"),
    "G": (0.001, "kg"), "GRAM": (0.001, "kg"), "GRAMS": (0.001, "kg"),
    "LB": (0.45359237, "kg"), "LBS": (0.45359237, "kg"), "POUND": (0.45359237, "kg"),
    # Length (Base: m)
    "M": (1.0, "m"), "METER": (1.0, "m"), "METERS": (1.0, "m"),
    "CM": (0.01, "m"), "CENTIMETER": (0.01, "m"),
    "MM": (0.001, "m"), "MILLIMETER": (0.001, "m"),
    "IN": (0.0254, "m"), "INCH": (0.0254, "m"), "INCHES": (0.0254, "m"),
    # Speed (Base: RPM)
    "RPM": (1.0, "RPM"), "R/MIN": (1.0, "RPM"), "REV/MIN": (1.0, "RPM"),
}


def normalize_to_si_base(val: Any, unit: Optional[str]) -> Tuple[Any, Optional[str]]:
    """
    Converts numeric attribute values into base SI unit representations for exact equivalence.

    Examples:
      (11.0, "kW")   -> (11000.0, "W")
      (11000.0, "W") -> (11000.0, "W")
      (0.23, "kV")   -> (230.0, "V")
      (230.0, "V")   -> (230.0, "V")
      (1000.0, "g")  -> (1.0, "kg")
    """
    if val is None:
        return None, unit

    if isinstance(val, (int, float)) and unit:
        unit_upper = unit.strip().upper()
        if unit_upper in _SI_CONVERSIONS:
            multiplier, base_unit = _SI_CONVERSIONS[unit_upper]
            return float(val) * multiplier, base_unit

    return val, unit


class MultiSourceReconciler:
    """
    Service responsible for aggregating and reconciling specification claims
    from multiple sources for a given product.
    """

    def __init__(self, session: Session):
        self.session = session
        self.product_repo = ProductRepository(session)
        self.attr_repo = AttributeRepository(session)
        self.normalizer = AttributeNormalizer()

    def reconcile_product(self, product_id: uuid.UUID) -> ProductReconciliationSummary:
        """
        Runs multi-source attribute reconciliation across all attributes of a product.

        Args:
            product_id: UUID of the product to reconcile.

        Returns:
            ProductReconciliationSummary detailing reconciliation results.
        """
        product = self.product_repo.get_by_id(product_id)
        if not product:
            raise ValueError(f"Product with ID {product_id} not found")

        attributes = self.attr_repo.list_by_product(product_id)
        all_evidence = self.attr_repo.get_evidence_for_product(product_id)
        all_sources = self.session.exec(select(Source)).all()
        source_map = {str(s.id): s for s in all_sources}

        reconciled_map: Dict[str, AttributeReconciliationResult] = {}

        agreements_count = 0
        equivalents_count = 0
        missing_count = 0
        conflicts_count = 0
        review_count = 0

        for attr in attributes:
            # Gather evidence items for this attribute
            attr_evidences = [e for e in all_evidence if e.attribute_id == attr.id]

            rec_result = self._reconcile_single_attribute(
                product=product,
                attribute=attr,
                evidences=attr_evidences,
                source_map=source_map,
            )

            reconciled_map[attr.attribute_name] = rec_result

            if rec_result.status == ReconciliationStatus.AGREEMENT:
                agreements_count += 1
            elif rec_result.status == ReconciliationStatus.EQUIVALENT:
                equivalents_count += 1
            elif rec_result.status == ReconciliationStatus.MISSING:
                missing_count += 1
            elif rec_result.status == ReconciliationStatus.CONFLICTING:
                conflicts_count += 1
            elif rec_result.status == ReconciliationStatus.REVIEW:
                review_count += 1

        # Calculate overall confidence
        total_attrs = len(reconciled_map)
        if total_attrs > 0:
            overall_conf = sum(r.confidence_score for r in reconciled_map.values()) / total_attrs
        else:
            overall_conf = 1.0

        summary = ProductReconciliationSummary(
            product_id=str(product.id),
            product_name=product.product_name,
            total_attributes=total_attrs,
            agreements_count=agreements_count,
            equivalents_count=equivalents_count,
            missing_count=missing_count,
            conflicts_count=conflicts_count,
            review_count=review_count,
            overall_confidence=round(overall_conf, 4),
            reconciled_attributes=reconciled_map,
        )

        return summary

    def _reconcile_single_attribute(
        self,
        product: Product,
        attribute: ProductAttribute,
        evidences: List[AttributeEvidence],
        source_map: Dict[str, Source],
    ) -> AttributeReconciliationResult:
        """
        Reconciles specification claims for a single ProductAttribute.
        """
        claims: List[SourceClaim] = []
        # Group evidence items by source_id so each distinct Source contributes at most 1 claim
        source_evidence_map: Dict[Optional[str], AttributeEvidence] = {}
        for ev in evidences:
            src_key = str(ev.source_id) if ev.source_id else f"ev_{ev.id}"
            if src_key not in source_evidence_map:
                source_evidence_map[src_key] = ev

        # Build claims from grouped evidence records
        for src_key, ev in source_evidence_map.items():
            src_id_str = str(ev.source_id) if ev.source_id else None
            src_obj = source_map.get(src_id_str) if src_id_str else None

            src_name = src_obj.name if src_obj else "Primary Document Source"
            src_type = src_obj.source_type if src_obj else "document"
            trust_lvl = src_obj.trust_level if src_obj else 1.0

            raw_val = ev.evidence_text.strip() if ev.evidence_text and ev.evidence_text.strip() else attribute.raw_value
            norm_res = self.normalizer.normalize(raw_val, data_type=attribute.data_type, unit=attribute.unit)
            if not norm_res.success:
                # Fallback to attribute normalized value if raw evidence_text has extra text
                norm_res = self.normalizer.normalize(attribute.raw_value, data_type=attribute.data_type, unit=attribute.unit)

            claim = SourceClaim(
                source_id=src_id_str,
                source_name=src_name,
                source_type=src_type,
                trust_level=trust_lvl,
                document_id=str(ev.document_id) if ev.document_id else None,
                page_number=ev.page_number,
                evidence_text=ev.evidence_text,
                attribute_id=str(attribute.id),
                raw_value=raw_val,
                normalized_value=norm_res.normalized_value,
                unit=norm_res.unit or attribute.unit,
                extraction_method=ev.extraction_method,
            )
            claims.append(claim)

        # Fallback: if no explicit AttributeEvidence exists yet, synthesize default claim from ProductAttribute
        if not claims:
            claims.append(
                SourceClaim(
                    source_id=None,
                    source_name="Default Catalog Extraction",
                    source_type="document",
                    trust_level=1.0,
                    attribute_id=str(attribute.id),
                    raw_value=attribute.raw_value,
                    normalized_value=attribute.normalized_value,
                    unit=attribute.unit,
                    evidence_text=attribute.raw_value,
                )
            )

        # Sort claims by trust_level descending
        claims.sort(key=lambda c: c.trust_level, reverse=True)
        winning_claim = claims[0]

        # Case 1: Single Source Claim -> MISSING / NON-CONFLICTING
        if len(claims) == 1:
            return AttributeReconciliationResult(
                attribute_name=attribute.attribute_name,
                display_name=attribute.display_name,
                canonical_value=attribute.raw_value,
                canonical_unit=attribute.unit,
                canonical_normalized_value=attribute.normalized_value,
                status=ReconciliationStatus.MISSING,
                confidence_score=round(min(1.0, max(0.0, winning_claim.trust_level * attribute.confidence)), 4),
                winning_source_name=winning_claim.source_name,
                winning_source_trust=winning_claim.trust_level,
                claims=claims,
                competing_claims=[],
                explanation=f"Attribute present in single source ('{winning_claim.source_name}'). Non-conflicting.",
            )

        # Case 2: Multiple Source Claims -> Pairwise Normalized Comparison
        distinct_sources = {c.source_id for c in claims if c.source_id}

        # Compute SI-base normalized representation for each claim
        si_claims = []
        for c in claims:
            # Re-normalize claim raw value
            norm_res = self.normalizer.normalize(c.raw_value, data_type=attribute.data_type, unit=c.unit)
            si_val, si_unit = normalize_to_si_base(norm_res.normalized_value, norm_res.unit)
            si_claims.append((c, si_val, si_unit, norm_res))

        # Check if all claims agree
        base_si_val, base_si_unit = si_claims[0][1], si_claims[0][2]
        all_equal = True
        textually_identical = True

        for c, si_v, si_u, norm_res in si_claims[1:]:
            # Exact or float-tolerant equality check
            if isinstance(base_si_val, (int, float)) and isinstance(si_v, (int, float)):
                if abs(base_si_val - si_v) > 1e-5:
                    all_equal = False
            elif base_si_val != si_v:
                # Textual cleanup check
                t1 = repair_mojibake(str(base_si_val or "")).strip().lower()
                t2 = repair_mojibake(str(si_v or "")).strip().lower()
                if t1 != t2:
                    all_equal = False

            if c.raw_value.strip().lower() != winning_claim.raw_value.strip().lower():
                textually_identical = False

        if all_equal:
            status = ReconciliationStatus.AGREEMENT if textually_identical else ReconciliationStatus.EQUIVALENT
            # Boost confidence for agreement across distinct sources (max 1.0)
            agreement_bonus = 0.05 * (len(distinct_sources) - 1)
            final_conf = min(1.0, winning_claim.trust_level + agreement_bonus)

            expl = (
                f"Consensus across {len(claims)} source claims. "
                f"{'Textually identical' if textually_identical else 'SI-unit equivalent'} values."
            )

            return AttributeReconciliationResult(
                attribute_name=attribute.attribute_name,
                display_name=attribute.display_name,
                canonical_value=winning_claim.raw_value,
                canonical_unit=winning_claim.unit,
                canonical_normalized_value=winning_claim.normalized_value,
                status=status,
                confidence_score=round(final_conf, 4),
                winning_source_name=winning_claim.source_name,
                winning_source_trust=winning_claim.trust_level,
                claims=claims,
                competing_claims=[],
                explanation=expl,
            )

        # Case 3: Genuine Conflict Detected
        competing = [c for c in claims if c != winning_claim]
        competing_names = ", ".join(f"{c.raw_value} ({c.source_name})" for c in competing)

        # Update ProductAttribute status to conflicting without overwriting canonical values
        attribute.status = AttributeStatus.conflicting
        attribute.updated_at = datetime.now(timezone.utc)
        self.session.add(attribute)
        self.session.commit()

        # Idempotent ValidationResult Conflict Registration
        self._register_cross_source_conflict_validation(
            product_id=product.id,
            attribute=attribute,
            winning_claim=winning_claim,
            competing_claims=competing,
        )

        conf_penalty = max(0.2, winning_claim.trust_level - 0.25)
        expl = (
            f"Cross-source conflict: Highest trust source '{winning_claim.source_name}' "
            f"({winning_claim.trust_level}) specifies '{winning_claim.raw_value}', vs competing claim(s): {competing_names}."
        )

        return AttributeReconciliationResult(
            attribute_name=attribute.attribute_name,
            display_name=attribute.display_name,
            canonical_value=attribute.raw_value,
            canonical_unit=attribute.unit,
            canonical_normalized_value=attribute.normalized_value,
            status=ReconciliationStatus.CONFLICTING,
            confidence_score=round(conf_penalty, 4),
            winning_source_name=winning_claim.source_name,
            winning_source_trust=winning_claim.trust_level,
            claims=claims,
            competing_claims=competing,
            explanation=expl,
        )

    def _register_cross_source_conflict_validation(
        self,
        product_id: uuid.UUID,
        attribute: ProductAttribute,
        winning_claim: SourceClaim,
        competing_claims: List[SourceClaim],
    ) -> None:
        """
        Idempotently creates or updates an open ValidationResult conflict record.
        """
        # Query for existing open cross-source conflict validation for this attribute
        stmt = select(ValidationResult).where(
            and_(
                ValidationResult.product_id == product_id,
                ValidationResult.attribute_id == attribute.id,
                ValidationResult.validation_type == ValidationType.cross_source_conflict,
                ValidationResult.status == ValidationStatus.open,
            )
        )
        existing = self.session.exec(stmt).first()

        expected_dict = winning_claim.model_dump()
        actual_dict = [c.model_dump() for c in competing_claims]
        msg = f"Cross-source conflict on '{attribute.display_name}': '{winning_claim.raw_value}' ({winning_claim.source_name}) vs '{competing_claims[0].raw_value}' ({competing_claims[0].source_name})"

        if existing:
            existing.message = msg
            existing.expected_value = expected_dict
            existing.actual_value = actual_dict
            self.session.add(existing)
        else:
            val_res = ValidationResult(
                product_id=product_id,
                attribute_id=attribute.id,
                validation_type=ValidationType.cross_source_conflict,
                severity=ValidationSeverity.warning,
                status=ValidationStatus.open,
                message=msg,
                expected_value=expected_dict,
                actual_value=actual_dict,
            )
            self.session.add(val_res)

        self.session.commit()
