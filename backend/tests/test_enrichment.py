"""
Tests for Phase 5 AI Commerce Enrichment, Schemas, Prompts, Claim Checker, and Enrichment Confidence.
"""
import pytest
from app.services.claim_checker import ClaimChecker
from app.services.enrichment_confidence import EnrichmentConfidenceCalculator
from app.services.llm.base import CommerceEnrichment
from app.services.llm.mock_provider import MockProvider
from app.services.llm.prompts import build_enrichment_prompt


def test_commerce_enrichment_schema_validation():
    """Test CommerceEnrichment Pydantic model normalization."""
    enrichment = CommerceEnrichment(
        commerce_description="High quality motor",
        features=["Continuous duty rated", {"key": "Class F insulation"}],
        applications="Industrial conveyor systems",
        confidence=0.90,
    )

    assert enrichment.commerce_description == "High quality motor"
    assert "Continuous duty rated" in enrichment.features
    assert "Class F insulation" in enrichment.features[1]
    assert enrichment.applications == ["Industrial conveyor systems"]


def test_enrichment_prompt_construction():
    """Test building enrichment prompt from verified product context."""
    context = {
        "product_name": "MX-500 Motor",
        "brand": "CatalogIQ",
        "sku": "MX500-230",
        "category": "Industrial Motors",
        "verified_attributes": {
            "voltage": {"raw_value": "230 V"},
            "power": {"raw_value": "5.5 kW"},
        },
        "features": ["Continuous duty rated"],
    }

    prompt_str = build_enrichment_prompt(context)
    assert "MX-500 Motor" in prompt_str
    assert "230 V" in prompt_str
    assert "5.5 kW" in prompt_str
    assert "Continuous duty rated" in prompt_str


def test_mock_provider_enrichment():
    """Test MockProvider returns valid CommerceEnrichment."""
    provider = MockProvider()
    context = {
        "product_name": "MX-500 Motor",
        "brand": "CatalogIQ",
        "sku": "MX500-230",
    }

    res = provider.enrich(context)
    assert res.commerce_description is not None
    assert "MX-500" in res.commerce_description
    assert len(res.features) > 0
    assert res.confidence == 0.92


def test_claim_checker_detects_unsupported_specs():
    """Test ClaimChecker flags fabricated numeric numbers or ratings."""
    checker = ClaimChecker()

    verified_attrs = {
        "voltage": "230 V",
        "power": "5.5 kW",
    }
    verified_features = ["Continuous duty rated"]
    verified_apps = ["Conveyor systems"]

    # AI text claims 7.5 kW and IP65 protection class (not in verified context!)
    bad_enrichment = CommerceEnrichment(
        commerce_description="The motor produces 7.5 kW power with IP65 weather rating.",
        short_description="7.5 kW motor",
        features=["IP65 rated"],
        applications=["Conveyor systems"],
    )

    res = checker.check(bad_enrichment, verified_attrs, verified_features, verified_apps)

    assert not res.valid
    assert res.has_unsupported_claims
    assert len(res.unsupported_claims) >= 2


def test_enrichment_confidence_never_reaches_one():
    """Verify AI enrichment confidence is capped at <= 0.95."""
    calc = EnrichmentConfidenceCalculator()
    checker = ClaimChecker()

    verified_attrs = {"power": "5.5 kW", "voltage": "230 V"}
    good_enrichment = CommerceEnrichment(
        commerce_description="The MX-500 is a 5.5 kW 230 V motor.",
        short_description="5.5 kW 230 V motor.",
        features=["5.5 kW rated"],
    )

    claim_res = checker.check(good_enrichment, verified_attrs, [], [], product_identity_text="MX-500 Motor")
    conf = calc.calculate(claim_res, evidence_coverage=100.0, validation_health=100.0)

    assert conf <= 0.95
    assert conf >= 0.85


def test_unsupported_claim_lowers_confidence():
    """Verify unsupported claims penalize confidence below 0.50."""
    calc = EnrichmentConfidenceCalculator()
    checker = ClaimChecker()

    bad_enrichment = CommerceEnrichment(
        commerce_description="Produces 99.9 kW power.",
    )

    claim_res = checker.check(bad_enrichment, {"power": "5.5 kW"}, [], [])
    conf = calc.calculate(claim_res, evidence_coverage=100.0, validation_health=100.0)

    assert conf < 0.50
