import uuid
from typing import Optional, List
from sqlmodel import Session, select
from app.models import Document

class DocumentRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, doc_id: uuid.UUID) -> Optional[Document]:
        return self.session.get(Document, doc_id)

    def get_by_file_hash(self, file_hash: str) -> Optional[Document]:
        statement = select(Document).where(Document.file_hash == file_hash)
        return self.session.exec(statement).first()

    def list_documents(self, limit: int = 100, offset: int = 0, status: Optional[str] = None) -> List[Document]:
        statement = select(Document)
        if status:
            statement = statement.where(Document.status == status)
        statement = statement.offset(offset).limit(limit)
        return list(self.session.exec(statement).all())

    def create(self, document: Document) -> Document:
        self.session.add(document)
        self.session.commit()
        self.session.refresh(document)
        return document

    def save(self, document: Document) -> Document:
        self.session.add(document)
        self.session.commit()
        self.session.refresh(document)
        return document
