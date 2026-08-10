"""
Factory for instantiating configured embedding provider.
"""
import logging
from typing import Optional

from app.core.config import settings
from app.services.embeddings.base import BaseEmbeddingProvider
from app.services.embeddings.fastembed_provider import FastEmbedProvider
from app.services.embeddings.mock_provider import MockEmbeddingProvider

logger = logging.getLogger(__name__)


def get_embedding_provider(provider_name: Optional[str] = None) -> BaseEmbeddingProvider:
    """
    Returns configured embedding provider instance based on settings and environment.

    In test environment (ENV=test), ALWAYS returns MockEmbeddingProvider.
    In development/production, returns FastEmbedProvider or specified provider.
    """
    target = (provider_name or settings.EMBEDDING_PROVIDER).lower().strip()

    # Hard guard: force MockEmbeddingProvider during pytest runs
    if settings.ENV.lower() == "test" or target == "mock":
        return MockEmbeddingProvider(vector_dim=384)

    if target == "fastembed":
        return FastEmbedProvider()

    logger.warning(f"Unknown embedding provider '{target}'. Defaulting to MockEmbeddingProvider.")
    return MockEmbeddingProvider(vector_dim=384)
