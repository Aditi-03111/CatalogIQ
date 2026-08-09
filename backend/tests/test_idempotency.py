"""
Unit and integration tests for document reprocessing idempotency.
Verifies that reprocessing a document updates existing ProductAttribute records
in place rather than creating duplicate rows.
"""
import json
import uuid
import pytest
from sqlmodel import Session, select
from app.models import Product, ProductAttribute, Document, ProcessingJob, ProcessingStep, ProcessingStage as PStage, StepStatus, JobStatus
from app.services.pipeline import ExtractionStage
from app.services.llm.mock_provider import MockProvider
from app.repositories import AttributeRepository, ProductRepository
from app.services.storage import get_storage_service


def test_reprocessing_idempotency(session: Session):
    """
    Tests idempotency across multiple reprocessing runs of the same document:
    - Test 1 & 2: Row counts match after first and second processing.
    - Test 3: Values remain accurate after reprocessing.
    - Test 4: Row counts remain stable across 3+ reprocessing runs.
    - Test 5: Unrelated product's attributes are completely unaffected.
    """
    mock_provider = MockProvider()
    doc_id = uuid.uuid4()
    content_hash = f"idempotency_hash_{doc_id}"
    parsed_key = f"documents/parsed/{doc_id}.json"

    sample_ir = {
        "content_hash": content_hash,
        "pages": [
            {
                "page_number": 1,
                "text": "Industrial Motor\nModel: MX-500\nSKU: MX500-230\n",
                "tables": [],
                "images": []
            }
        ]
    }

    storage = get_storage_service()
    storage.upload_file(json.dumps(sample_ir).encode("utf-8"), parsed_key)

    # Create Document record to satisfy FK constraints
    document = Document(
        id=doc_id,
        filename="test_datasheet.pdf",
        storage_key=f"documents/original/{doc_id}.pdf",
        file_hash=f"file_hash_{doc_id}",
        content_hash=content_hash,
        mime_type="application/pdf",
        file_size=1024,
        parsed_storage_key=parsed_key,
        parser_name="docling",
        status="processed"
    )
    session.add(document)
    session.commit()

    # 0. Setup an unrelated product with attributes to test isolation (Test 5)
    unrelated_prod = Product(sku="UNRELATED-99", brand="TestBrand", product_name="Unrelated Product", category="Motors")
    session.add(unrelated_prod)
    session.commit()
    unrelated_attr = ProductAttribute(
        product_id=unrelated_prod.id,
        attribute_name="unrelated_spec",
        display_name="Unrelated Spec",
        raw_value="Initial Value",
        normalized_value="Initial Value",
        data_type="text",
        confidence=0.9,
        status="verified",
        source_type="deterministic"
    )
    session.add(unrelated_attr)
    session.commit()

    # 1. RUN 1: First processing of target document
    job1 = ProcessingJob(total_items=1, status=JobStatus.queued, current_stage="extracting")
    session.add(job1)
    session.commit()
    step1 = ProcessingStep(job_id=job1.id, document_id=doc_id, stage=PStage.extracting, status=StepStatus.queued)
    session.add(step1)
    session.commit()

    ext_stage = ExtractionStage(llm_provider=mock_provider)
    ext_stage.execute(session, doc_id, job1.id, step1.id)

    # Find created product
    products = session.exec(select(Product)).all()
    assert len(products) >= 2, f"Expected products created, found {len(products)}"
    # Target product is the one created by ExtractionStage (not unrelated_prod)
    product = [p for p in products if p.id != unrelated_prod.id][0]
    assert product is not None

    attr_repo = AttributeRepository(session)
    attrs1 = attr_repo.list_by_product(product.id)
    count_after_first = len(attrs1)
    assert count_after_first > 0

    # 2. RUN 2: Reprocess the SAME document (Test 2 & Test 3)
    job2 = ProcessingJob(total_items=1, status=JobStatus.queued, current_stage="extracting")
    session.add(job2)
    session.commit()
    step2 = ProcessingStep(job_id=job2.id, document_id=doc_id, stage=PStage.extracting, status=StepStatus.queued)
    session.add(step2)
    session.commit()

    ext_stage.execute(session, doc_id, job2.id, step2.id)

    attrs2 = attr_repo.list_by_product(product.id)
    count_after_second = len(attrs2)

    # ASSERT TEST 2: Row counts must match after 2nd processing
    assert count_after_second == count_after_first, f"Expected {count_after_first} attrs, got {count_after_second}"

    # ASSERT TEST 3: Values are correct after reprocessing
    attr_map2 = {a.attribute_name: a for a in attrs2}
    assert "rated_voltage" in attr_map2
    assert attr_map2["rated_voltage"].raw_value == "230 V"
    assert attr_map2["rated_voltage"].normalized_value == 230

    assert "rated_power" in attr_map2
    assert attr_map2["rated_power"].raw_value == "5.5 kW"
    assert attr_map2["rated_power"].normalized_value == 5.5

    # 3. RUN 3: Reprocess a third time (Test 4)
    job3 = ProcessingJob(total_items=1, status=JobStatus.queued, current_stage="extracting")
    session.add(job3)
    session.commit()
    step3 = ProcessingStep(job_id=job3.id, document_id=doc_id, stage=PStage.extracting, status=StepStatus.queued)
    session.add(step3)
    session.commit()

    ext_stage.execute(session, doc_id, job3.id, step3.id)

    attrs3 = attr_repo.list_by_product(product.id)
    count_after_third = len(attrs3)
    assert count_after_third == count_after_first, f"Expected {count_after_first} attrs after 3rd run, got {count_after_third}"

    # ASSERT TEST 5: Verify unrelated product's attributes are completely unchanged
    unrelated_attrs_after = attr_repo.list_by_product(unrelated_prod.id)
    assert len(unrelated_attrs_after) == 1
    assert unrelated_attrs_after[0].raw_value == "Initial Value"
    assert unrelated_attrs_after[0].id == unrelated_attr.id
