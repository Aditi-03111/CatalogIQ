"""
Base abstract interface for embedding providers.
"""
from abc import ABC, abstractmethod
from typing import List


class BaseEmbeddingProvider(ABC):
    """
    Abstract interface for embedding generation providers.

    All embedding implementations (Mock, FastEmbed, Gemini, Ollama, etc.)
    must inherit from this base class to ensure provider independence.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable provider identifier (e.g. 'mock', 'fastembed')."""
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Model identifier (e.g. 'BAAI/bge-small-en-v1.5', 'text-embedding-3-small')."""
        ...

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Dimension size of vector outputs (e.g. 384, 1536)."""
        ...

    @abstractmethod
    def embed_text(self, text: str) -> List[float]:
        """
        Generates a vector embedding for a single string.

        Args:
            text: The text representation to embed.

        Returns:
            List of floats representing normalized vector embedding.
        """
        ...

    @abstractmethod
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generates vector embeddings for a list of strings.

        Args:
            texts: List of text strings to embed.

        Returns:
            List of vector float lists.
        """
        ...
