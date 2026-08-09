import uuid
import json
import pytest
from sqlmodel import Session, create_engine, SQLModel
from app.models import Product, EnrichmentResult, EnrichmentStatus, ProcessingJob, ProcessingStep, ProcessingStage, StepStatus, ProductDocumentAssociation, Document, DocumentStatus
from app.services.pipeline import EnrichmentStage
from app.services.llm.mock_provider import MockProvider
from app.api.v1.products import get_product_enrichment

def test_manual_verification_product_c1b3c3eb():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)

    product_id = uuid.UUID("c1b3c3eb-f7e8-4ba5-b1ec-d27518b03c38")

    with Session(engine) as session:
        # Create doc & product with exact ID from prompt
        doc = Document(filename="CQ_X120_Datasheet.pdf", storage_key="docs/cq.pdf", file_hash="hashcq123", mime_type="application/pdf", file_size=1024, status=DocumentStatus.processed)
        session.add(doc)
        session.commit()

        product = Product(
            id=product_id,
            sku="CQ-X120-230",
            brand="CatalogIQ",
            product_name="Synthetic Industrial Motor",
            category="industrial_motor",
            quality_score=88.0,
        )
        session.add(product)
        session.commit()

        assoc = ProductDocumentAssociation(product_id=product_id, document_id=doc.id)
        session.add(assoc)
        session.commit()

        job = ProcessingJob(total_items=1)
        session.add(job)
        session.commit()

        step = ProcessingStep(job_id=job.id, document_id=doc.id, stage=ProcessingStage.enriching, status=StepStatus.queued)
        session.add(step)
        session.commit()

        # Run EnrichmentStage
        stage = EnrichmentStage(llm_provider=MockProvider())
        stage.execute(session, doc.id, job.id, step.id)

        session.refresh(product)

        # Query GET /api/v1/products/{product_id}/enrichment output
        res = get_product_enrichment(product_id, session)

        print("\n=== MANUAL VERIFICATION OUTPUT FOR PRODUCT c1b3c3eb-f7e8-4ba5-b1ec-d27518b03c38 ===")
        print(json.dumps(res, indent=2))

        # 1. Check status is completed
        assert res["status"] == "completed"
        # 2. Check generated_value present
        assert res["generated_value"] is not None
        # 3. Check model & confidence
        assert res["model"] == "mock-v1"
        assert res["confidence"] is not None
        # 4. Check parsed fields exposed
        assert res["commerce_description"] is not None
        assert len(res["features"]) > 0
        assert len(res["applications"]) > 0
        # 5. Check evidence-constrained missing specs
        gen_text = res["generated_value"].lower()
        absent_specs = ["ambient temperature", "shaft diameter", "bearing specification", "noise level"]
        for spec in absent_specs:
            assert spec not in gen_text

        print("=== VERIFICATION PASSED PERFECTLY ===")
