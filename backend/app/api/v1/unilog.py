import os
import uuid
import csv
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, Query, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse, Response, StreamingResponse
from sqlmodel import Session, select, func

from app.core.config import settings
from app.db.session import get_session
from app.models.unilog import UnilogRecord, UnilogEnriched, UnilogStatus
from app.services.unilog.pipeline import UnilogPipelineService

router = APIRouter()

# Global lock/state to prevent duplicate concurrent background runs
is_processing = False

def run_background_enrichment(limit: int, db: Session):
    global is_processing
    is_processing = True
    try:
        # Fetch records
        stmt = (
            select(UnilogRecord.id)
            .join(UnilogEnriched, UnilogRecord.id == UnilogEnriched.record_id, isouter=True)
            .where(
                (UnilogEnriched.status == None) |
                (UnilogEnriched.status == UnilogStatus.queued) |
                (UnilogEnriched.status == UnilogStatus.failed)
            )
            .limit(limit)
        )
        record_ids = db.exec(stmt).all()
        
        pipeline = UnilogPipelineService(db)
        for rec_id in record_ids:
            try:
                pipeline.process_record(rec_id)
            except Exception:
                pass
    finally:
        is_processing = False

@router.post("/import", response_model=Dict[str, Any])
def import_unilog_dataset(db: Session = Depends(get_session)):
    """Imports the raw catalog dataset file from the local data folder."""
    data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../data"))
    raw_input_path = os.path.join(data_dir, "Unihack_ Sample Dataset - Input.csv")
    
    if not os.path.exists(raw_input_path):
        raise HTTPException(status_code=404, detail="Raw input dataset file not found in data folder.")
        
    count = 0
    skipped = 0
    with open(raw_input_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            mpn = row.get("Mfg_Part_Num", "").strip()
            if not mpn:
                continue
                
            existing = db.exec(select(UnilogRecord).where(UnilogRecord.mfg_part_num == mpn)).first()
            if existing:
                skipped += 1
                continue
                
            record = UnilogRecord(
                id=uuid.uuid4(),
                mfg_part_num=mpn,
                part_desc=row.get("Part_Desc", ""),
                e1_brand=row.get("E1_Brand", ""),
                unilog_brand=row.get("Unilog_Brand", ""),
                dib_brand=row.get("DIB_Brand", ""),
                part_manuf=row.get("Part_Manuf", "")
            )
            db.add(record)
            count += 1
        db.commit()
        
    return {"status": "success", "imported": count, "skipped": skipped}

@router.post("/process", response_model=Dict[str, Any])
def start_batch_enrichment(
    background_tasks: BackgroundTasks,
    limit: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_session)
):
    """Triggers background AI processing of queued catalog records."""
    global is_processing
    if is_processing:
        return {"status": "active", "message": "Enrichment pipeline is already running in background."}
        
    # Queue the background task
    background_tasks.add_task(run_background_enrichment, limit, db)
    return {"status": "started", "message": f"Queued {limit} records for enrichment in background."}

@router.get("/status", response_model=Dict[str, Any])
def get_enrichment_status(db: Session = Depends(get_session)):
    """Returns metrics about catalog enrichment progress, backlog, and health."""
    total_records = db.exec(select(func.count(UnilogRecord.id))).one()
    
    enriched_records = db.exec(select(func.count(UnilogEnriched.id)).where(UnilogEnriched.status == UnilogStatus.enriched)).one()
    failed_records = db.exec(select(func.count(UnilogEnriched.id)).where(UnilogEnriched.status == UnilogStatus.failed)).one()
    processing_records = db.exec(select(func.count(UnilogEnriched.id)).where(UnilogEnriched.status == UnilogStatus.processing)).one()
    
    pending_records = total_records - enriched_records - failed_records - processing_records
    
    # Calculate average quality score
    avg_score_stmt = select(func.avg(UnilogEnriched.quality_score)).where(UnilogEnriched.status == UnilogStatus.enriched)
    avg_score = db.exec(avg_score_stmt).first() or 0.0
    
    global is_processing
    return {
        "total_records": total_records,
        "enriched_records": enriched_records,
        "failed_records": failed_records,
        "processing_records": processing_records,
        "pending_records": pending_records,
        "average_quality_score": round(float(avg_score), 2),
        "is_active": is_processing
    }

@router.get("/records", response_model=Dict[str, Any])
def list_enriched_records(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=10, ge=1, le=100),
    status: Optional[str] = None,
    needs_review: Optional[bool] = None,
    db: Session = Depends(get_session)
):
    """Lists imported records, showing input details and enriched specs if available."""
    offset = (page - 1) * limit
    
    # Select joined records
    stmt = (
        select(UnilogRecord, UnilogEnriched)
        .join(UnilogEnriched, UnilogRecord.id == UnilogEnriched.record_id, isouter=True)
    )
    
    if status:
        stmt = stmt.where(UnilogEnriched.status == status)
        
    if needs_review is not None:
        stmt = stmt.where(UnilogEnriched.needs_review == needs_review)
        
    stmt = stmt.offset(offset).limit(limit).order_by(UnilogRecord.created_at.desc())
    results = db.exec(stmt).all()
    
    records_list = []
    for record, enriched in results:
        records_list.append({
            "id": str(record.id),
            "mfg_part_num": record.mfg_part_num,
            "part_desc": record.part_desc,
            "part_manuf": record.part_manuf,
            "status": enriched.status if enriched else "queued",
            "quality_score": enriched.quality_score if enriched else 0.0,
            "needs_review": enriched.needs_review if enriched else False,
            "validation_flags": enriched.validation_flags if enriched else [],
            "explainability_trace": enriched.explainability_trace if enriched else {},
            "error_message": enriched.error_message if enriched else None,
            "enriched_data": enriched.enriched_data if enriched and enriched.status == UnilogStatus.enriched else None
        })
        
    # Count total
    count_stmt = select(func.count(UnilogRecord.id))
    
    # Apply filters to count statement
    if status or needs_review is not None:
        count_stmt = count_stmt.join(UnilogEnriched, UnilogRecord.id == UnilogEnriched.record_id)
        if status:
            count_stmt = count_stmt.where(UnilogEnriched.status == status)
        if needs_review is not None:
            count_stmt = count_stmt.where(UnilogEnriched.needs_review == needs_review)
            
    total_count = db.exec(count_stmt).one()
    
    return {
        "records": records_list,
        "total": total_count,
        "page": page,
        "limit": limit
    }

@router.post("/records/{record_id}/approve", response_model=Dict[str, Any])
def approve_enriched_record(record_id: str, db: Session = Depends(get_session)):
    """Sets needs_review = False to approve the record mapping in the review queue."""
    from datetime import datetime, timezone
    enriched = db.exec(select(UnilogEnriched).where(UnilogEnriched.record_id == uuid.UUID(record_id))).first()
    if not enriched:
        raise HTTPException(status_code=404, detail="Enriched record not found")
        
    enriched.needs_review = False
    enriched.validation_flags = []
    enriched.updated_at = datetime.now(timezone.utc)
    db.add(enriched)
    
    # Sync status to CatalogIQ tables
    try:
        from app.models import UnilogRecord, Product, ProductAttribute, ProductStatus, AttributeStatus
        raw_record = db.get(UnilogRecord, enriched.record_id)
        if raw_record:
            # Find the synced product
            prod_stmt = select(Product).where(Product.sku == raw_record.mfg_part_num)
            product = db.exec(prod_stmt).first()
            if product:
                product.status = ProductStatus.verified
                db.add(product)
                
                # Find product attributes
                attrs_stmt = select(ProductAttribute).where(ProductAttribute.product_id == product.id)
                prod_attrs = db.exec(attrs_stmt).all()
                for attr in prod_attrs:
                    attr.status = AttributeStatus.verified
                    db.add(attr)
    except Exception as sync_err:
        pass
        
    db.commit()
    db.refresh(enriched)
    return {"status": "success", "message": "Record approved successfully."}

@router.get("/export")
def download_enriched_csv():
    """Generates and streams the delivery format CSV file download."""
    data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../data"))
    template_path = os.path.join(data_dir, "Unihack_ Expected Output - Delivery Format.csv")
    output_path = os.path.join(data_dir, "enriched_unilog_output.csv")
    
    # Re-run script export module programmatically
    from app.scripts.process_unilog import export_delivery_csv
    export_delivery_csv(template_path, output_path)
    
    if not os.path.exists(output_path):
        raise HTTPException(status_code=404, detail="Enriched output CSV file could not be generated.")
        
    return FileResponse(
        output_path,
        media_type="text/csv",
        filename="enriched_unilog_output.csv"
    )

@router.get("/records/{record_id}/export-pdf")
def download_record_pdf(record_id: str, db: Session = Depends(get_session)):
    """Generates and streams a PDF specification report for a single enriched record."""
    from app.services.pdf_exporter import generate_product_pdf
    
    rec_uuid = uuid.UUID(record_id)
    raw_record = db.get(UnilogRecord, rec_uuid)
    if not raw_record:
        raise HTTPException(status_code=404, detail="Record not found")
        
    enriched = db.exec(select(UnilogEnriched).where(UnilogEnriched.record_id == rec_uuid)).first()
    enriched_data = enriched.enriched_data if enriched and enriched.enriched_data else {}
    
    record_info = {
        "mfg_part_num": raw_record.mfg_part_num,
        "part_desc": raw_record.part_desc,
        "part_manuf": raw_record.part_manuf
    }
    
    pdf_bytes = generate_product_pdf(enriched_data, record_info)
    mpn = raw_record.mfg_part_num or "product"
    
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=CatalogIQ_SpecSheet_{mpn}.pdf"}
    )

@router.get("/export-pdf")
def download_batch_export_pdf(db: Session = Depends(get_session)):
    """Generates and streams a PDF report for the latest enriched record."""
    from app.services.pdf_exporter import generate_product_pdf
    
    enriched = db.exec(
        select(UnilogEnriched)
        .where(UnilogEnriched.status == UnilogStatus.enriched)
        .order_by(UnilogEnriched.updated_at.desc())
    ).first()
    
    if not enriched:
        raise HTTPException(status_code=404, detail="No enriched records available for PDF export.")
        
    raw_record = db.get(UnilogRecord, enriched.record_id)
    enriched_data = enriched.enriched_data or {}
    record_info = {
        "mfg_part_num": raw_record.mfg_part_num if raw_record else "",
        "part_desc": raw_record.part_desc if raw_record else "",
        "part_manuf": raw_record.part_manuf if raw_record else ""
    }
    
    pdf_bytes = generate_product_pdf(enriched_data, record_info)
    mpn = raw_record.mfg_part_num if raw_record else "catalog"
    
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=CatalogIQ_Enriched_Delivery_Report_{mpn}.pdf"}
    )
