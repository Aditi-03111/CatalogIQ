import uuid
from typing import List, Optional
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlmodel import Session, select
from pydantic import BaseModel

from app.db.session import get_session
from app.models import ProcessingJob, ProcessingStep, JobStatus, StepStatus
from app.services.processing_runner import run_document_pipeline

router = APIRouter(prefix="/jobs")

# Strongly typed API schemas for job monitoring
class ProcessingStepResponse(BaseModel):
    id: uuid.UUID
    stage: str
    status: str
    attempt_count: int
    error_message: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]
    product_id: Optional[uuid.UUID] = None

    class Config:
        from_attributes = True

class ProcessingJobDetail(BaseModel):
    job_id: uuid.UUID
    status: str
    total_items: int
    completed_items: int
    failed_items: int
    current_stage: str
    error_message: Optional[str]
    steps: List[ProcessingStepResponse]

    class Config:
        from_attributes = True

@router.get("/", response_model=List[ProcessingJob])
def list_jobs(
    limit: int = 100,
    offset: int = 0,
    status: Optional[str] = None,
    session: Session = Depends(get_session)
):
    statement = select(ProcessingJob)
    if status:
        statement = statement.where(ProcessingJob.status == status)
    statement = statement.offset(offset).limit(limit)
    return list(session.exec(statement).all())

@router.get("/{job_id}", response_model=ProcessingJobDetail)
def get_job(
    job_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session)
):
    job = session.get(ProcessingJob, job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID {job_id} not found"
        )
    
    # Auto-healing mechanism: if a job is queued or stale in processing when
    # polled, enqueue the web-process runner so it does not stay frozen forever.
    job_updated_at = job.updated_at
    if job_updated_at and job_updated_at.tzinfo is None:
        job_updated_at = job_updated_at.replace(tzinfo=timezone.utc)
    is_stale_processing = (
        job.status in [JobStatus.processing, "processing"]
        and job_updated_at is not None
        and job_updated_at < datetime.now(timezone.utc) - timedelta(minutes=2)
    )
    if job.status in [JobStatus.queued, "queued"] or is_stale_processing:
        stmt = select(ProcessingStep).where(ProcessingStep.job_id == job_id).order_by(ProcessingStep.created_at.desc())
        latest_step = session.exec(stmt).first()
        if latest_step and latest_step.document_id:
            background_tasks.add_task(
                run_document_pipeline,
                latest_step.document_id,
                job.id,
                latest_step.id,
            )

    # Retrieve steps associated with this job
    stmt = select(ProcessingStep).where(ProcessingStep.job_id == job_id).order_by(ProcessingStep.created_at.asc())
    steps = session.exec(stmt).all()
    
    return ProcessingJobDetail(
        job_id=job.id,
        status=job.status,
        total_items=job.total_items,
        completed_items=job.completed_items,
        failed_items=job.failed_items,
        current_stage=job.current_stage,
        error_message=job.error_message,
        steps=[ProcessingStepResponse.model_validate(s) for s in steps]
    )

@router.post("/{job_id}/retry")
def retry_job(
    job_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session)
):
    job = session.get(ProcessingJob, job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID {job_id} not found"
        )
    
    if job.status != JobStatus.failed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Only failed jobs can be retried. Current status is '{job.status}'"
        )

    # Find the latest step associated with this job
    stmt = select(ProcessingStep).where(ProcessingStep.job_id == job_id).order_by(ProcessingStep.created_at.desc())
    step = session.exec(stmt).first()
    if not step:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No steps found for this job to retry"
        )

    # Reset job and step statuses back to queued
    job.status = JobStatus.queued
    job.error_message = None
    job.completed_items = 0
    job.failed_items = 0
    
    step.status = StepStatus.queued
    step.error_message = None
    step.attempt_count += 1
    
    session.add(job)
    session.add(step)
    session.commit()

    background_tasks.add_task(run_document_pipeline, step.document_id, job_id, step.id)

    return {"message": "Job retry scheduled successfully", "job_id": job_id}
