"""
Product Indexing Service.
Orchestrates search document generation, embedding generation, idempotent Qdrant vector upserts,
and PostgreSQL EmbeddingMetadata synchronization.
"""
import hashlib
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlmodel import Session, select

from app.core.config import settings
from app.models import EmbeddingMetadata, EnrichmentResult, Product
from app.repositories import AttributeRepository, ProductRepository
from app.services.embeddings.base import BaseEmbeddingProvider
from app.services.embeddings.factory import get_embedding_provider
from app.services.qdrant import QdrantService
from app.services.search_document import build_qdrant_payload, build_search_document

logger = logging.getLogger(__name__)


class IndexingService:
    """
    Service responsible for building product search documents, generating vector embeddings,
    and idempotently indexing products into Qdrant and PostgreSQL EmbeddingMetadata.
    """

    def __init__(
        self,
        session: Session,
        embedding_provider: Optional[BaseEmbeddingProvider] = None,
        qdrant_service: Optional[QdrantService] = None,
    ):
        self.session = session
        self._embedding_provider = embedding_provider
        self._qdrant_service = qdrant_service or QdrantService()

    @property
    def embedding_provider(self) -> BaseEmbeddingProvider:
        if self._embedding_provider is None:
            self._embedding_provider = get_embedding_provider()
        return self._embedding_provider

    @staticmethod
    def get_vector_id(product_id: uuid.UUID) -> str:
        """Returns deterministic string UUID point ID derived from product_id."""
        return str(product_id)

    def index_product(
        self,
        product_id: uuid.UUID,
        collection_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Indexes or re-indexes a single product into Qdrant and updates EmbeddingMetadata.

        CRITICAL IDEMPOTENCY GUARANTEE:
          Uses a deterministic Qdrant point ID derived from product_id.
          Repeated indexing overwrites the single point in Qdrant rather than creating duplicates.

        Args:
            product_id: UUID of product to index.
            collection_name: Target Qdrant collection name.

        Returns:
            Dict containing indexing status, vector_id, content_hash, and dimensions.
        """
        target_collection = collection_name or settings.QDRANT_COLLECTION_NAME

        # 1. Fetch Product
        product_repo = ProductRepository(self.session)
        product = product_repo.get_by_id(product_id)
        if not product:
            raise ValueError(f"Product with ID {product_id} not found")

        # 2. Fetch Attributes
        attr_repo = AttributeRepository(self.session)
        attributes = attr_repo.list_by_product(product.id)

        # 3. Fetch latest EnrichmentResult
        enrich_stmt = (
            select(EnrichmentResult)
            .where(EnrichmentResult.product_id == product.id)
            .order_by(EnrichmentResult.created_at.desc())
        )
        enrichment = self.session.exec(enrich_stmt).first()

        # 4. Build canonical search document text & content hash
        search_doc_text = build_search_document(product, attributes, enrichment)
        content_hash = hashlib.sha256(search_doc_text.encode("utf-8")).hexdigest()

        # 5. Generate vector embedding
        provider = self.embedding_provider
        vector = provider.embed_text(search_doc_text)
        vector_dim = len(vector)

        # 6. Build Qdrant payload
        payload = build_qdrant_payload(product, attributes)
        payload["content_hash"] = content_hash
        payload["indexed_at"] = datetime.now(timezone.utc).isoformat()

        # 7. Upsert to Qdrant using deterministic vector_id
        vector_id = self.get_vector_id(product.id)
        self._qdrant_service.upsert_product_vector(
            point_id=vector_id,
            vector=vector,
            payload=payload,
            collection_name=target_collection,
        )

        # 8. Synchronize PostgreSQL EmbeddingMetadata record
        now = datetime.now(timezone.utc)
        meta_stmt = select(EmbeddingMetadata).where(
            EmbeddingMetadata.product_id == product.id
        )
        meta_record = self.session.exec(meta_stmt).first()

        if meta_record:
            meta_record.vector_id = vector_id
            meta_record.collection_name = target_collection
            meta_record.embedding_model = provider.model_name
            meta_record.content_hash = content_hash
            meta_record.dimensions = vector_dim
            meta_record.updated_at = now
            self.session.add(meta_record)
        else:
            meta_record = EmbeddingMetadata(
                product_id=product.id,
                vector_id=vector_id,
                collection_name=target_collection,
                embedding_model=provider.model_name,
                content_hash=content_hash,
                dimensions=vector_dim,
                created_at=now,
                updated_at=now,
            )
            self.session.add(meta_record)

        self.session.commit()
        self.session.refresh(meta_record)

        logger.info(
            f"Successfully indexed product {product.id} ({product.sku}) into Qdrant "
            f"collection '{target_collection}' with vector_id {vector_id}"
        )

        return {
            "status": "indexed",
            "product_id": str(product.id),
            "vector_id": vector_id,
            "collection_name": target_collection,
            "embedding_model": provider.model_name,
            "content_hash": content_hash,
            "dimensions": vector_dim,
        }

    def index_all_products(
        self, collection_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Indexes all products existing in PostgreSQL into Qdrant.

        Returns:
            Dict summary of total, indexed, and failed products.
        """
        product_repo = ProductRepository(self.session)
        products = product_repo.list_products(limit=10000)

        total = len(products)
        indexed = 0
        failed = 0
        errors = []

        for p in products:
            try:
                self.index_product(p.id, collection_name=collection_name)
                indexed += 1
            except Exception as e:
                failed += 1
                err_msg = f"Failed to index product {p.id} ({p.sku}): {e}"
                logger.error(err_msg)
                errors.append(err_msg)

        return {
            "total": total,
            "indexed": indexed,
            "failed": failed,
            "errors": errors,
        }

    def delete_product_index(
        self,
        product_id: uuid.UUID,
        collection_name: Optional[str] = None,
    ) -> bool:
        """
        Removes product vector from Qdrant and deletes PostgreSQL EmbeddingMetadata record.
        """
        target_collection = collection_name or settings.QDRANT_COLLECTION_NAME
        vector_id = self.get_vector_id(product_id)

        # 1. Delete vector from Qdrant
        self._qdrant_service.delete_vector(vector_id, collection_name=target_collection)

        # 2. Delete EmbeddingMetadata record
        meta_stmt = select(EmbeddingMetadata).where(
            EmbeddingMetadata.product_id == product_id
        )
        meta_record = self.session.exec(meta_stmt).first()
        if meta_record:
            self.session.delete(meta_record)
            self.session.commit()

        return True
