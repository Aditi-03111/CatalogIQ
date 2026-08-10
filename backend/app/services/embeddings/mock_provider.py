"""
Mock embedding provider for tests and offline development.
Generates deterministic, L2-normalized float vectors from text SHA-256 hashes.
"""
import hashlib
import math
from typing import List

from app.services.embeddings.base import BaseEmbeddingProvider


class MockEmbeddingProvider(BaseEmbeddingProvider):
    """
    Deterministic mock provider producing unit-length float vectors.
    Used during unit tests (ENV=test) or when EMBEDDING_PROVIDER=mock.
    """

    def __init__(self, vector_dim: int = 384, model_name: str = "mock-bge-small-en-v1.5"):
        self._dim = vector_dim
        self._model_name = model_name

    @property
    def provider_name(self) -> str:
        return "mock"

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimension(self) -> int:
        return self._dim

    def embed_text(self, text: str) -> List[float]:
        """Generate deterministic pseudo-random unit vector based on input text hash."""
        if not text:
            # Zero vector fallback for empty text
            return [0.0] * self._dim

        # Compute multi-chunk SHA-256 digest to fill vector_dim elements deterministically
        raw_vals: List[float] = []
        salt = 0
        while len(raw_vals) < self._dim:
            seed_str = f"{text}:{salt}"
            digest = hashlib.sha256(seed_str.encode("utf-8")).digest()
            # Extract floats from byte digest
            for i in range(0, len(digest) - 1, 2):
                val = ((digest[i] << 8) | digest[i + 1]) / 65535.0 - 0.5
                raw_vals.append(val)
                if len(raw_vals) == self._dim:
                    break
            salt += 1

        # L2-normalize
        norm = math.sqrt(sum(v * v for v in raw_vals))
        if norm > 0:
            return [v / norm for v in raw_vals]
        return [1.0 / math.sqrt(self._dim)] * self._dim

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        return [self.embed_text(t) for t in texts]
