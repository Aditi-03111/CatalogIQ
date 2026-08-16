"""
LLM Provider factory.

Reads settings.LLM_PROVIDER and returns the correct BaseLLMProvider instance.

Rules:
  - "ollama"  → OllamaProvider (local development)
  - "gemini"  → GeminiProvider (production)
  - "mock"    → MockProvider (tests only; only valid when settings.ENV == "test")
  - Any other → raises ConfigurationError immediately

The pipeline NEVER falls back silently. A misconfigured provider is a hard failure.
"""
import logging

from app.core.config import settings
from app.services.llm.base import BaseLLMProvider, ConfigurationError

logger = logging.getLogger(__name__)


def get_llm_provider() -> BaseLLMProvider:
    """
    Factory function that instantiates and returns the configured LLM provider.

    Returns:
        BaseLLMProvider: The fully initialized provider instance.

    Raises:
        ConfigurationError:
            - If LLM_PROVIDER is an unrecognized value.
            - If LLM_PROVIDER is "mock" but ENV != "test".
            - If the selected provider fails to initialize (missing key, import error, etc.).
    """
    provider_name = settings.LLM_PROVIDER.lower().strip()

    if provider_name == "mock":
        if settings.ENV not in ["test", "development"]:
            raise ConfigurationError(
                f"LLM_PROVIDER='mock' is only permitted when ENV='test' or 'development'. "
                f"Current ENV='{settings.ENV}'. "
                f"Set LLM_PROVIDER=ollama or LLM_PROVIDER=gemini for non-test environments."
            )
        logger.info("LLM provider: MockProvider (offline playground environment)")
        from app.services.llm.mock_provider import MockProvider
        return MockProvider()

    elif provider_name == "ollama":
        logger.info(f"LLM provider: OllamaProvider (model={settings.OLLAMA_MODEL})")
        from app.services.llm.ollama_provider import OllamaProvider
        return OllamaProvider()

    elif provider_name == "gemini":
        logger.info(f"LLM provider: GeminiProvider (model={settings.GEMINI_MODEL})")
        from app.services.llm.gemini_provider import GeminiProvider
        return GeminiProvider()

    else:
        raise ConfigurationError(
            f"Unknown LLM_PROVIDER='{provider_name}'. "
            f"Valid options are: 'ollama', 'gemini', 'mock' (test only). "
            f"Update the LLM_PROVIDER environment variable."
        )
