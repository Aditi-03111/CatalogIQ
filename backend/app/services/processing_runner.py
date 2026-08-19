import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Session, select

from app.db.session import engine
from app.models import (
    Document,
    DocumentStatus,
    JobStatus,
    ProcessingJob,
    ProcessingStage,
    ProcessingStep,
    StepStatus,
)
from app.services.pipeline import DocumentProcessingService

logger = logging.getLogger(__name__)


def create_processing_step(
    session: Session,
    job_id: uuid.UUID,
    document_id: uuid.UUID,
    stage: ProcessingStage,
) -> ProcessingStep:
    step = ProcessingStep(
        id=uuid.uuid4(),
        job_id=job_id,
        document_id=document_id,
        stage=stage,
        status=StepStatus.queued,
    )
    session.add(step)
    session.commit()
    session.refresh(step)
    return step


def _mark_failed(
    session: Session,
    document_id: uuid.UUID,
    job_id: uuid.UUID,
    step_id: Optional[uuid.UUID],
    error: Exception,
) -> None:
    now = datetime.now(timezone.utc)
    message = str(error)[:500]

    document = session.get(Document, document_id)
    if document:
        document.status = DocumentStatus.failed
        document.updated_at = now
        session.add(document)

    job = session.get(ProcessingJob, job_id)
    if job:
        job.status = JobStatus.failed
        job.failed_items = max(job.failed_items, 1)
        job.error_message = message
        job.completed_at = now
        job.updated_at = now
        session.add(job)

    if step_id:
        step = session.get(ProcessingStep, step_id)
        if step and step.status != StepStatus.completed:
            step.status = StepStatus.failed
            step.error_message = message
            step.completed_at = now
            step.updated_at = now
            session.add(step)

    session.commit()


def run_document_pipeline(document_id: uuid.UUID | str, job_id: uuid.UUID | str, first_step_id: uuid.UUID | str | None = None) -> None:
    """
    Runs the full document pipeline inside the web process.

    Render deployments often run only one web service. This runner avoids jobs
    sitting forever in queued/processing when a separate Celery worker or broker
    is not available.
    """
    doc_id = uuid.UUID(str(document_id))
    proc_job_id = uuid.UUID(str(job_id))
    parsing_step_id = uuid.UUID(str(first_step_id)) if first_step_id else None
    current_step_id: Optional[uuid.UUID] = parsing_step_id

    logger.info("Starting inline document pipeline doc=%s job=%s", doc_id, proc_job_id)

    with Session(engine) as session:
        try:
            document = session.get(Document, doc_id)
            job = session.get(ProcessingJob, proc_job_id)
            if not document or not job:
                logger.error("Cannot run pipeline: document/job missing doc=%s job=%s", doc_id, proc_job_id)
                return

            if parsing_step_id is not None:
                supplied_step = session.get(ProcessingStep, parsing_step_id)
                if not supplied_step or supplied_step.stage != ProcessingStage.parsing:
                    parsing_step_id = None

            if parsing_step_id is None:
                stmt = (
                    select(ProcessingStep)
                    .where(
                        ProcessingStep.job_id == proc_job_id,
                        ProcessingStep.document_id == doc_id,
                        ProcessingStep.stage == ProcessingStage.parsing,
                    )
                    .order_by(ProcessingStep.created_at.desc())
                )
                existing = session.exec(stmt).first()
                parsing_step_id = existing.id if existing else create_processing_step(
                    session, proc_job_id, doc_id, ProcessingStage.parsing
                ).id

            processor = DocumentProcessingService(session)

            current_step_id = parsing_step_id
            processor.process_document(doc_id, proc_job_id, parsing_step_id)

            extraction_step = create_processing_step(session, proc_job_id, doc_id, ProcessingStage.extracting)
            current_step_id = extraction_step.id
            processor.extract_document(doc_id, proc_job_id, extraction_step.id)

            validation_step = create_processing_step(session, proc_job_id, doc_id, ProcessingStage.validating)
            current_step_id = validation_step.id
            processor.validate_document(doc_id, proc_job_id, validation_step.id)

            enrichment_step = create_processing_step(session, proc_job_id, doc_id, ProcessingStage.enriching)
            current_step_id = enrichment_step.id
            processor.enrich_document(doc_id, proc_job_id, enrichment_step.id)

            logger.info("Completed inline document pipeline doc=%s job=%s", doc_id, proc_job_id)
        except Exception as exc:
            logger.error(
                "Inline document pipeline failed doc=%s job=%s step=%s: %s",
                doc_id,
                proc_job_id,
                current_step_id,
                exc,
                exc_info=True,
            )
            _mark_failed(session, doc_id, proc_job_id, current_step_id, exc)
