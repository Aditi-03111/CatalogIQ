import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel import Session, select

from app.db.session import get_session
from app.models import (
    AttributeEvidence,
    AuditLog,
    Document,
    EnrichmentResult,
    Product,
    ProductAttribute,
    ProductDocumentAssociation,
    ProductStatus,
    ProductVersion,
    Source,
    SourceType,
    ValidationResult,
    ValidationStatus,
)
from app.repositories import AttributeRepository, ProductRepository
from app.services.product import ProductService
from app.services.reconciler import MultiSourceReconciler
from app.services.validation_engine import ValidationEngine

router = APIRouter(prefix="/products")


class SourceClaimSchema(BaseModel):
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


class AttributeReconciliationSchema(BaseModel):
    attribute_name: str
    display_name: str
    canonical_value: Optional[str] = None
    canonical_unit: Optional[str] = None
    canonical_normalized_value: Optional[Any] = None
    status: str
    confidence_score: float
    winning_source_name: Optional[str] = None
    winning_source_trust: Optional[float] = None
    claims: List[SourceClaimSchema] = []
    competing_claims: List[SourceClaimSchema] = []
    explanation: str = ""


class ProductReconciliationResponse(BaseModel):
    product_id: str
    product_name: str
    total_attributes: int = 0
    agreements_count: int = 0
    equivalents_count: int = 0
    missing_count: int = 0
    conflicts_count: int = 0
    review_count: int = 0
    overall_confidence: float = 1.0
    reconciled_attributes: Dict[str, AttributeReconciliationSchema] = {}


class ProductSourceResponse(BaseModel):
    source_id: str
    source_name: str
    source_type: str
    uri: Optional[str] = None
    trust_level: float = 1.0
    document_id: Optional[str] = None
    metadata_json: Dict[str, Any] = {}
    created_at: datetime
    association_type: str = "document_source"


class ResolutionRequest(BaseModel):
    resolution: str  # "accept_source_a" | "accept_source_b" | "custom_value"
    resolved_value: Optional[Any] = None
    notes: Optional[str] = None


@router.get("/", response_model=List[Product])
def list_products(
    limit: int = 100,
    offset: int = 0,
    status: Optional[str] = None,
    brand: Optional[str] = None,
    category: Optional[str] = None,
    quality_score_min: Optional[float] = None,
    quality_score_max: Optional[float] = None,
    session: Session = Depends(get_session),
):
    repo = ProductRepository(session)
    return repo.list_products(
        limit=limit,
        offset=offset,
        status=status,
        brand=brand,
        category=category,
        quality_score_min=quality_score_min,
        quality_score_max=quality_score_max,
    )


@router.get("/{product_id}", response_model=Product)
def get_product(product_id: uuid.UUID, session: Session = Depends(get_session)):
    repo = ProductRepository(session)
    product = repo.get_by_id(product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID {product_id} not found",
        )

    attributes = repo.get_attributes(product_id)
    formatted_attributes = {}
    for attr in attributes:
        val = attr.normalized_value if attr.normalized_value is not None else attr.raw_value
        formatted_attributes[attr.attribute_name] = {
            "value": val,
            "unit": attr.unit,
            "raw_value": attr.raw_value,
            "display_name": attr.display_name,
            "data_type": attr.data_type.value if hasattr(attr.data_type, "value") else str(attr.data_type),
            "confidence": attr.confidence,
            "status": attr.status.value if hasattr(attr.status, "value") else str(attr.status),
            "source_type": attr.source_type,
        }

    product_dict = product.model_dump()
    product_dict["attributes"] = formatted_attributes
    return product_dict


@router.get("/{product_id}/attributes", response_model=List[ProductAttribute])
def get_product_attributes(product_id: uuid.UUID, session: Session = Depends(get_session)):
    repo = ProductRepository(session)
    if not repo.get_by_id(product_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID {product_id} not found",
        )
    return repo.get_attributes(product_id)


@router.get("/{product_id}/validation")
def get_product_validation_summary(product_id: uuid.UUID, session: Session = Depends(get_session)):
    """
    Returns comprehensive validation summary including quality score,
    completeness, open validation issues, and conflict status.
    """
    repo = ProductRepository(session)
    product = repo.get_by_id(product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID {product_id} not found",
        )

    validations = repo.get_validations(product_id)
    attributes = repo.get_attributes(product_id)
    attr_repo = AttributeRepository(session)
    evidence = attr_repo.get_evidence_for_product(product_id)

    evidence_names = {
        a.attribute_name for a in attributes
        if any(e.attribute_id == a.id and e.evidence_text for e in evidence)
    }

    engine = ValidationEngine()
    val_res = engine.validate_product(
        product=product,
        attributes=attributes,
        evidence_supported_attribute_names=evidence_names,
    )

    return {
        "product_id": str(product_id),
        "quality_score": product.quality_score,
        "validation_status": product.status,
        "completeness_score": val_res.completeness.completeness_score,
        "completeness_details": val_res.completeness.model_dump(),
        "quality_breakdown": val_res.quality_breakdown.model_dump(),
        "issues": [v.model_dump() for v in validations],
        "has_critical_issues": val_res.has_critical_issues,
        "has_errors": val_res.has_errors,
    }


@router.get("/{product_id}/enrichment")
def get_product_enrichment(product_id: uuid.UUID, session: Session = Depends(get_session)):
    """Returns the latest AI commerce enrichment content for this product in frontend-consumable format."""
    repo = ProductRepository(session)
    product = repo.get_by_id(product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID {product_id} not found",
        )

    stmt = select(EnrichmentResult).where(
        EnrichmentResult.product_id == product_id
    ).order_by(EnrichmentResult.created_at.desc())
    
    enrichment = session.exec(stmt).first()
    if not enrichment:
        return {
            "product_id": str(product_id),
            "commerce_description": product.commerce_description,
            "short_description": None,
            "features": product.features or [],
            "applications": product.applications or [],
            "keywords": product.keywords or [],
            "seo_title": None,
            "seo_description": None,
            "status": "pending",
            "confidence": None,
            "model": None,
            "prompt_version": None,
        }

    try:
        gen_data = json.loads(enrichment.generated_value) if isinstance(enrichment.generated_value, str) else enrichment.generated_value
        if not isinstance(gen_data, dict):
            gen_data = {}
    except Exception:
        gen_data = {}

    return {
        "id": str(enrichment.id),
        "product_id": str(enrichment.product_id),
        "enrichment_type": enrichment.enrichment_type.value if hasattr(enrichment.enrichment_type, "value") else str(enrichment.enrichment_type),
        "status": enrichment.status.value if hasattr(enrichment.status, "value") else str(enrichment.status),
        "model": enrichment.model,
        "prompt_version": enrichment.prompt_version,
        "confidence": enrichment.confidence,
        "created_at": enrichment.created_at.isoformat() if enrichment.created_at else None,
        "approved_at": enrichment.approved_at.isoformat() if enrichment.approved_at else None,
        "approved_by": enrichment.approved_by,
        "generated_value": enrichment.generated_value,
        # Parsed generated fields for direct consumption
        "commerce_description": gen_data.get("commerce_description") or product.commerce_description,
        "short_description": gen_data.get("short_description"),
        "features": gen_data.get("features") or product.features or [],
        "applications": gen_data.get("applications") or product.applications or [],
        "keywords": gen_data.get("keywords") or product.keywords or [],
        "seo_title": gen_data.get("seo_title"),
        "seo_description": gen_data.get("seo_description"),
    }


@router.post("/{product_id}/validate")
def rerun_product_validation(product_id: uuid.UUID, session: Session = Depends(get_session)):
    """Re-runs validation engine on demand for a product."""
    repo = ProductRepository(session)
    product = repo.get_by_id(product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID {product_id} not found",
        )

    attributes = repo.get_attributes(product_id)
    attr_repo = AttributeRepository(session)
    evidence = attr_repo.get_evidence_for_product(product_id)
    evidence_names = {
        a.attribute_name for a in attributes
        if any(e.attribute_id == a.id and e.evidence_text for e in evidence)
    }

    engine = ValidationEngine()
    val_res = engine.validate_product(
        product=product,
        attributes=attributes,
        evidence_supported_attribute_names=evidence_names,
    )

    # Persist ValidationResult records
    existing_open = repo.get_validations(product_id, status=ValidationStatus.open)
    for old in existing_open:
        session.delete(old)

    for issue in val_res.issues:
        session.add(issue.to_db_model(product.id))

    product.quality_score = val_res.quality_breakdown.quality_score
    if val_res.has_critical_issues or val_res.has_errors or product.quality_score < 70.0:
        product.status = ProductStatus.needs_review
    else:
        product.status = ProductStatus.verified

    product.updated_at = datetime.now(timezone.utc)
    session.add(product)
    session.commit()

    return {
        "status": "success",
        "product_id": str(product_id),
        "quality_score": product.quality_score,
        "product_status": product.status,
        "issues_count": len(val_res.issues),
    }


@router.post("/{product_id}/enrich")
def rerun_product_enrichment(product_id: uuid.UUID, session: Session = Depends(get_session)):
    """Re-runs AI commerce enrichment on demand for a product."""
    repo = ProductRepository(session)
    product = repo.get_by_id(product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID {product_id} not found",
        )

    from app.services.llm.factory import get_llm_provider
    from app.services.pipeline import EnrichmentStage

    provider = get_llm_provider()
    stage = EnrichmentStage(llm_provider=provider)

    # Create dummy processing step for stage execution
    from app.models import ProcessingJob, ProcessingStep, ProcessingStage, StepStatus
    job = ProcessingJob(total_items=1, completed_items=0)
    session.add(job)
    session.commit()
    session.refresh(job)

    step = ProcessingStep(job_id=job.id, stage=ProcessingStage.enriching, status=StepStatus.processing)
    session.add(step)
    session.commit()
    session.refresh(step)

    # Find associated document
    from app.models import ProductDocumentAssociation
    stmt = select(ProductDocumentAssociation).where(ProductDocumentAssociation.product_id == product_id)
    assoc = session.exec(stmt).first()

    if assoc:
        stage.execute(session, assoc.document_id, job.id, step.id)

    session.refresh(product)
    return {
        "status": "success",
        "product_id": str(product_id),
        "commerce_description": product.commerce_description,
        "features": product.features,
        "applications": product.applications,
    }


@router.post("/{product_id}/validation/{validation_id}/resolve")
def resolve_validation_issue(
    product_id: uuid.UUID,
    validation_id: uuid.UUID,
    request: ResolutionRequest,
    session: Session = Depends(get_session),
):
    """
    Human review endpoint for resolving validation issues and conflict resolution.
    Creates ProductVersion and AuditLog transactionally.
    """
    repo = ProductRepository(session)
    product = repo.get_by_id(product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID {product_id} not found",
        )

    val_record = session.get(ValidationResult, validation_id)
    if not val_record or val_record.product_id != product_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Validation result {validation_id} not found for product {product_id}",
        )

    now = datetime.now(timezone.utc)

    # Create version snapshot BEFORE resolution
    product_service = ProductService(session)

    # If associated attribute value is updated by resolution
    if val_record.attribute_id:
        attr = session.get(ProductAttribute, val_record.attribute_id)
        if attr:
            old_value = attr.raw_value
            new_value = request.resolved_value if request.resolved_value is not None else old_value
            if request.resolution == "accept_source_a" and val_record.actual_value:
                new_value = str(val_record.actual_value)
            elif request.resolution == "accept_source_b" and val_record.expected_value:
                new_value = str(val_record.expected_value)

            attr.raw_value = str(new_value)
            attr.status = ProductStatus.verified
            attr.updated_at = now
            session.add(attr)

    # Mark validation as resolved
    val_record.status = ValidationStatus.resolved
    val_record.resolved_at = now
    val_record.resolved_by = "human_reviewer"
    session.add(val_record)

    # Audit log
    audit = AuditLog(
        entity_type="validation_result",
        entity_id=validation_id,
        action="human_resolution",
        changes={
            "resolution": request.resolution,
            "resolved_value": request.resolved_value,
            "notes": request.notes,
        },
        actor_type="human",
    )
    session.add(audit)

    # Recalculate quality score
    attributes = repo.get_attributes(product_id)
    attr_repo = AttributeRepository(session)
    evidence = attr_repo.get_evidence_for_product(product_id)
    evidence_names = {
        a.attribute_name for a in attributes
        if any(e.attribute_id == a.id and e.evidence_text for e in evidence)
    }

    engine = ValidationEngine()
    val_res = engine.validate_product(product, attributes, evidence_names)
    product.quality_score = val_res.quality_breakdown.quality_score
    if not val_res.has_critical_issues and not val_res.has_errors:
        product.status = ProductStatus.verified
    product.updated_at = now
    session.add(product)

    session.commit()

    return {
        "status": "resolved",
        "validation_id": str(validation_id),
        "product_id": str(product_id),
        "quality_score": product.quality_score,
        "product_status": product.status,
    }


@router.get("/{product_id}/versions", response_model=List[ProductVersion])
def get_product_versions(product_id: uuid.UUID, session: Session = Depends(get_session)):
    repo = ProductRepository(session)
    if not repo.get_by_id(product_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID {product_id} not found",
        )
    return repo.get_versions(product_id)


@router.get("/{product_id}/evidence", response_model=List[AttributeEvidence])
def get_product_evidence(product_id: uuid.UUID, session: Session = Depends(get_session)):
    repo = ProductRepository(session)
    if not repo.get_by_id(product_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID {product_id} not found",
        )
    attr_repo = AttributeRepository(session)
    return attr_repo.get_evidence_for_product(product_id)


@router.get("/{product_id}/reconciliation", response_model=ProductReconciliationResponse)
def get_product_reconciliation(
    product_id: uuid.UUID, session: Session = Depends(get_session)
):
    repo = ProductRepository(session)
    if not repo.get_by_id(product_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID {product_id} not found",
        )

    reconciler = MultiSourceReconciler(session)
    summary = reconciler.reconcile_product(product_id)
    return summary


@router.get("/{product_id}/sources", response_model=List[ProductSourceResponse])
def get_product_sources(
    product_id: uuid.UUID, session: Session = Depends(get_session)
):
    repo = ProductRepository(session)
    product = repo.get_by_id(product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID {product_id} not found",
        )

    attr_repo = AttributeRepository(session)
    evidences = attr_repo.get_evidence_for_product(product_id)

    # Collect source IDs from evidence
    source_ids = {ev.source_id for ev in evidences if ev.source_id}

    # Also collect document associations
    stmt = select(ProductDocumentAssociation).where(
        ProductDocumentAssociation.product_id == product_id
    )
    doc_assocs = session.exec(stmt).all()
    doc_ids = {da.document_id for da in doc_assocs}

    sources_by_id: Dict[str, Source] = {}
    if source_ids:
        src_stmt = select(Source).where(Source.id.in_(source_ids))
        for s in session.exec(src_stmt).all():
            sources_by_id[str(s.id)] = s

    if doc_ids:
        doc_src_stmt = select(Source).where(Source.document_id.in_(doc_ids))
        for s in session.exec(doc_src_stmt).all():
            sources_by_id[str(s.id)] = s

    # Fallback to Document table for virtual source representation if no Source record registered yet
    if doc_ids:
        doc_stmt = select(Document).where(Document.id.in_(doc_ids))
        docs = session.exec(doc_stmt).all()
        for doc in docs:
            already_registered = any(s.document_id == doc.id for s in sources_by_id.values())
            if not already_registered:
                sources_by_id[str(doc.id)] = Source(
                    id=doc.id,
                    source_type=SourceType.document,
                    name=doc.filename,
                    document_id=doc.id,
                    trust_level=1.0,
                    metadata_json=doc.metadata_json or {},
                    created_at=doc.created_at,
                )

    result_sources: List[ProductSourceResponse] = []
    for s in sources_by_id.values():
        result_sources.append(
            ProductSourceResponse(
                source_id=str(s.id),
                source_name=s.name,
                source_type=str(s.source_type.value if hasattr(s.source_type, "value") else s.source_type),
                uri=s.uri,
                trust_level=s.trust_level,
                document_id=str(s.document_id) if s.document_id else None,
                metadata_json=s.metadata_json or {},
                created_at=s.created_at,
                association_type="evidence_source" if s.id in source_ids else "document_source",
            )
        )

    result_sources.sort(key=lambda s: s.trust_level, reverse=True)
    return result_sources

