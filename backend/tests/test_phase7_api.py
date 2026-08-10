"""
Phase 7 Task 7.3 Test Suite — Multi-Source Reconciliation & Sources REST APIs.

Tests:
  - GET /api/v1/products/{id}/reconciliation returns 200 for valid product
  - GET /api/v1/products/{id}/reconciliation returns 404 for invalid product UUID
  - GET /api/v1/products/{id}/sources returns 200 for valid product
  - GET /api/v1/products/{id}/sources returns 404 for invalid product UUID
  - Multiple sources appear in reconciliation response
  - Source trust levels and evidence provenance exposed in API
  - AGREEMENT status correctly returned by API
  - EQUIVALENT status correctly returned by API
  - CONFLICTING status preserves all competing claims in API
  - MISSING status attributes do not become conflicts in API
  - API call is read-only / idempotent and does not mutate product data unnecessarily
"""
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.db.session import get_session
from app.main import app
from app.models import (
    Product,
    ProductAttribute,
    AttributeEvidence,
    Source,
    SourceType,
    AttributeDataType,
)


@pytest.fixture(autouse=True)
def reset_overrides():
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def test_get_product_reconciliation_404(session: Session):
    """Test 2: Non-existent product ID returns 404 for reconciliation endpoint."""
    def override_get_session():
        yield session

    app.dependency_overrides[get_session] = override_get_session
    try:
        client = TestClient(app)
        fake_id = uuid.uuid4()
        response = client.get(f"/api/v1/products/{fake_id}/reconciliation")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    finally:
        app.dependency_overrides.clear()


def test_get_product_sources_404(session: Session):
    """Test 4: Non-existent product ID returns 404 for sources endpoint."""
    def override_get_session():
        yield session

    app.dependency_overrides[get_session] = override_get_session
    try:
        client = TestClient(app)
        fake_id = uuid.uuid4()
        response = client.get(f"/api/v1/products/{fake_id}/sources")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    finally:
        app.dependency_overrides.clear()


def test_get_product_reconciliation_200_and_agreement(session: Session):
    """Test 1, 8, 12: Valid product returns 200 with AGREEMENT representation."""
    def override_get_session():
        yield session

    app.dependency_overrides[get_session] = override_get_session
    try:
        client = TestClient(app)

        product = Product(sku="API-REC-01", brand="BrandAPI", product_name="API Motor 1", category="Motors")
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

        s1 = Source(name="Datasheet PDF", source_type=SourceType.document, trust_level=0.95)
        s2 = Source(name="Manufacturer Website", source_type=SourceType.manufacturer_website, trust_level=0.90)
        session.add(s1)
        session.add(s2)
        session.commit()

        ev1 = AttributeEvidence(attribute_id=attr.id, source_id=s1.id, evidence_text="11 kW")
        ev2 = AttributeEvidence(attribute_id=attr.id, source_id=s2.id, evidence_text="11 kW")
        session.add(ev1)
        session.add(ev2)
        session.commit()

        res = client.get(f"/api/v1/products/{product.id}/reconciliation")
        assert res.status_code == 200
        data = res.json()

        assert data["product_id"] == str(product.id)
        assert data["agreements_count"] == 1
        assert "rated_power" in data["reconciled_attributes"]

        pow_rec = data["reconciled_attributes"]["rated_power"]
        assert pow_rec["status"] == "AGREEMENT"
        assert pow_rec["winning_source_name"] == "Datasheet PDF"
        assert pow_rec["winning_source_trust"] == 0.95
        assert len(pow_rec["claims"]) == 2
    finally:
        app.dependency_overrides.clear()


def test_get_product_reconciliation_equivalent(session: Session):
    """Test 9: EQUIVALENT status correctly represented in API response."""
    def override_get_session():
        yield session

    app.dependency_overrides[get_session] = override_get_session
    try:
        client = TestClient(app)

        product = Product(sku="API-REC-02", brand="BrandAPI", product_name="API Motor 2", category="Motors")
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

        s1 = Source(name="PDF Spec Sheet", source_type=SourceType.document, trust_level=0.95)
        s2 = Source(name="Distributor Catalog W", source_type=SourceType.catalog, trust_level=0.80)
        session.add(s1)
        session.add(s2)
        session.commit()

        ev1 = AttributeEvidence(attribute_id=attr.id, source_id=s1.id, evidence_text="11 kW")
        ev2 = AttributeEvidence(attribute_id=attr.id, source_id=s2.id, evidence_text="11000 W")
        session.add(ev1)
        session.add(ev2)
        session.commit()

        res = client.get(f"/api/v1/products/{product.id}/reconciliation")
        assert res.status_code == 200
        data = res.json()

        pow_rec = data["reconciled_attributes"]["rated_power"]
        assert pow_rec["status"] == "EQUIVALENT"
        assert data["equivalents_count"] == 1
    finally:
        app.dependency_overrides.clear()


def test_get_product_reconciliation_conflicting(session: Session):
    """Test 5, 6, 7, 10: CONFLICTING status preserves all competing claims, trust levels, and evidence in API."""
    def override_get_session():
        yield session

    app.dependency_overrides[get_session] = override_get_session
    try:
        client = TestClient(app)

        product = Product(sku="API-REC-03", brand="BrandAPI", product_name="API Motor 3", category="Motors")
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
        s2 = Source(name="Distributor Site", source_type=SourceType.catalog, trust_level=0.70)
        session.add(s1)
        session.add(s2)
        session.commit()

        ev1 = AttributeEvidence(attribute_id=attr.id, source_id=s1.id, evidence_text="11 kW")
        ev2 = AttributeEvidence(attribute_id=attr.id, source_id=s2.id, evidence_text="7.5 kW")
        session.add(ev1)
        session.add(ev2)
        session.commit()

        res = client.get(f"/api/v1/products/{product.id}/reconciliation")
        assert res.status_code == 200
        data = res.json()

        assert data["conflicts_count"] == 1
        pow_rec = data["reconciled_attributes"]["rated_power"]
        assert pow_rec["status"] == "CONFLICTING"
        assert pow_rec["winning_source_name"] == "Manufacturer PDF"
        assert pow_rec["winning_source_trust"] == 0.95

        # Verify competing claims preserved in API response
        assert len(pow_rec["competing_claims"]) == 1
        competing = pow_rec["competing_claims"][0]
        assert competing["source_name"] == "Distributor Site"
        assert competing["trust_level"] == 0.70
        assert competing["raw_value"] == "7.5 kW"
    finally:
        app.dependency_overrides.clear()


def test_get_product_reconciliation_missing_is_not_conflict(session: Session):
    """Test 11: Attributes unmentioned in additional sources remain MISSING (non-conflicting)."""
    def override_get_session():
        yield session

    app.dependency_overrides[get_session] = override_get_session
    try:
        client = TestClient(app)

        product = Product(sku="API-REC-04", brand="BrandAPI", product_name="API Motor 4", category="Motors")
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

        s1 = Source(name="Manufacturer Website", source_type=SourceType.manufacturer_website, trust_level=0.90)
        session.add(s1)
        session.commit()

        ev1 = AttributeEvidence(attribute_id=attr.id, source_id=s1.id, evidence_text="IP Rating: IP55")
        session.add(ev1)
        session.commit()

        res = client.get(f"/api/v1/products/{product.id}/reconciliation")
        assert res.status_code == 200
        data = res.json()

        assert data["conflicts_count"] == 0
        assert data["missing_count"] == 1
        assert data["reconciled_attributes"]["ip_rating"]["status"] == "MISSING"
    finally:
        app.dependency_overrides.clear()


def test_get_product_sources_200(session: Session):
    """Test 3, 5, 6: GET /api/v1/products/{id}/sources returns 200 with associated sources and trust levels."""
    def override_get_session():
        yield session

    app.dependency_overrides[get_session] = override_get_session
    try:
        client = TestClient(app)

        product = Product(sku="API-REC-05", brand="BrandAPI", product_name="API Motor 5", category="Motors")
        session.add(product)
        session.commit()

        attr = ProductAttribute(
            product_id=product.id,
            attribute_name="voltage",
            display_name="Voltage",
            raw_value="400 V",
            data_type=AttributeDataType.numeric,
            source_type="llm",
        )
        session.add(attr)
        session.commit()

        s1 = Source(name="Manual PDF", source_type=SourceType.document, trust_level=0.95, uri="s3://manual.pdf")
        s2 = Source(name="Vendor Website", source_type=SourceType.manufacturer_website, trust_level=0.85, uri="https://vendor.com")
        session.add(s1)
        session.add(s2)
        session.commit()

        ev1 = AttributeEvidence(attribute_id=attr.id, source_id=s1.id, evidence_text="400 V")
        ev2 = AttributeEvidence(attribute_id=attr.id, source_id=s2.id, evidence_text="400 V")
        session.add(ev1)
        session.add(ev2)
        session.commit()

        res = client.get(f"/api/v1/products/{product.id}/sources")
        assert res.status_code == 200
        sources = res.json()

        assert len(sources) == 2
        # Verify sorted by trust_level descending
        assert sources[0]["source_name"] == "Manual PDF"
        assert sources[0]["trust_level"] == 0.95
        assert sources[1]["source_name"] == "Vendor Website"
        assert sources[1]["trust_level"] == 0.85
    finally:
        app.dependency_overrides.clear()
