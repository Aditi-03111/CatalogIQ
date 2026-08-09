"""
LLM Provider package for CatalogIQ AI extraction.

Provides:
  - BaseLLMProvider     — abstract interface all providers implement
  - ExtractionResult    — validated Pydantic output model
  - get_llm_provider()  — factory function that reads settings

Usage:
    from app.services.llm import get_llm_provider
    provider = get_llm_provider()
    result = provider.extract(parsed_ir)
"""
from .base import BaseLLMProvider, ExtractionResult, RawAttributeItem
from .factory import get_llm_provider

__all__ = [
    "BaseLLMProvider",
    "ExtractionResult",
    "RawAttributeItem",
    "get_llm_provider",
]
