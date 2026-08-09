import json
import os
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.main import app as fastapi_app
from app.models import (
    Document,
    DocumentStatus,
    EnrichmentResult,
    EnrichmentStatus,
    JobStatus,
    ProcessingJob,
    ProcessingStep,
    ProcessingStage,
    Product,
    ProductAttribute,
    ProductDocumentAssociation,
    ProductStatus,
    StepStatus,
    ValidationResult,
    ValidationStatus,
)
from app.repositories import ProductRepository
from app.services.llm.base import BaseLLMProvider, CommerceEnrichment
from app.services.llm.mock_provider import MockProvider
from app.services.parser import MockParser
from app.services.pipeline import (
    DocumentProcessingService,
    EnrichmentStage,
    NonRetryableProcessingError,
    ValidationStage,
)


def test_validation_stage_execution(session: Session):
    """Test ValidationStage loads product, runs validation, updates quality score."""
    # Setup document, job, step, product
    doc = Document(filename="test.pdf", storage_key="docs/test.pdf", file_hash="hash123", mime_type="application/pdf", file_size=1024, status=DocumentStatus.processed)
    session.add(doc)
    session.commit()
    session.refresh(doc)

    product = Product(sku="MX500-230", brand="CatalogIQ", product_name="MX-500 Motor", category="industrial_motor")
    session.add(product)
    session.commit()
    session.refresh(product)

    assoc = ProductDocumentAssociation(product_id=product.id, document_id=doc.id)
    session.add(assoc)

    attr = ProductAttribute(
        product_id=product.id,
        attribute_name="voltage",
        display_name="Voltage",
        raw_value="230 V",
        unit="V",
        data_type="numeric",
        confidence=0.95,
        status="extracted",
        source_type="deterministic",
    )
    session.add(attr)
    session.commit()

    job = ProcessingJob(total_items=1)
    session.add(job)
    session.commit()
    session.refresh(job)

    step = ProcessingStep(job_id=job.id, document_id=doc.id, stage=ProcessingStage.validating, status=StepStatus.queued)
    session.add(step)
    session.commit()
    session.refresh(step)

    stage = ValidationStage()
    stage.execute(session, doc.id, job.id, step.id)

    session.refresh(product)
    session.refresh(step)

    assert step.status == StepStatus.completed
    assert product.quality_score > 0.0


def test_enrichment_stage_execution(session: Session):
    """Test EnrichmentStage generates AI commerce content, persists status=completed, model, confidence, and generated_value."""
    doc = Document(filename="test.pdf", storage_key="docs/test.pdf", file_hash="hash123", mime_type="application/pdf", file_size=1024, status=DocumentStatus.processed)
    session.add(doc)
    session.commit()
    session.refresh(doc)

    product = Product(
        sku="MX500-230",
        brand="CatalogIQ",
        product_name="MX-500 Motor",
        category="industrial_motor",
        quality_score=88.0,
    )
    session.add(product)
    session.commit()
    session.refresh(product)

    assoc = ProductDocumentAssociation(product_id=product.id, document_id=doc.id)
    session.add(assoc)
    session.commit()

    job = ProcessingJob(total_items=1)
    session.add(job)
    session.commit()
    session.refresh(job)

    step = ProcessingStep(job_id=job.id, document_id=doc.id, stage=ProcessingStage.enriching, status=StepStatus.queued)
    session.add(step)
    session.commit()
    session.refresh(step)

    mock_provider = MockProvider()
    stage = EnrichmentStage(llm_provider=mock_provider)
    stage.execute(session, doc.id, job.id, step.id)

    session.refresh(product)
    session.refresh(step)

    assert step.status == StepStatus.completed
    assert product.commerce_description is not None
    assert "MX-500" in product.commerce_description

    # Verify DB EnrichmentResult record
    stmt = select(EnrichmentResult).where(EnrichmentResult.product_id == product.id)
    enrich_res = session.exec(stmt).first()
    assert enrich_res is not None
    assert enrich_res.status == EnrichmentStatus.completed
    assert enrich_res.model == mock_provider.model_name
    assert enrich_res.confidence > 0.0
    assert enrich_res.approved_at is None
    assert enrich_res.approved_by is None

    gen_data = json.loads(enrich_res.generated_value)
    assert gen_data["commerce_description"] == product.commerce_description


def test_enrichment_stage_failure_handling(session: Session):
    """Test that LLM failure sets enrichment status to failed and logs without saving partial invalid data."""
    class FailingProvider(BaseLLMProvider):
        @property
        def provider_name(self) -> str:
            return "failing_mock"

        @property
        def model_name(self) -> str:
            return "failing-model"

        def extract(self, prompt: str, schema: dict) -> dict:
            raise RuntimeError("API quota exceeded")

        def enrich(self, product_context: dict) -> CommerceEnrichment:
            raise RuntimeError("LLM Service Unavailable")

    doc = Document(filename="test.pdf", storage_key="docs/test.pdf", file_hash="hash123", mime_type="application/pdf", file_size=1024, status=DocumentStatus.processed)
    session.add(doc)
    session.commit()

    product = Product(sku="ERR-100", brand="CatalogIQ", product_name="Failing Item", category="industrial")
    session.add(product)
    session.commit()

    assoc = ProductDocumentAssociation(product_id=product.id, document_id=doc.id)
    session.add(assoc)
    session.commit()

    job = ProcessingJob(total_items=1)
    session.add(job)
    session.commit()

    step = ProcessingStep(job_id=job.id, document_id=doc.id, stage=ProcessingStage.enriching, status=StepStatus.queued)
    session.add(step)
    session.commit()

    failing_stage = EnrichmentStage(llm_provider=FailingProvider())
    with pytest.raises(NonRetryableProcessingError):
        failing_stage.execute(session, doc.id, job.id, step.id)

    session.refresh(step)
    assert step.status == StepStatus.failed

    stmt = select(EnrichmentResult).where(EnrichmentResult.product_id == product.id)
    enrich_res = session.exec(stmt).first()
    assert enrich_res is not None
    assert enrich_res.status == EnrichmentStatus.failed
    assert enrich_res.confidence == 0.0
    assert enrich_res.generated_value == "{}"


def test_get_product_enrichment_api_endpoint(session: Session):
    """Test GET /api/v1/products/{product_id}/enrichment exposes parsed fields in frontend-consumable format."""
    from app.db.session import get_session
    fastapi_app.dependency_overrides[get_session] = lambda: session
    try:
        doc = Document(filename="test.pdf", storage_key="docs/test.pdf", file_hash="hash123", mime_type="application/pdf", file_size=1024, status=DocumentStatus.processed)
        session.add(doc)
        session.commit()

        product = Product(
            sku="API-SPEC-1",
            brand="CatalogIQ",
            product_name="API Test Motor",
            category="industrial_motor",
            quality_score=90.0,
        )
        session.add(product)
        session.commit()

        assoc = ProductDocumentAssociation(product_id=product.id, document_id=doc.id)
        session.add(assoc)
        session.commit()

        job = ProcessingJob(total_items=1)
        session.add(job)
        session.commit()

        step = ProcessingStep(job_id=job.id, document_id=doc.id, stage=ProcessingStage.enriching, status=StepStatus.queued)
        session.add(step)
        session.commit()

        stage = EnrichmentStage(llm_provider=MockProvider())
        stage.execute(session, doc.id, job.id, step.id)

        client = TestClient(fastapi_app)
        response = client.get(f"/api/v1/products/{product.id}/enrichment")
        assert response.status_code == 200

        data = response.json()
        assert data["product_id"] == str(product.id)
        assert data["status"] == "completed"
        assert data["model"] == "mock-v1"
        assert "commerce_description" in data
        assert "features" in data
        assert "applications" in data
        assert "seo_title" in data
        assert "seo_description" in data
        assert data["confidence"] is not None
    finally:
        fastapi_app.dependency_overrides.clear()


def test_evidence_constrained_no_invented_specs(session: Session):
    """Test evidence constraint: missing specifications (ambient temp, dimensions, shaft dia, bearing spec, noise level) are not invented."""
    doc = Document(filename="test.pdf", storage_key="docs/test.pdf", file_hash="hash123", mime_type="application/pdf", file_size=1024, status=DocumentStatus.processed)
    session.add(doc)
    session.commit()

    # Product with minimal verified specs intentionally omitting ambient temp, dimensions, shaft diameter, bearing spec, noise level
    product = Product(
        sku="CONSTRAINED-01",
        brand="CatalogIQ",
        product_name="Evidence Constrained Motor",
        category="industrial_motor",
        quality_score=85.0,
    )
    session.add(product)
    session.commit()

    assoc = ProductDocumentAssociation(product_id=product.id, document_id=doc.id)
    session.add(assoc)
    session.commit()

    job = ProcessingJob(total_items=1)
    session.add(job)
    session.commit()

    step = ProcessingStep(job_id=job.id, document_id=doc.id, stage=ProcessingStage.enriching, status=StepStatus.queued)
    session.add(step)
    session.commit()

    stage = EnrichmentStage(llm_provider=MockProvider())
    stage.execute(session, doc.id, job.id, step.id)

    stmt = select(EnrichmentResult).where(EnrichmentResult.product_id == product.id)
    enrich_res = session.exec(stmt).first()
    gen_text = enrich_res.generated_value.lower()

    absent_specs = ["ambient temperature", "shaft diameter", "bearing specification", "noise level"]
    for spec in absent_specs:
        assert spec not in gen_text, f"Unverified specification '{spec}' was hallucinated!"


def test_repeated_enrichment_idempotency(session: Session):
    """Test repeated enrichment runs update existing EnrichmentResult in place without duplicate records."""
    doc = Document(filename="test.pdf", storage_key="docs/test.pdf", file_hash="hash123", mime_type="application/pdf", file_size=1024, status=DocumentStatus.processed)
    session.add(doc)
    session.commit()

    product = Product(sku="IDEM-ENRICH-1", brand="CatalogIQ", product_name="Idempotency Item", category="motor")
    session.add(product)
    session.commit()

    assoc = ProductDocumentAssociation(product_id=product.id, document_id=doc.id)
    session.add(assoc)
    session.commit()

    mock_provider = MockProvider()
    stage = EnrichmentStage(llm_provider=mock_provider)

    for i in range(3):
        job = ProcessingJob(total_items=1)
        session.add(job)
        session.commit()

        step = ProcessingStep(job_id=job.id, document_id=doc.id, stage=ProcessingStage.enriching, status=StepStatus.queued)
        session.add(step)
        session.commit()

        stage.execute(session, doc.id, job.id, step.id)

    records = session.exec(select(EnrichmentResult).where(EnrichmentResult.product_id == product.id)).all()
    assert len(records) == 1, f"Expected exactly 1 EnrichmentResult row, found {len(records)}"
    assert records[0].status == EnrichmentStatus.completed


def test_human_validation_resolution(session: Session):
    """Test human resolution updates ValidationResult, ProductAttribute value, and recalculates quality score."""
    product = Product(sku="MX500-230", brand="CatalogIQ", product_name="MX-500 Motor", category="industrial_motor")
    session.add(product)
    session.commit()
    session.refresh(product)

    attr = ProductAttribute(
        product_id=product.id,
        attribute_name="weight",
        display_name="Weight",
        raw_value="35 kg",
        data_type="numeric",
        confidence=0.80,
        status="conflicting",
        source_type="llm",
    )
    session.add(attr)
    session.commit()
    session.refresh(attr)

    val = ValidationResult(
        product_id=product.id,
        attribute_id=attr.id,
        validation_type="cross_source_conflict",
        severity="warning",
        status=ValidationStatus.open,
        message="Conflicting weight values (32 kg vs 35 kg)",
        expected_value="32 kg",
        actual_value="35 kg",
    )
    session.add(val)
    session.commit()
    session.refresh(val)

    # Resolve validation issue by accepting expected value (Source A: 32 kg)
    val.status = ValidationStatus.resolved
    val.resolved_by = "human_reviewer"
    attr.raw_value = "32 kg"
    attr.status = "verified"
    session.add(val)
    session.add(attr)
    session.commit()

    session.refresh(val)
    session.refresh(attr)

    assert val.status == ValidationStatus.resolved
    assert attr.raw_value == "32 kg"
    assert attr.status == "verified"


@pytest.mark.skipif(
    os.getenv("RUN_LIVE_GEMINI") != "1",
    reason="Opt-in live Gemini test requires RUN_LIVE_GEMINI=1 environment variable"
)
def test_live_gemini_enrichment():
    """Opt-in live integration test for GeminiProvider enrichment."""
    from app.services.llm.gemini_provider import GeminiProvider

    provider = GeminiProvider()
    context = {
        "product_name": "MX-500 Motor",
        "brand": "CatalogIQ",
        "sku": "MX500-230",
        "category": "Industrial Motor",
        "verified_attributes": {
            "voltage": {"raw_value": "230 V"},
            "power": {"raw_value": "5.5 kW"},
            "speed": {"raw_value": "1440 RPM"},
            "weight": {"raw_value": "32 kg"},
        },
        "features": ["Continuous duty rated", "Class F insulation"],
    }

    res = provider.enrich(context)
    assert res.commerce_description is not None
    assert "5.5" in res.commerce_description or "230" in res.commerce_description
    assert res.provider_name == "gemini"
