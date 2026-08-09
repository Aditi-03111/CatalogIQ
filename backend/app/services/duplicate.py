import uuid
from typing import Optional, Dict, Any
from sqlmodel import Session, select, and_
from app.models import DuplicateCandidate, DuplicateStatus, DuplicateMethod

class DuplicateService:
    def __init__(self, session: Session):
        self.session = session

    def add_duplicate_candidate(
        self,
        p1: uuid.UUID,
        p2: uuid.UUID,
        similarity_score: float,
        detection_method: DuplicateMethod,
        evidence_json: Optional[Dict[str, Any]] = None
    ) -> DuplicateCandidate:
        """
        Registers a potential duplicate between two products.
        Enforces canonical ordering (product_id < candidate_product_id) to prevent duplicate pairs.
        """
        if p1 == p2:
            raise ValueError("product_id and candidate_product_id cannot be identical")

        # Force canonical ordering sorting
        prod_id, cand_id = (p1, p2) if p1 < p2 else (p2, p1)

        # Check for existing record
        statement = select(DuplicateCandidate).where(
            and_(
                DuplicateCandidate.product_id == prod_id,
                DuplicateCandidate.candidate_product_id == cand_id
            )
        )
        existing = self.session.exec(statement).first()
        
        if existing:
            existing.similarity_score = similarity_score
            existing.detection_method = detection_method
            if evidence_json:
                existing.evidence_json = evidence_json
            self.session.add(existing)
            self.session.commit()
            self.session.refresh(existing)
            return existing

        # Insert new record
        candidate = DuplicateCandidate(
            product_id=prod_id,
            candidate_product_id=cand_id,
            similarity_score=similarity_score,
            detection_method=detection_method,
            evidence_json=evidence_json or {},
            status=DuplicateStatus.pending
        )
        self.session.add(candidate)
        self.session.commit()
        self.session.refresh(candidate)
        return candidate
