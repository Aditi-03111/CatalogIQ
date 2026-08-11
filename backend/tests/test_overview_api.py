import uuid
from fastapi.testclient import TestClient
from sqlmodel import Session
import pytest

from app.main import app
from app.db.session import get_session
from app.models import (
    Product,
    ProductStatus,
    Document,
    DocumentStatus,
    ProcessingJob,
    JobStatus,
    ProductAttribute,
    AttributeDataType,
    AttributeStatus,
    ValidationResult,
    ValidationType,
    ValidationSeverity,
    ValidationStatus,
)

client = TestClient(app)


def test_overview_summary_empty_db(session: Session):
    """
    Verifies /api/v1/overview/summary returns correct empty aggregate values
    when no products or documents exist.
    """
    def get_session_override():
        yield session

    app.dependency_overrides[get_session] = get_session_override
    try:
        response = client.get("/api/v1/overview/summary")
        assert response.status_code == 200
        data = response.json()

        assert "kpis" in data
        assert data["kpis"]["total_products"] == 0
        assert data["kpis"]["documents_processed"] == 0
        assert data["kpis"]["total_documents"] == 0
        assert data["kpis"]["active_processing_jobs"] == 0
        assert data["kpis"]["review_backlog"] == 0
        assert data["kpis"]["catalog_quality_score"] is None
        assert data["kpis"]["verification_rate"] is None

        assert data["processing_activity"] == []
        assert data["review_summary"]["unresolved_validation_issues"] == 0
        assert data["review_summary"]["conflicts_count"] == 0
        assert data["recent_products"] == []
    finally:
        app.dependency_overrides.clear()


def test_overview_summary_populated_db(session: Session):
    """
    Verifies /api/v1/overview/summary aggregates real database entities correctly.
    """
    # Create products
    p1 = Product(
        sku="TEST-SKU-001",
        brand="Siemens",
        product_name="Siemens Motor 500W",
        category="Motors",
        status=ProductStatus.verified,
        quality_score=95.0,
    )
    p2 = Product(
        sku="TEST-SKU-002",
        brand="ABB",
        product_name="ABB Inverter 100",
        category="Drive",
        status=ProductStatus.needs_review,
        quality_score=60.0,
    )
    session.add(p1)
    session.add(p2)
    session.commit()
    session.refresh(p1)
    session.refresh(p2)

    # Create document
    doc = Document(
        filename="datasheet_motor.pdf",
        storage_backend="local",
        storage_key="docs/datasheet_motor.pdf",
        file_hash="hash123",
        mime_type="application/pdf",
        file_size=1024,
        page_count=4,
        status=DocumentStatus.processed,
    )
    session.add(doc)

    # Create job
    job = ProcessingJob(
        total_items=1,
        completed_items=0,
        status=JobStatus.processing,
        current_stage="extracting",
    )
    session.add(job)

    # Create validation conflict result
    val_issue = ValidationResult(
        product_id=p2.id,
        validation_type=ValidationType.cross_attribute_conflict,
        severity=ValidationSeverity.warning,
        status=ValidationStatus.open,
        message="Voltage conflict between source A and source B",
    )
    session.add(val_issue)
    session.commit()

    def get_session_override():
        yield session

    app.dependency_overrides[get_session] = get_session_override
    try:
        response = client.get("/api/v1/overview/summary")
        assert response.status_code == 200
        data = response.json()

        kpis = data["kpis"]
        assert kpis["total_products"] == 2
        assert kpis["documents_processed"] == 1
        assert kpis["total_documents"] == 1
        assert kpis["active_processing_jobs"] == 1
        assert kpis["review_backlog"] == 1  # 1 product with needs_review
        assert kpis["catalog_quality_score"] == 77.5  # (95 + 60) / 2
        assert kpis["verification_rate"] == 50.0  # 1 verified / 2 total * 100

        # Processing Activity
        assert len(data["processing_activity"]) == 1
        assert data["processing_activity"][0]["filename"] == "datasheet_motor.pdf"
        assert data["processing_activity"][0]["status"] == "processed"
        assert data["processing_activity"][0]["page_count"] == 4

        # Review Summary
        assert data["review_summary"]["unresolved_validation_issues"] == 1
        assert data["review_summary"]["conflicts_count"] == 1
        assert data["review_summary"]["products_needing_review"] == 1

        # Catalog Quality Summary
        assert data["catalog_quality_summary"]["verified_products_count"] == 1
        assert data["catalog_quality_summary"]["needs_review_products_count"] == 1
        assert data["catalog_quality_summary"]["products_needing_attention"] == 1

        # Recent Products
        assert len(data["recent_products"]) == 2
    finally:
        app.dependency_overrides.clear()
