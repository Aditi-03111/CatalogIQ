"""
FastEmbed embedding provider for local development.
Uses fastembed package if available, or falls back gracefully to local deterministic vector generation.
"""
import logging
from typing import List, Optional

from app.services.embeddings.base import BaseEmbeddingProvider
from app.services.embeddings.mock_provider import MockEmbeddingProvider

logger = logging.getLogger(__name__)


class FastEmbedProvider(BaseEmbeddingProvider):
    """
    Local embedding provider using fastembed (BAAI/bge-small-en-v1.5, 384 dim).
    Falls back to mock provider if fastembed package or model is unavailable.
    """

    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5"):
        self._model_name = model_name
        self._fastembed_model = None
        self._fallback_provider = None
        self._dim = 384

        try:
            from fastembed import TextEmbedding
            self._fastembed_model = TextEmbedding(model_name=self._model_name)
            # Test dimension
            test_vec = list(next(self._fastembed_model.embed(["test"])))
            self._dim = len(test_vec)
            logger.info(f"Initialized FastEmbed model '{self._model_name}' (dim={self._dim})")
        except Exception as e:
            logger.warning(
                f"FastEmbed initialization failed ({e}). Falling back to deterministic embedding provider."
            )
            self._fallback_provider = MockEmbeddingProvider(
                vector_dim=384, model_name=f"fastembed-fallback-{model_name}"
            )

    @property
    def provider_name(self) -> str:
        return "fastembed"

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimension(self) -> int:
        return self._dim

    def embed_text(self, text: str) -> List[float]:
        if self._fastembed_model:
            try:
                embeddings = list(self._fastembed_model.embed([text]))
                return [float(x) for x in embeddings[0]]
            except Exception as e:
                logger.error(f"FastEmbed inference error: {e}. Using fallback.")
        
        if not self._fallback_provider:
            self._fallback_provider = MockEmbeddingProvider(vector_dim=self._dim)
        return self._fallback_provider.embed_text(text)

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        if self._fastembed_model:
            try:
                embeddings = list(self._fastembed_model.embed(texts))
                return [[float(x) for x in emb] for emb in embeddings]
            except Exception as e:
                logger.error(f"FastEmbed batch inference error: {e}. Using fallback.")

        if not self._fallback_provider:
            self._fallback_provider = MockEmbeddingProvider(vector_dim=self._dim)
        return self._fallback_provider.embed_batch(texts)
