import uuid
import json
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile
from sqlmodel import Session
from pydantic import BaseModel

from app.db.session import get_session
from app.models import Document
from app.repositories import DocumentRepository
from app.services.document import DocumentService
from app.services.storage import get_storage_service

router = APIRouter(prefix="/documents")

# Typed upload response
class UploadResponse(BaseModel):
    document_id: uuid.UUID
    job_id: Optional[uuid.UUID]
    status: str
    cached: bool

class ReprocessResponse(BaseModel):
    document_id: uuid.UUID
    job_id: uuid.UUID
    status: str
    reprocessed: bool

@router.get("/", response_model=List[Document])
def list_documents(
    limit: int = 100,
    offset: int = 0,
    status: Optional[str] = None,
    session: Session = Depends(get_session)
):
    repo = DocumentRepository(session)
    return repo.list_documents(limit=limit, offset=offset, status=status)

@router.get("/{document_id}", response_model=Document)
def get_document(document_id: uuid.UUID, session: Session = Depends(get_session)):
    repo = DocumentRepository(session)
    doc = repo.get_by_id(document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID {document_id} not found"
        )
    return doc

@router.post("/upload", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
def upload_document(
    file: UploadFile = File(...),
    session: Session = Depends(get_session)
):
    service = DocumentService(session)
    try:
        file_content = file.file.read()
        res = service.upload_document(
            file_content=file_content,
            filename=file.filename,
            mime_type=file.content_type or "application/pdf"
        )
        return UploadResponse(
            document_id=res["document_id"],
            job_id=res.get("job_id"),
            status=res["status"],
            cached=res.get("cached", False)
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"File ingestion failed: {str(e)}"
        )

@router.post("/{document_id}/reprocess", response_model=ReprocessResponse)
def reprocess_document(
    document_id: uuid.UUID,
    session: Session = Depends(get_session)
):
    service = DocumentService(session)
    try:
        res = service.force_reprocess(document_id)
        return ReprocessResponse(
            document_id=res["document_id"],
            job_id=res["job_id"],
            status=res["status"],
            reprocessed=res.get("reprocessed", True)
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Reprocessing failed: {str(e)}"
        )

@router.get("/{document_id}/parsed")
def get_parsed_document(
    document_id: uuid.UUID,
    session: Session = Depends(get_session)
):
    repo = DocumentRepository(session)
    doc = repo.get_by_id(document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID {document_id} not found"
        )
    
    if not doc.parsed_storage_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document has not been successfully parsed yet"
        )

    # Download the structured intermediate representation from storage
    storage = get_storage_service()
    try:
        file_bytes = storage.download_file(doc.parsed_storage_key)
        parsed_data = json.loads(file_bytes.decode("utf-8"))
        return parsed_data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load parsed document artifact: {str(e)}"
        )
@router.get("/{document_id}/extracted")
def get_extracted_document(
    document_id: uuid.UUID,
    session: Session = Depends(get_session)
):
    """
    Returns the extraction summary for a document (product + attributes count).
    The full product data is available via GET /api/v1/products/{product_id}.
    """
    repo = DocumentRepository(session)
    doc = repo.get_by_id(document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID {document_id} not found"
        )

    extraction_key = f"documents/extracted/{document_id}.json"
    storage = get_storage_service()
    try:
        file_bytes = storage.download_file(extraction_key)
        return json.loads(file_bytes.decode("utf-8"))
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Extraction results not yet available for this document. "
                   "Ensure the document has been processed through the extraction stage."
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load extraction results: {str(e)}"
        )
