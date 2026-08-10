"""
Phase 7 Task 7.4 Test Suite — Integration & Test Hardening.

Coverage:
  1. Full end-to-end multi-source pipeline (Source Registration -> Entity Resolution -> Association -> Reconciliation -> Validation -> API -> Qdrant Indexing)
  2. Entity Resolution & Merge Prevention integration rules
  3. Realistic Multi-Source Scenarios (Agreement, SI-Equivalence, Missing/Non-conflicting, Genuine Conflict)
  4. Human-Review Boundary & Resolution Provenance preservation
  5. 3x Consecutive Execution Idempotency & DB state deduplication
  6. Phase 6 Qdrant indexing integration & error isolation
  7. API Integration (reconciliation matrix, sources listing, error codes, read-only guarantees)
"""
import uuid
import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.db.session import get_session
from app.main import app as fastapi_app
from app.models import (
    Product,
    ProductAttribute,
    AttributeEvidence,
    Source,
    SourceType,
    AttributeDataType,
    AttributeStatus,
    ProductDocumentAssociation,
    ValidationResult,
    ValidationType,
    ValidationStatus,
    Document,
    DocumentStatus,
)
from app.services.entity_resolution import EntityResolutionService
from app.services.reconciler import MultiSourceReconciler, ReconciliationStatus
from app.services.indexing import IndexingService
from app.services.embeddings.mock_provider import MockEmbeddingProvider


@pytest.fixture
def mock_qdrant_service():
    """Mock Qdrant service for Phase 6 semantic search integration tests."""
    mock = MagicMock()
    mock.collection_name = "catalogiq_products_test"
    mock.ensure_collection_exists.return_value = True
    mock.upsert_product_vector.return_value = True
    mock.search_similar_products.return_value = []
    return mock


def test_full_multi_source_pipeline_end_to_end(session: Session, mock_qdrant_service):
    """Test 1: Full pipeline execution from Source Registration -> Entity Resolution -> Reconciliation -> Qdrant."""
    # 1. Existing Base Product in Catalog
    existing_product = Product(
        sku="M3BP-160-4A",
        brand="ABB",
        product_name="ABB Industrial Motor M3BP 160",
        category="Motors",
    )
    session.add(existing_product)
    session.commit()

    base_attr = ProductAttribute(
        product_id=existing_product.id,
        attribute_name="rated_power",
        display_name="Rated Power",
        raw_value="11 kW",
        unit="kW",
        data_type=AttributeDataType.numeric,
        source_type="llm",
    )
    session.add(base_attr)
    session.commit()

    # 2. Incoming Extracted Datasheet Source (Level 1 Match: Exact SKU + Brand)
    resolution_service = EntityResolutionService(session)
    match_res = resolution_service.resolve_product(
        {"sku": "M3BP-160-4A", "brand": "ABB", "product_name": "ABB Motor M3BP 160kW"},
        enable_semantic_search=False,
    )
    assert match_res.is_exact_match is True
    assert match_res.match_level == "exact_sku_brand"
    assert match_res.matched_product_id == str(existing_product.id)

    # 3. Register Sources & Link Document Associations
    doc = Document(
        filename="abb_m3bp_160.pdf",
        storage_key="docs/abb_m3bp_160.pdf",
        file_hash="hash_m3bp_160",
        mime_type="application/pdf",
        file_size=2048576,
        status=DocumentStatus.processed,
    )
    session.add(doc)
    session.commit()

    assoc = ProductDocumentAssociation(product_id=existing_product.id, document_id=doc.id)
    session.add(assoc)

    s1 = Source(name="ABB Datasheet PDF", source_type=SourceType.document, trust_level=0.95, document_id=doc.id)
    s2 = Source(name="ABB Official Website", source_type=SourceType.manufacturer_website, trust_level=0.90)
    s3 = Source(name="Distributor Catalog", source_type=SourceType.catalog, trust_level=0.70)
    session.add(s1)
    session.add(s2)
    session.add(s3)
    session.commit()

    # 4. Extract Claims & Evidence (s1=11 kW, s2=11 kW [AGREEMENT], s3=7.5 kW [CONFLICTING])
    ev1 = AttributeEvidence(attribute_id=base_attr.id, source_id=s1.id, document_id=doc.id, page_number=3, evidence_text="11 kW")
    ev2 = AttributeEvidence(attribute_id=base_attr.id, source_id=s2.id, evidence_text="11 kW")
    ev3 = AttributeEvidence(attribute_id=base_attr.id, source_id=s3.id, evidence_text="7.5 kW")
    session.add(ev1)
    session.add(ev2)
    session.add(ev3)
    session.commit()

    # 5. Multi-Source Reconciliation & Validation Conflict Registration
    reconciler = MultiSourceReconciler(session)
    rec_summary = reconciler.reconcile_product(existing_product.id)

    assert rec_summary.total_attributes == 1
    rec_attr = rec_summary.reconciled_attributes["rated_power"]
    assert rec_attr.status == ReconciliationStatus.CONFLICTING
    assert rec_attr.winning_source_name == "ABB Datasheet PDF"
    assert len(rec_attr.claims) == 3

    # 6. Verify ValidationResult created in DB
    val_stmt = select(ValidationResult).where(ValidationResult.product_id == existing_product.id)
    val_results = session.exec(val_stmt).all()
    assert len(val_results) == 1
    assert val_results[0].validation_type == ValidationType.cross_source_conflict

    # 7. Reconciliation API Response Verification
    fastapi_app.dependency_overrides[get_session] = lambda: session
    try:
        client = TestClient(fastapi_app)
        api_res = client.get(f"/api/v1/products/{existing_product.id}/reconciliation")
        assert api_res.status_code == 200
        api_data = api_res.json()
        assert api_data["conflicts_count"] == 1
    finally:
        fastapi_app.dependency_overrides.clear()

    # 8. Qdrant Semantic Re-indexing Integration
    embedding_provider = MockEmbeddingProvider()
    indexing_service = IndexingService(
        session=session,
        embedding_provider=embedding_provider,
        qdrant_service=mock_qdrant_service,
    )
    idx_result = indexing_service.index_product(existing_product.id)

    assert idx_result["status"] == "indexed"
    mock_qdrant_service.upsert_product_vector.assert_called_once()


def test_entity_resolution_rules_and_merge_prevention(session: Session):
    """Test 2: Entity Resolution matching hierarchy & safe candidate generation."""
    p1 = Product(sku="SKU-AAA-100", brand="Siemens", product_name="Siemens Motor A", model="1LA7090", category="Motors")
    session.add(p1)
    session.commit()

    res_service = EntityResolutionService(session)

    # 1. Exact SKU + Brand -> Auto-Match
    r1 = res_service.resolve_product({"sku": "SKU-AAA-100", "brand": "Siemens"}, enable_semantic_search=False)
    assert r1.is_exact_match is True
    assert r1.match_level == "exact_sku_brand"
    assert r1.matched_product_id == str(p1.id)

    # 2. Exact Model + Brand -> Auto-Match
    r2 = res_service.resolve_product({"model": "1LA7090", "brand": "Siemens"}, enable_semantic_search=False)
    assert r2.is_exact_match is True
    assert r2.match_level == "exact_model_brand"
    assert r2.matched_product_id == str(p1.id)

    # 3. Conflicting SKU -> Prevents Merge
    r3 = res_service.resolve_product({"sku": "SKU-DIFFERENT-999", "model": "1LA7090", "brand": "Siemens"}, enable_semantic_search=False)
    assert r3.is_exact_match is False
    assert r3.matched_product_id is None

    # 4. Conflicting Brand -> Prevents Merge
    r4 = res_service.resolve_product({"sku": "SKU-AAA-100", "brand": "WEG"}, enable_semantic_search=False)
    assert r4.is_exact_match is False
    assert r4.matched_product_id is None


def test_realistic_multi_source_scenarios(session: Session):
    """Test 3: AGREEMENT, EQUIVALENT, MISSING, and CONFLICTING classifications across 3 sources."""
    product = Product(sku="MULTI-SRC-01", brand="WEG", product_name="WEG W22 Motor", category="Motors")
    session.add(product)
    session.commit()

    # Attributes
    a_power = ProductAttribute(product_id=product.id, attribute_name="power", display_name="Power", raw_value="11 kW", unit="kW", data_type=AttributeDataType.numeric, source_type="llm")
    a_freq = ProductAttribute(product_id=product.id, attribute_name="frequency", display_name="Frequency", raw_value="50 Hz", unit="Hz", data_type=AttributeDataType.numeric, source_type="llm")
    a_ip = ProductAttribute(product_id=product.id, attribute_name="ip_rating", display_name="IP Rating", raw_value="IP55", data_type=AttributeDataType.text, source_type="llm")
    a_voltage = ProductAttribute(product_id=product.id, attribute_name="voltage", display_name="Voltage", raw_value="400 V", unit="V", data_type=AttributeDataType.numeric, source_type="llm")

    session.add(a_power)
    session.add(a_freq)
    session.add(a_ip)
    session.add(a_voltage)
    session.commit()

    s_pdf = Source(name="Manufacturer PDF", source_type=SourceType.document, trust_level=0.95)
    s_web = Source(name="Manufacturer Website", source_type=SourceType.manufacturer_website, trust_level=0.90)
    s_dist = Source(name="Distributor Catalog", source_type=SourceType.catalog, trust_level=0.70)
    session.add(s_pdf)
    session.add(s_web)
    session.add(s_dist)
    session.commit()

    # a_power: s_pdf=11 kW, s_dist=7.5 kW -> CONFLICTING
    session.add(AttributeEvidence(attribute_id=a_power.id, source_id=s_pdf.id, evidence_text="11 kW"))
    session.add(AttributeEvidence(attribute_id=a_power.id, source_id=s_dist.id, evidence_text="7.5 kW"))

    # a_freq: s_pdf=50 Hz, s_web=50 Hz -> AGREEMENT
    session.add(AttributeEvidence(attribute_id=a_freq.id, source_id=s_pdf.id, evidence_text="50 Hz"))
    session.add(AttributeEvidence(attribute_id=a_freq.id, source_id=s_web.id, evidence_text="50 Hz"))

    # a_voltage: s_pdf=0.4 kV, s_web=400 V -> EQUIVALENT
    session.add(AttributeEvidence(attribute_id=a_voltage.id, source_id=s_pdf.id, evidence_text="0.4 kV"))
    session.add(AttributeEvidence(attribute_id=a_voltage.id, source_id=s_web.id, evidence_text="400 V"))

    # a_ip: s_pdf=IP55 (s_web & s_dist missing) -> MISSING / NON-CONFLICTING
    session.add(AttributeEvidence(attribute_id=a_ip.id, source_id=s_pdf.id, evidence_text="IP55"))

    session.commit()

    reconciler = MultiSourceReconciler(session)
    summary = reconciler.reconcile_product(product.id)

    assert summary.agreements_count == 1
    assert summary.equivalents_count == 1
    assert summary.missing_count == 1
    assert summary.conflicts_count == 1

    assert summary.reconciled_attributes["frequency"].status == ReconciliationStatus.AGREEMENT
    assert summary.reconciled_attributes["voltage"].status == ReconciliationStatus.EQUIVALENT
    assert summary.reconciled_attributes["ip_rating"].status == ReconciliationStatus.MISSING
    assert summary.reconciled_attributes["power"].status == ReconciliationStatus.CONFLICTING


def test_human_review_boundary_and_conflict_resolution(session: Session):
    """Test 4: Human-review boundary preservation and resolution flow."""
    product = Product(sku="HR-BOUND-01", brand="Schneider", product_name="Schneider Breaker", category="Breakers")
    session.add(product)
    session.commit()

    attr = ProductAttribute(
        product_id=product.id,
        attribute_name="current_rating",
        display_name="Current Rating",
        raw_value="16 A",
        unit="A",
        data_type=AttributeDataType.numeric,
        source_type="llm",
    )
    session.add(attr)
    session.commit()

    s1 = Source(name="Factory Spec Sheet", source_type=SourceType.document, trust_level=0.95)
    s2 = Source(name="Vendor Website", source_type=SourceType.catalog, trust_level=0.75)
    session.add(s1)
    session.add(s2)
    session.commit()

    ev1 = AttributeEvidence(attribute_id=attr.id, source_id=s1.id, evidence_text="16 A")
    ev2 = AttributeEvidence(attribute_id=attr.id, source_id=s2.id, evidence_text="32 A")
    session.add(ev1)
    session.add(ev2)
    session.commit()

    # Reconcile -> creates open ValidationResult for conflict
    reconciler = MultiSourceReconciler(session)
    reconciler.reconcile_product(product.id)

    val_stmt = select(ValidationResult).where(
        ValidationResult.product_id == product.id,
        ValidationResult.validation_type == ValidationType.cross_source_conflict,
        ValidationResult.status == ValidationStatus.open,
    )
    open_val = session.exec(val_stmt).first()
    assert open_val is not None
    assert open_val.actual_value[0]["raw_value"] == "32 A"

    # Human resolves conflict via API endpoint
    fastapi_app.dependency_overrides[get_session] = lambda: session
    try:
        client = TestClient(fastapi_app)
        resolve_payload = {
            "resolution": "custom",
            "resolved_value": "32 A",
            "notes": "Verified against vendor physical plate photo",
        }
        res = client.post(
            f"/api/v1/products/{product.id}/validation/{open_val.id}/resolve",
            json=resolve_payload,
        )
        assert res.status_code == 200
        res_data = res.json()
        assert res_data["status"] == "resolved"

        # Verify canonical ProductAttribute raw_value was updated to resolved value 32 A
        updated_attr = session.get(ProductAttribute, attr.id)
        assert updated_attr.raw_value == "32 A"

        # Verify historical evidence provenance entries (16 A and 32 A) remain intact in DB
        ev_all = session.exec(select(AttributeEvidence).where(AttributeEvidence.attribute_id == attr.id)).all()
        assert len(ev_all) == 2
    finally:
        fastapi_app.dependency_overrides.clear()


def test_pipeline_idempotency_3x_runs(session: Session):
    """Test 5: Running the reconciliation pipeline 3 consecutive times produces 0 duplicate records."""
    product = Product(sku="IDEM-3X-01", brand="Danfoss", product_name="Danfoss VFD Drive", category="Drives")
    session.add(product)
    session.commit()

    attr = ProductAttribute(
        product_id=product.id,
        attribute_name="output_current",
        display_name="Output Current",
        raw_value="24 A",
        unit="A",
        data_type=AttributeDataType.numeric,
        source_type="llm",
    )
    session.add(attr)
    session.commit()

    s1 = Source(name="Manual A", source_type=SourceType.document, trust_level=0.95)
    s2 = Source(name="Manual B", source_type=SourceType.catalog, trust_level=0.70)
    session.add(s1)
    session.add(s2)
    session.commit()

    ev1 = AttributeEvidence(attribute_id=attr.id, source_id=s1.id, evidence_text="24 A")
    ev2 = AttributeEvidence(attribute_id=attr.id, source_id=s2.id, evidence_text="18 A")
    session.add(ev1)
    session.add(ev2)
    session.commit()

    reconciler = MultiSourceReconciler(session)

    # Execution 1
    r1 = reconciler.reconcile_product(product.id)
    c1 = r1.reconciled_attributes["output_current"].confidence_score
    val_count_1 = len(session.exec(select(ValidationResult).where(ValidationResult.product_id == product.id)).all())

    # Execution 2
    r2 = reconciler.reconcile_product(product.id)
    c2 = r2.reconciled_attributes["output_current"].confidence_score
    val_count_2 = len(session.exec(select(ValidationResult).where(ValidationResult.product_id == product.id)).all())

    # Execution 3
    r3 = reconciler.reconcile_product(product.id)
    c3 = r3.reconciled_attributes["output_current"].confidence_score
    val_count_3 = len(session.exec(select(ValidationResult).where(ValidationResult.product_id == product.id)).all())

    assert c1 == c2 == c3
    assert val_count_1 == 1
    assert val_count_2 == 1
    assert val_count_3 == 1


def test_qdrant_indexing_and_failure_isolation(session: Session):
    """Test 6: PostgreSQL authoritative state is safe even if Qdrant indexing fails."""
    product = Product(
        sku="QDR-ISO-01",
        brand="Eaton",
        product_name="Eaton Circuit Breaker NZM2",
        category="Breakers",
        status=AttributeStatus.verified,
    )
    session.add(product)
    session.commit()

    attr = ProductAttribute(
        product_id=product.id,
        attribute_name="frame_size",
        display_name="Frame Size",
        raw_value="NZM2",
        data_type=AttributeDataType.text,
        source_type="deterministic",
    )
    session.add(attr)
    session.commit()

    # Create failing Qdrant service mock
    failing_qdrant = MagicMock()
    failing_qdrant.upsert_product_vector.side_effect = Exception("Qdrant connection timeout")

    indexing_service = IndexingService(
        session=session,
        embedding_provider=MockEmbeddingProvider(),
        qdrant_service=failing_qdrant,
    )

    with pytest.raises(Exception) as exc_info:
        indexing_service.index_product(product.id)
    assert "timeout" in str(exc_info.value).lower()

    # Confirm PostgreSQL product and attribute records remain completely safe and uncorrupted
    db_prod = session.get(Product, product.id)
    assert db_prod is not None
    assert db_prod.sku == "QDR-ISO-01"
    db_attr = session.get(ProductAttribute, attr.id)
    assert db_attr is not None
    assert db_attr.raw_value == "NZM2"


def test_api_integration_end_to_end_validation(session: Session):
    """Test 7: Verification of API endpoints for reconciliation and sources."""
    product = Product(sku="API-E2E-99", brand="Siemens", product_name="Siemens S7-1500 PLC", category="PLCs")
    session.add(product)
    session.commit()

    attr = ProductAttribute(
        product_id=product.id,
        attribute_name="memory",
        display_name="Memory",
        raw_value="500 KB",
        data_type=AttributeDataType.text,
        source_type="llm",
    )
    session.add(attr)
    session.commit()

    s1 = Source(name="Siemens Manual", source_type=SourceType.document, trust_level=0.95, uri="s3://manual.pdf")
    session.add(s1)
    session.commit()

    ev1 = AttributeEvidence(attribute_id=attr.id, source_id=s1.id, evidence_text="500 KB")
    session.add(ev1)
    session.commit()

    fastapi_app.dependency_overrides[get_session] = lambda: session
    try:
        client = TestClient(fastapi_app)

        # 404 test
        res_404 = client.get(f"/api/v1/products/{uuid.uuid4()}/reconciliation")
        assert res_404.status_code == 404

        # 422 invalid UUID test
        res_422 = client.get("/api/v1/products/invalid-uuid-string/reconciliation")
        assert res_422.status_code == 422

        # Valid product reconciliation GET
        res_rec = client.get(f"/api/v1/products/{product.id}/reconciliation")
        assert res_rec.status_code == 200
        assert res_rec.json()["product_id"] == str(product.id)

        # Valid product sources GET
        res_src = client.get(f"/api/v1/products/{product.id}/sources")
        assert res_src.status_code == 200
        assert len(res_src.json()) >= 1
    finally:
        fastapi_app.dependency_overrides.clear()
