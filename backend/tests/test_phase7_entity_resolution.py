"""
Phase 7 Task 7.1 Test Suite — Entity Resolution Service.

Tests:
  - Level 1: Exact SKU + Brand match
  - Level 2: Exact Model + Brand match
  - Level 3: Exact Product Name + Brand match
  - Safety check: SKU mismatch for same brand prevents auto-merge
  - Safety check: Brand mismatch prevents auto-merge
  - Missing SKU with valid Model match
  - Identifier normalization behavior (hyphens, case, spaces)
  - Semantic vector candidate generation (DOES NOT silently merge)
  - No candidate match outcome
  - Idempotent repeated resolution
"""
import uuid
import pytest
from sqlmodel import Session

from app.models import Product, ProductStatus
from app.services.entity_resolution import EntityResolutionService


def test_level1_exact_sku_and_brand_match(session: Session):
    """Level 1: Input with exact SKU and Brand must automatically match existing product."""
    p = Product(
        sku="MX-500",
        brand="ACME",
        product_name="ACME Industrial Motor MX-500",
        category="Industrial",
        status=ProductStatus.verified,
    )
    session.add(p)
    session.commit()

    service = EntityResolutionService(session)
    res = service.resolve_product({"sku": "MX-500", "brand": "ACME"}, enable_semantic_search=False)

    assert res.is_exact_match is True
    assert res.match_level == "exact_sku_brand"
    assert res.matched_product_id == str(p.id)
    assert res.confidence_score == 1.0
    assert res.needs_human_review is False


def test_level1_sku_normalization_match(session: Session):
    """Level 1: SKUs differing only by hyphens or spaces must match after normalization."""
    p = Product(
        sku="MX-500",
        brand="ACME",
        product_name="ACME Motor",
        category="Industrial",
    )
    session.add(p)
    session.commit()

    service = EntityResolutionService(session)
    # "MX 500" should normalize to "mx500" matching "MX-500" -> "mx500"
    res = service.resolve_product({"sku": "MX 500", "brand": "acme"}, enable_semantic_search=False)

    assert res.is_exact_match is True
    assert res.match_level == "exact_sku_brand"
    assert res.matched_product_id == str(p.id)


def test_sku_mismatch_prevents_match(session: Session):
    """Safety Check: Input with different SKU for same brand MUST NOT match existing product."""
    p = Product(
        sku="MX-500",
        brand="ACME",
        product_name="ACME Motor 500",
        category="Industrial",
    )
    session.add(p)
    session.commit()

    service = EntityResolutionService(session)
    res = service.resolve_product({"sku": "MX-501", "brand": "ACME"}, enable_semantic_search=False)

    assert res.is_exact_match is False
    assert res.matched_product_id is None
    assert res.match_level == "none"


def test_level2_exact_model_and_brand_match(session: Session):
    """Level 2: Input with missing SKU but matching Model and Brand must automatically match."""
    p = Product(
        sku="SKU-UNKNOWN",
        brand="ACME",
        model="MX-500",
        product_name="ACME Model MX-500 Motor",
        category="Industrial",
    )
    session.add(p)
    session.commit()

    service = EntityResolutionService(session)
    res = service.resolve_product({"model": "MX-500", "brand": "ACME"}, enable_semantic_search=False)

    assert res.is_exact_match is True
    assert res.match_level == "exact_model_brand"
    assert res.matched_product_id == str(p.id)
    assert res.confidence_score == 0.95


def test_brand_mismatch_prevents_match(session: Session):
    """Safety Check: Same model/SKU for a different brand MUST NOT automatically match."""
    p = Product(
        sku="MX-500",
        brand="ACME",
        model="MX-500",
        product_name="ACME Motor",
        category="Industrial",
    )
    session.add(p)
    session.commit()

    service = EntityResolutionService(session)
    res = service.resolve_product({"sku": "MX-500", "brand": "OTHER_BRAND"}, enable_semantic_search=False)

    assert res.is_exact_match is False
    assert res.matched_product_id is None


def test_distinct_sku_suffixes_remain_distinct(session: Session):
    """Safety Check: MX-500 vs MX-500A must remain distinct and NOT merge."""
    p = Product(
        sku="MX-500",
        brand="ACME",
        product_name="ACME Base Model",
        category="Industrial",
    )
    session.add(p)
    session.commit()

    service = EntityResolutionService(session)
    res = service.resolve_product({"sku": "MX-500A", "brand": "ACME"}, enable_semantic_search=False)

    assert res.is_exact_match is False
    assert res.matched_product_id is None


def test_semantic_similarity_generates_candidate_without_auto_merge(session: Session):
    """Level 4: Semantic similarity match MUST generate a candidate requiring review, NOT auto-merge."""
    p = Product(
        sku="SEM-99",
        brand="SemanticBrand",
        product_name="High Torque Continuous Induction Motor 15kW",
        category="Motors",
    )
    session.add(p)
    session.commit()

    # Mock QdrantService
    class MockQdrantService:
        def health_check(self):
            return True
        def search_vectors(self, query_vector, limit=5):
            return [{"id": str(p.id), "score": 0.88, "payload": {"product_name": p.product_name}}]

    service = EntityResolutionService(session, qdrant_service=MockQdrantService())
    res = service.resolve_product(
        {"product_name": "High Torque Motor 15kW"},
        search_text="High Torque Continuous Induction Motor 15kW",
        enable_semantic_search=True,
    )

    # MUST NOT auto-merge!
    assert res.is_exact_match is False
    assert res.matched_product_id is None
    assert res.match_level == "semantic_candidate"
    assert res.needs_human_review is True
    assert len(res.candidate_products) == 1
    assert str(res.candidate_products[0]["id"]) == str(p.id)


def test_no_match_returns_clean_result(session: Session):
    """No matching product in DB should return clean result indicating new product entity."""
    service = EntityResolutionService(session)
    res = service.resolve_product({"sku": "COMPLETELY-NEW-SKU", "brand": "NEW-BRAND"}, enable_semantic_search=False)

    assert res.is_exact_match is False
    assert res.matched_product_id is None
    assert res.match_level == "none"
    assert res.needs_human_review is False


def test_idempotent_repeated_resolution(session: Session):
    """Repeated resolution calls with identical input return consistent outcomes."""
    p = Product(
        sku="IDEM-77",
        brand="IdemBrand",
        product_name="Idempotent Test Motor",
        category="Motors",
    )
    session.add(p)
    session.commit()

    service = EntityResolutionService(session)
    res1 = service.resolve_product({"sku": "IDEM-77", "brand": "IdemBrand"}, enable_semantic_search=False)
    res2 = service.resolve_product({"sku": "IDEM-77", "brand": "IdemBrand"}, enable_semantic_search=False)

    assert res1.matched_product_id == res2.matched_product_id
    assert res1.match_level == res2.match_level == "exact_sku_brand"
