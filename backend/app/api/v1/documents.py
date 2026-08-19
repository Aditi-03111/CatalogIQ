import uuid
import json
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, BackgroundTasks
from sqlmodel import Session
from pydantic import BaseModel

from app.db.session import get_session
from app.models import Document
from app.repositories import DocumentRepository
from app.services.document import DocumentService
from app.services.processing_runner import run_document_pipeline
from app.services.storage import get_storage_service

router = APIRouter(prefix="/documents")


def _schedule_processing(background_tasks: BackgroundTasks, result: Dict[str, Any]) -> None:
    if not result.get("job_id") or not result.get("step_id"):
        return
    if str(result.get("status", "")).lower() in {"already_processed", "completed"}:
        return
    background_tasks.add_task(
        run_document_pipeline,
        result["document_id"],
        result["job_id"],
        result["step_id"],
    )

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

class URLIngestRequest(BaseModel):
    url: str

class TextIngestRequest(BaseModel):
    text: str
    title: Optional[str] = None

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
    background_tasks: BackgroundTasks,
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
        _schedule_processing(background_tasks, res)
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

@router.post("/url", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
def ingest_url(
    payload: URLIngestRequest,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session)
):
    import urllib.request
    from urllib.parse import urlparse
    
    url = payload.url.strip()
    if not (url.startswith("http://") or url.startswith("https://")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="URL must start with http:// or https://"
        )

    try:
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.replace(":", "_").replace("/", "_") or "webpage"
        filename = f"{domain}_{uuid.uuid4().hex[:6]}.html"

        req = urllib.request.Request(
            url, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
        with urllib.request.urlopen(req, timeout=15) as response:
            content = response.read()
            
        service = DocumentService(session)
        res = service.upload_document(
            file_content=content,
            filename=filename,
            mime_type="text/html"
        )
        _schedule_processing(background_tasks, res)
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
            detail=f"URL scraping failed: {str(e)}"
        )

@router.post("/text", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
def ingest_text(
    payload: TextIngestRequest,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session)
):
    if not payload.text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Pasted text cannot be empty"
        )

    try:
        title = payload.title.strip() if payload.title else "pasted_text"
        title_slug = "".join([c if c.isalnum() else "_" for c in title])
        filename = f"{title_slug}_{uuid.uuid4().hex[:6]}.txt"
        content = payload.text.encode("utf-8")

        service = DocumentService(session)
        res = service.upload_document(
            file_content=content,
            filename=filename,
            mime_type="text/plain"
        )
        _schedule_processing(background_tasks, res)
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
            detail=f"Text ingestion failed: {str(e)}"
        )

@router.post("/{document_id}/reprocess", response_model=ReprocessResponse)
def reprocess_document(
    document_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session)
):
    service = DocumentService(session)
    try:
        res = service.force_reprocess(document_id)
        _schedule_processing(background_tasks, res)
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
