"""
Embedding Provider package for CatalogIQ.
Provides abstract interface and concrete implementations for generating vector embeddings.
"""
from app.services.embeddings.base import BaseEmbeddingProvider
from app.services.embeddings.factory import get_embedding_provider

__all__ = ["BaseEmbeddingProvider", "get_embedding_provider"]
