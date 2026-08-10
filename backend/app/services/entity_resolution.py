"""
EntityResolutionService — Product Entity Resolution & Match Hierarchy.

Provides deterministic and semantic entity matching to link incoming source data
to existing Product records safely without false merges.

Decision Hierarchy:
  Level 1 — Exact SKU + Brand Match      (Automatic Match)
  Level 2 — Exact Model + Brand Match    (Automatic Match, if SKU does not conflict)
  Level 3 — Exact Product Name + Brand  (Automatic Match, if no identity conflicts)
  Level 4 — Semantic Vector Similarity   (Generates DuplicateCandidate for human review; NEVER auto-merges)

Safety Rules:
  - Prefers 'uncertain match' over 'incorrect merge'.
  - Distinct SKUs for same brand (e.g. MX-500 vs MX-501) MUST NOT match.
  - High semantic vector similarity creates DuplicateCandidate with status='pending'.
"""
import re
import uuid
import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from sqlmodel import Session, select, and_

from app.models import Product, DuplicateCandidate, DuplicateMethod, DuplicateStatus
from app.repositories import ProductRepository
from app.services.duplicate import DuplicateService
from app.services.qdrant import QdrantService
from app.services.embeddings.factory import get_embedding_provider

logger = logging.getLogger(__name__)


class EntityResolutionResult(BaseModel):
    """
    Structured outcome of product entity resolution pass.
    """
    matched_product: Optional[Dict[str, Any]] = None  # Model dump or dict representation of matched product
    matched_product_id: Optional[str] = None
    is_exact_match: bool = False
    match_level: str = "none"  # "exact_sku_brand" | "exact_model_brand" | "exact_name_brand" | "semantic_candidate" | "none"
    confidence_score: float = 0.0
    candidate_products: List[Dict[str, Any]] = Field(default_factory=list)
    duplicate_candidate_ids: List[str] = Field(default_factory=list)
    needs_human_review: bool = False
    explanation: str = ""


class EntityResolutionService:
    """
    Service responsible for safely determining whether incoming extracted product data
    matches an existing database Product.
    """

    def __init__(
        self,
        session: Session,
        qdrant_service: Optional[QdrantService] = None,
    ):
        self.session = session
        self.product_repo = ProductRepository(session)
        self.duplicate_service = DuplicateService(session)
        self.qdrant_service = qdrant_service or QdrantService()

    @staticmethod
    def normalize_identifier(val: Optional[str]) -> Optional[str]:
        """
        Normalizes SKUs, Model numbers, and Brand names for strict identity comparison.
        Collapses whitespace, lowercases, and strips non-alphanumeric characters.

        Examples:
          "MX-500"  -> "mx500"
          "MX 500"  -> "mx500"
          "MX500"   -> "mx500"
          "MX-500A" -> "mx500a" (distinct from mx500)
        """
        if not val or not isinstance(val, str):
            return None
        cleaned = re.sub(r"[^a-zA-Z0-9]", "", val.strip().lower())
        return cleaned if cleaned else None

    @staticmethod
    def normalize_text(val: Optional[str]) -> Optional[str]:
        """Light cleanup for text fields (product_name, category)."""
        if not val or not isinstance(val, str):
            return None
        return " ".join(val.strip().lower().split())

    def resolve_product(
        self,
        product_data: Dict[str, Any],
        search_text: Optional[str] = None,
        enable_semantic_search: bool = True,
    ) -> EntityResolutionResult:
        """
        Resolves product identity against existing PostgreSQL products using hierarchy.

        Args:
            product_data: Dict containing candidate product fields (sku, brand, model, product_name, etc.)
            search_text: Optional raw text representation for vector similarity lookup.
            enable_semantic_search: Whether to execute Qdrant candidate search if exact match fails.

        Returns:
            EntityResolutionResult detailing match outcome.
        """
        raw_sku = product_data.get("sku")
        raw_brand = product_data.get("brand")
        raw_model = product_data.get("model")
        raw_name = product_data.get("product_name")

        sku_norm = self.normalize_identifier(raw_sku)
        brand_norm = self.normalize_identifier(raw_brand)
        model_norm = self.normalize_identifier(raw_model)
        name_norm = self.normalize_text(raw_name)

        all_products = self.session.exec(select(Product)).all()

        # -------------------------------------------------------------------
        # LEVEL 1 — EXACT SKU + BRAND MATCH
        # -------------------------------------------------------------------
        if sku_norm and brand_norm:
            for p in all_products:
                p_sku_norm = self.normalize_identifier(p.sku)
                p_brand_norm = self.normalize_identifier(p.brand)

                if p_sku_norm == sku_norm and p_brand_norm == brand_norm:
                    logger.info(f"Level 1 Match (Exact SKU + Brand): {p.id} ({p.brand} {p.sku})")
                    return EntityResolutionResult(
                        matched_product=p.model_dump(),
                        matched_product_id=str(p.id),
                        is_exact_match=True,
                        match_level="exact_sku_brand",
                        confidence_score=1.0,
                        needs_human_review=False,
                        explanation=f"Exact match on SKU '{raw_sku}' and Brand '{raw_brand}'",
                    )

        # -------------------------------------------------------------------
        # LEVEL 2 — EXACT MODEL + BRAND MATCH
        # -------------------------------------------------------------------
        if model_norm and brand_norm:
            for p in all_products:
                p_model_norm = self.normalize_identifier(p.model)
                p_brand_norm = self.normalize_identifier(p.brand)
                p_sku_norm = self.normalize_identifier(p.sku)

                if p_model_norm == model_norm and p_brand_norm == brand_norm:
                    # Safety check: if input SKU is provided and differs from p.sku, DO NOT match!
                    if sku_norm and p_sku_norm and sku_norm != p_sku_norm:
                        logger.warning(
                            f"Model matches ({model_norm}) but SKUs conflict ({sku_norm} vs {p_sku_norm}). Preventing match."
                        )
                        continue

                    logger.info(f"Level 2 Match (Exact Model + Brand): {p.id} ({p.brand} Model: {p.model})")
                    return EntityResolutionResult(
                        matched_product=p.model_dump(),
                        matched_product_id=str(p.id),
                        is_exact_match=True,
                        match_level="exact_model_brand",
                        confidence_score=0.95,
                        needs_human_review=False,
                        explanation=f"Exact match on Model '{raw_model}' and Brand '{raw_brand}'",
                    )

        # -------------------------------------------------------------------
        # LEVEL 3 — EXACT PRODUCT NAME + BRAND MATCH
        # -------------------------------------------------------------------
        if name_norm and brand_norm:
            for p in all_products:
                p_name_norm = self.normalize_text(p.product_name)
                p_brand_norm = self.normalize_identifier(p.brand)
                p_sku_norm = self.normalize_identifier(p.sku)
                p_model_norm = self.normalize_identifier(p.model)

                if p_name_norm == name_norm and p_brand_norm == brand_norm:
                    # Safety check: SKU or Model mismatch prevents auto-merge
                    if sku_norm and p_sku_norm and sku_norm != p_sku_norm:
                        continue
                    if model_norm and p_model_norm and model_norm != p_model_norm:
                        continue

                    logger.info(f"Level 3 Match (Exact Name + Brand): {p.id} ({p.product_name})")
                    return EntityResolutionResult(
                        matched_product=p.model_dump(),
                        matched_product_id=str(p.id),
                        is_exact_match=True,
                        match_level="exact_name_brand",
                        confidence_score=0.90,
                        needs_human_review=False,
                        explanation=f"Exact match on Product Name '{raw_name}' and Brand '{raw_brand}'",
                    )

        # -------------------------------------------------------------------
        # LEVEL 4 — SEMANTIC SIMILARITY CANDIDATES (Qdrant)
        # -------------------------------------------------------------------
        if enable_semantic_search and self.qdrant_service.health_check():
            text_to_embed = search_text or f"{raw_name or ''} {raw_brand or ''} {raw_sku or ''} {raw_model or ''}".strip()
            if text_to_embed:
                try:
                    provider = get_embedding_provider()
                    query_vec = provider.embed_text(text_to_embed)
                    hits = self.qdrant_service.search_vectors(query_vector=query_vec, limit=5)

                    candidate_products = []
                    candidate_ids = []

                    for hit in hits:
                        cand_id_str = hit["id"]
                        score = hit["score"]

                        # Threshold for candidate registration: >= 0.70
                        if score >= 0.70:
                            try:
                                cand_uuid = uuid.UUID(cand_id_str)
                                cand_prod = self.product_repo.get_by_id(cand_uuid)
                                if cand_prod:
                                    cand_sku_norm = self.normalize_identifier(cand_prod.sku)
                                    cand_brand_norm = self.normalize_identifier(cand_prod.brand)

                                    # False match prevention: if SKUs conflict for same brand, skip
                                    if sku_norm and cand_sku_norm and sku_norm != cand_sku_norm and brand_norm == cand_brand_norm:
                                        continue

                                    candidate_products.append(cand_prod.model_dump())
                                    candidate_ids.append(str(cand_prod.id))
                            except ValueError:
                                continue

                    if candidate_products:
                        logger.info(
                            f"Level 4 Candidate Match: Found {len(candidate_products)} vector candidates. Requiring human review."
                        )
                        return EntityResolutionResult(
                            matched_product=None,
                            matched_product_id=None,
                            is_exact_match=False,
                            match_level="semantic_candidate",
                            confidence_score=float(hits[0]["score"]) if hits else 0.75,
                            candidate_products=candidate_products,
                            duplicate_candidate_ids=candidate_ids,
                            needs_human_review=True,
                            explanation=f"Found {len(candidate_products)} potential vector similarity candidates. Human review required.",
                        )
                except Exception as e:
                    logger.warning(f"Semantic entity resolution lookup failed: {e}")

        # -------------------------------------------------------------------
        # NO MATCH FOUND
        # -------------------------------------------------------------------
        logger.info("No matching product found during entity resolution.")
        return EntityResolutionResult(
            matched_product=None,
            matched_product_id=None,
            is_exact_match=False,
            match_level="none",
            confidence_score=0.0,
            candidate_products=[],
            duplicate_candidate_ids=[],
            needs_human_review=False,
            explanation="No existing product matched in database",
        )
