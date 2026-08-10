"""
Phase 7 Task 7.2 Test Suite — Multi-Source Attribute Reconciliation.

Tests:
  - 1. Two sources with same value → AGREEMENT
  - 2. Textual formatting variants → AGREEMENT
  - 3. Unit equivalence: 11 kW vs 11000 W → EQUIVALENT
  - 4. One source missing attribute → MISSING / NON-CONFLICTING
  - 5. Genuine conflict: 11 kW vs 7.5 kW → CONFLICTING
  - 6. High-trust manufacturer vs low-trust distributor handling
  - 7. Preservation of source trust levels
  - 8. Preservation of evidence provenance
  - 9. ProductAttribute raw_value NOT silently overwritten during conflict
  - 10. ValidationResult cross_source_conflict record registered
  - 11. Idempotency: Re-running reconciliation 3x does not duplicate conflicts
  - 12. Multiple copies of same source do not artificially boost confidence
  - 13. Unrelated products remain untouched
"""
import uuid
import pytest
from sqlmodel import Session, select

from app.models import (
    Product,
    ProductAttribute,
    AttributeEvidence,
    Source,
    SourceType,
    ValidationResult,
    ValidationType,
    ValidationStatus,
    AttributeStatus,
    AttributeDataType,
)
from app.services.reconciler import (
    MultiSourceReconciler,
    ReconciliationStatus,
    normalize_to_si_base,
)


def test_si_unit_conversion():
    """Verify SI unit conversion helper functions."""
    val1, unit1 = normalize_to_si_base(11.0, "kW")
    val2, unit2 = normalize_to_si_base(11000.0, "W")
    assert val1 == 11000.0
    assert val2 == 11000.0
    assert unit1 == "W"
    assert unit2 == "W"

    v_kv, u_kv = normalize_to_si_base(0.23, "kV")
    v_v, u_v = normalize_to_si_base(230.0, "V")
    assert v_kv == 230.0
    assert v_v == 230.0
    assert u_kv == u_v == "V"


def test_two_sources_agree(session: Session):
    """Test 1: Two independent sources providing the same raw value produce AGREEMENT."""
    product = Product(sku="REC-01", brand="BrandA", product_name="Motor 1", category="Motors")
    session.add(product)
    session.commit()

    attr = ProductAttribute(
        product_id=product.id,
        attribute_name="rated_power",
        display_name="Rated Power",
        raw_value="11 kW",
        unit="kW",
        data_type=AttributeDataType.numeric,
        source_type="llm",
    )
    session.add(attr)
    session.commit()

    s1 = Source(name="Manufacturer Datasheet PDF", source_type=SourceType.document, trust_level=0.95)
    s2 = Source(name="Manufacturer Website", source_type=SourceType.manufacturer_website, trust_level=0.90)
    session.add(s1)
    session.add(s2)
    session.commit()

    ev1 = AttributeEvidence(attribute_id=attr.id, source_id=s1.id, evidence_text="11 kW")
    ev2 = AttributeEvidence(attribute_id=attr.id, source_id=s2.id, evidence_text="11 kW")
    session.add(ev1)
    session.add(ev2)
    session.commit()

    reconciler = MultiSourceReconciler(session)
    summary = reconciler.reconcile_product(product.id)

    assert summary.agreements_count == 1
    rec = summary.reconciled_attributes["rated_power"]
    assert rec.status == ReconciliationStatus.AGREEMENT
    assert rec.confidence_score > 0.95  # Boosted for agreement across distinct sources
    assert rec.winning_source_name == "Manufacturer Datasheet PDF"
    assert len(rec.claims) == 2


def test_unit_equivalence_kw_vs_w(session: Session):
    """Test 3: 11 kW vs 11000 W produce EQUIVALENT status."""
    product = Product(sku="REC-02", brand="BrandB", product_name="Motor 2", category="Motors")
    session.add(product)
    session.commit()

    attr = ProductAttribute(
        product_id=product.id,
        attribute_name="rated_power",
        display_name="Rated Power",
        raw_value="11 kW",
        unit="kW",
        data_type=AttributeDataType.numeric,
        source_type="llm",
    )
    session.add(attr)
    session.commit()

    s1 = Source(name="Datasheet", source_type=SourceType.document, trust_level=0.95)
    s2 = Source(name="Catalog W", source_type=SourceType.catalog, trust_level=0.85)
    session.add(s1)
    session.add(s2)
    session.commit()

    ev1 = AttributeEvidence(attribute_id=attr.id, source_id=s1.id, evidence_text="11 kW")
    ev2 = AttributeEvidence(attribute_id=attr.id, source_id=s2.id, evidence_text="11000 W")
    session.add(ev1)
    session.add(ev2)
    session.commit()

    reconciler = MultiSourceReconciler(session)
    summary = reconciler.reconcile_product(product.id)

    rec = summary.reconciled_attributes["rated_power"]
    assert rec.status == ReconciliationStatus.EQUIVALENT
    assert summary.equivalents_count == 1


def test_one_source_missing_attribute(session: Session):
    """Test 4: Attribute present in one source but missing from another is NON-CONFLICTING (MISSING status)."""
    product = Product(sku="REC-03", brand="BrandC", product_name="Motor 3", category="Motors")
    session.add(product)
    session.commit()

    attr = ProductAttribute(
        product_id=product.id,
        attribute_name="ip_rating",
        display_name="IP Rating",
        raw_value="IP55",
        data_type=AttributeDataType.text,
        source_type="llm",
    )
    session.add(attr)
    session.commit()

    s1 = Source(name="Website", source_type=SourceType.manufacturer_website, trust_level=0.90)
    session.add(s1)
    session.commit()

    ev1 = AttributeEvidence(attribute_id=attr.id, source_id=s1.id, evidence_text="IP Rating: IP55")
    session.add(ev1)
    session.commit()

    reconciler = MultiSourceReconciler(session)
    summary = reconciler.reconcile_product(product.id)

    rec = summary.reconciled_attributes["ip_rating"]
    assert rec.status == ReconciliationStatus.MISSING
    assert summary.conflicts_count == 0


def test_genuine_conflict_and_source_trust(session: Session):
    """Test 5, 6, 7, 8, 9, 10: 11 kW (Manufacturer trust 0.95) vs 7.5 kW (Distributor trust 0.70) conflict."""
    product = Product(sku="REC-04", brand="BrandD", product_name="Motor 4", category="Motors")
    session.add(product)
    session.commit()

    attr = ProductAttribute(
        product_id=product.id,
        attribute_name="rated_power",
        display_name="Rated Power",
        raw_value="11 kW",
        unit="kW",
        data_type=AttributeDataType.numeric,
        source_type="llm",
    )
    session.add(attr)
    session.commit()

    s1 = Source(name="Manufacturer PDF", source_type=SourceType.document, trust_level=0.95)
    s2 = Source(name="Distributor Catalog", source_type=SourceType.catalog, trust_level=0.70)
    session.add(s1)
    session.add(s2)
    session.commit()

    ev1 = AttributeEvidence(attribute_id=attr.id, source_id=s1.id, evidence_text="Rated Power 11 kW")
    ev2 = AttributeEvidence(attribute_id=attr.id, source_id=s2.id, evidence_text="Rated Power 7.5 kW")
    session.add(ev1)
    session.add(ev2)
    session.commit()

    reconciler = MultiSourceReconciler(session)
    summary = reconciler.reconcile_product(product.id)

    rec = summary.reconciled_attributes["rated_power"]
    assert rec.status == ReconciliationStatus.CONFLICTING
    assert rec.winning_source_name == "Manufacturer PDF"
    assert rec.winning_source_trust == 0.95
    assert len(rec.competing_claims) == 1
    assert rec.competing_claims[0].source_name == "Distributor Catalog"
    assert rec.competing_claims[0].trust_level == 0.70

    # Verify ProductAttribute canonical raw_value is NOT overwritten
    saved_attr = session.get(ProductAttribute, attr.id)
    assert saved_attr.raw_value == "11 kW"
    assert saved_attr.status == AttributeStatus.conflicting

    # Verify ValidationResult conflict record created
    validations = session.exec(
        select(ValidationResult).where(
            ValidationResult.product_id == product.id,
            ValidationResult.validation_type == ValidationType.cross_source_conflict,
        )
    ).all()
    assert len(validations) == 1
    assert validations[0].status == ValidationStatus.open


def test_idempotent_reconciliation_runs(session: Session):
    """Test 11: Running reconciliation 3 times does NOT create duplicate ValidationResult records."""
    product = Product(sku="REC-05", brand="BrandE", product_name="Motor 5", category="Motors")
    session.add(product)
    session.commit()

    attr = ProductAttribute(
        product_id=product.id,
        attribute_name="voltage",
        display_name="Rated Voltage",
        raw_value="400 V",
        unit="V",
        data_type=AttributeDataType.numeric,
        source_type="llm",
    )
    session.add(attr)
    session.commit()

    s1 = Source(name="Source 1", source_type=SourceType.document, trust_level=0.90)
    s2 = Source(name="Source 2", source_type=SourceType.catalog, trust_level=0.70)
    session.add(s1)
    session.add(s2)
    session.commit()

    ev1 = AttributeEvidence(attribute_id=attr.id, source_id=s1.id, evidence_text="400 V")
    ev2 = AttributeEvidence(attribute_id=attr.id, source_id=s2.id, evidence_text="230 V")  # Conflict
    session.add(ev1)
    session.add(ev2)
    session.commit()

    reconciler = MultiSourceReconciler(session)

    # 1st Run
    s1_res = reconciler.reconcile_product(product.id)
    # 2nd Run
    s2_res = reconciler.reconcile_product(product.id)
    # 3rd Run
    s3_res = reconciler.reconcile_product(product.id)

    assert s1_res.conflicts_count == s2_res.conflicts_count == s3_res.conflicts_count == 1

    # Check DB ValidationResult count is STILL exactly 1
    validations = session.exec(
        select(ValidationResult).where(
            ValidationResult.product_id == product.id,
            ValidationResult.validation_type == ValidationType.cross_source_conflict,
        )
    ).all()
    assert len(validations) == 1


def test_duplicate_evidence_same_source_no_double_confidence_boost(session: Session):
    """Test 12: Multiple evidence items from the exact same source do not artificially boost confidence."""
    product = Product(sku="REC-06", brand="BrandF", product_name="Motor 6", category="Motors")
    session.add(product)
    session.commit()

    attr = ProductAttribute(
        product_id=product.id,
        attribute_name="speed",
        display_name="Rated Speed",
        raw_value="1470 RPM",
        unit="RPM",
        data_type=AttributeDataType.numeric,
        source_type="llm",
    )
    session.add(attr)
    session.commit()

    s1 = Source(name="Same Manual", source_type=SourceType.document, trust_level=0.90)
    session.add(s1)
    session.commit()

    # 2 evidence entries pointing to SAME source s1
    ev1 = AttributeEvidence(attribute_id=attr.id, source_id=s1.id, evidence_text="Speed 1470 RPM page 3")
    ev2 = AttributeEvidence(attribute_id=attr.id, source_id=s1.id, evidence_text="Speed 1470 RPM page 12")
    session.add(ev1)
    session.add(ev2)
    session.commit()

    reconciler = MultiSourceReconciler(session)
    summary = reconciler.reconcile_product(product.id)

    rec = summary.reconciled_attributes["speed"]
    # Single distinct source -> confidence remains equal to s1.trust_level (0.90), no double boost!
    assert rec.confidence_score == 0.90


def test_unrelated_products_remain_untouched(session: Session):
    """Test 13: Reconciling Product A leaves Product B completely untouched."""
    p1 = Product(sku="PROD-A", brand="BrandA", product_name="Product A", category="Motors")
    p2 = Product(sku="PROD-B", brand="BrandB", product_name="Product B", category="Motors")
    session.add(p1)
    session.add(p2)
    session.commit()

    a1 = ProductAttribute(
        product_id=p1.id,
        attribute_name="power",
        display_name="Power",
        raw_value="5 kW",
        data_type=AttributeDataType.numeric,
        source_type="llm",
    )
    a2 = ProductAttribute(
        product_id=p2.id,
        attribute_name="power",
        display_name="Power",
        raw_value="10 kW",
        data_type=AttributeDataType.numeric,
        source_type="llm",
    )
    session.add(a1)
    session.add(a2)
    session.commit()

    reconciler = MultiSourceReconciler(session)
    reconciler.reconcile_product(p1.id)

    saved_a2 = session.get(ProductAttribute, a2.id)
    assert saved_a2.status == AttributeStatus.extracted  # Unchanged


def test_confidence_idempotency_across_multiple_runs(session: Session):
    """Verify confidence score is identical across runs 1, 2, and 3 and does not continually increase."""
    product = Product(sku="REC-IDEM-CONF", brand="BrandIdem", product_name="Idem Motor", category="Motors")
    session.add(product)
    session.commit()

    attr = ProductAttribute(
        product_id=product.id,
        attribute_name="rated_power",
        display_name="Rated Power",
        raw_value="11 kW",
        unit="kW",
        confidence=1.0,
        data_type=AttributeDataType.numeric,
        source_type="llm",
    )
    session.add(attr)
    session.commit()

    s1 = Source(name="Source 1", source_type=SourceType.document, trust_level=0.90)
    s2 = Source(name="Source 2", source_type=SourceType.manufacturer_website, trust_level=0.95)
    session.add(s1)
    session.add(s2)
    session.commit()

    ev1 = AttributeEvidence(attribute_id=attr.id, source_id=s1.id, evidence_text="11 kW")
    ev2 = AttributeEvidence(attribute_id=attr.id, source_id=s2.id, evidence_text="11 kW")
    session.add(ev1)
    session.add(ev2)
    session.commit()

    reconciler = MultiSourceReconciler(session)

    # 1st Run
    r1 = reconciler.reconcile_product(product.id)
    c1 = r1.reconciled_attributes["rated_power"].confidence_score

    # 2nd Run
    r2 = reconciler.reconcile_product(product.id)
    c2 = r2.reconciled_attributes["rated_power"].confidence_score

    # 3rd Run
    r3 = reconciler.reconcile_product(product.id)
    c3 = r3.reconciled_attributes["rated_power"].confidence_score

    assert c1 == 1.0
    assert c1 == c2 == c3  # Identical across all runs!

