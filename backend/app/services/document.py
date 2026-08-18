import uuid
import hashlib
import os
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from sqlmodel import Session, select, and_
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.models import (
    Document, DocumentStatus, ProcessingJob, ProcessingStep, 
    JobStatus, ProcessingStage, StepStatus
)
from app.services.storage import get_storage_service
from app.repositories import DocumentRepository

logger = logging.getLogger(__name__)

class DocumentService:
    def __init__(self, session: Session):
        self.session = session
        self.doc_repo = DocumentRepository(session)
        self.storage = get_storage_service()

    def validate_file(self, file_content: bytes, filename: str) -> None:
        """
        Validates file extension and size limit. If it is a PDF, validates PDF signature.
        """
        # 1. Size validation
        max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        if len(file_content) > max_bytes:
            raise ValueError(f"File size exceeds limit of {settings.MAX_UPLOAD_SIZE_MB}MB")
        if len(file_content) == 0:
            raise ValueError("File is empty")

        # 2. Extension validation
        _, ext = os.path.splitext(filename.lower())
        allowed_exts = {".pdf", ".xlsx", ".xls", ".docx", ".pptx", ".csv", ".txt", ".html", ".htm"}
        if ext not in allowed_exts:
            raise ValueError(f"Unsupported file extension {ext}. Supported formats: PDF, Word, Excel, CSV, PPTX, Text, HTML.")

        # 3. Magic bytes validation (PDF signature %PDF)
        if ext == ".pdf":
            if not file_content.startswith(b"%PDF"):
                raise ValueError("Invalid PDF format. Magic bytes do not match %PDF signature.")

    def upload_document(self, file_content: bytes, filename: str, mime_type: str) -> Dict[str, Any]:
        """
        Ingests a document, performs duplicate detection, saves it to storage,
        registers it in the database, and schedules the parsing task.
        Handles concurrency race conditions via PostgreSQL constraints.
        """
        # Validate input
        self.validate_file(file_content, filename)

        # Compute SHA-256 hash
        file_hash = hashlib.sha256(file_content).hexdigest()

        # Check for existing document in database
        existing_doc = self.doc_repo.get_by_file_hash(file_hash)
        if existing_doc:
            return self._handle_existing_document(existing_doc)

        # If new, create document, job, and step within a transaction block
        doc_id = uuid.uuid4()
        storage_key = f"documents/original/{doc_id}.pdf"
        
        # Write binary file to object storage
        self.storage.upload_file(file_content, storage_key)

        document = Document(
            id=doc_id,
            filename=filename,
            storage_backend=settings.STORAGE_PROVIDER,
            storage_key=storage_key,
            file_hash=file_hash,
            mime_type=mime_type,
            file_size=len(file_content),
            status=DocumentStatus.uploaded
        )

        job_id = uuid.uuid4()
        job = ProcessingJob(
            id=job_id,
            total_items=1,
            status=JobStatus.queued,
            current_stage="parsing"
        )

        step_id = uuid.uuid4()
        step = ProcessingStep(
            id=step_id,
            job_id=job_id,
            document_id=doc_id,
            stage=ProcessingStage.parsing,
            status=StepStatus.queued
        )

        self.session.add(document)
        self.session.add(job)
        self.session.add(step)

        try:
            self.session.commit()
        except IntegrityError:
            # Handle concurrent upload race condition gracefully by picking up the database winner
            self.session.rollback()
            # Clean up the file uploaded to storage since we're discarding this record
            try:
                self.storage.delete_file(storage_key)
            except Exception:
                pass
            winner_doc = self.doc_repo.get_by_file_hash(file_hash)
            if winner_doc:
                return self._handle_existing_document(winner_doc)
            raise

        self.session.refresh(document)
        self.session.refresh(job)

        # Trigger background Celery worker task execution
        # (We import here to prevent circular import boundaries)
        from app.workers.celery_app import safe_dispatch_task
        from app.workers.tasks.document_processing import process_document_task
        safe_dispatch_task(process_document_task, str(doc_id), str(job_id), str(step_id))
        self.session.refresh(job)

        return {
            "document_id": document.id,
            "job_id": job.id,
            "status": job.status or "completed",
            "cached": False
        }

    def force_reprocess(self, document_id: uuid.UUID) -> Dict[str, Any]:
        """
        Creates a new ProcessingJob and ProcessingStep, forcing reprocessing of an
        existing document, preserving all historical jobs/steps in the process log.
        """
        document = self.doc_repo.get_by_id(document_id)
        if not document:
            raise ValueError(f"Document with ID {document_id} not found")

        # Set status back to uploaded to prepare for execution
        document.status = DocumentStatus.uploaded
        document.updated_at = datetime.now(timezone.utc)
        self.session.add(document)

        job_id = uuid.uuid4()
        job = ProcessingJob(
            id=job_id,
            total_items=1,
            status=JobStatus.queued,
            current_stage="parsing"
        )

        step_id = uuid.uuid4()
        step = ProcessingStep(
            id=step_id,
            job_id=job_id,
            document_id=document_id,
            stage=ProcessingStage.parsing,
            status=StepStatus.queued
        )

        self.session.add(job)
        self.session.add(step)
        self.session.commit()

        # Trigger background execution
        from app.workers.celery_app import safe_dispatch_task
        from app.workers.tasks.document_processing import process_document_task
        safe_dispatch_task(process_document_task, str(document_id), str(job_id), str(step_id))
        self.session.refresh(job)

        return {
            "document_id": document.id,
            "job_id": job.id,
            "status": job.status or "completed",
            "reprocessed": True
        }

    def _handle_existing_document(self, doc: Document) -> Dict[str, Any]:
        """
        Resolves duplicate uploads: returns already completed details, or active job pointer.
        """
        # Find the latest job for this document
        stmt = select(ProcessingStep).where(ProcessingStep.document_id == doc.id).order_by(ProcessingStep.created_at.desc())
        latest_step = self.session.exec(stmt).first()
        job_id = latest_step.job_id if latest_step else None

        if doc.status == DocumentStatus.processed:
            return {
                "document_id": doc.id,
                "job_id": job_id,
                "status": "already_processed",
                "cached": True
            }
        
        if doc.status in [DocumentStatus.uploaded, DocumentStatus.parsing]:
            return {
                "document_id": doc.id,
                "job_id": job_id,
                "status": "processing",
                "cached": True
            }

        # If previous attempt failed, fall back to scheduling a new job for retry
        # (This is clean: we don't silently ignore a failed document)
        job_id = uuid.uuid4()
        job = ProcessingJob(
            id=job_id,
            total_items=1,
            status=JobStatus.queued,
            current_stage="parsing"
        )
        step_id = uuid.uuid4()
        step = ProcessingStep(
            id=step_id,
            job_id=job_id,
            document_id=doc.id,
            stage=ProcessingStage.parsing,
            status=StepStatus.queued
        )

        # Reset document status to prepare
        doc.status = DocumentStatus.uploaded
        self.session.add(doc)
        self.session.add(job)
        self.session.add(step)
        self.session.commit()

        from app.workers.celery_app import safe_dispatch_task
        from app.workers.tasks.document_processing import process_document_task
        safe_dispatch_task(process_document_task, str(doc.id), str(job_id), str(step_id))
        self.session.refresh(job)

        return {
            "document_id": doc.id,
            "job_id": job.id,
            "status": job.status or "completed",
            "cached": False
        }
