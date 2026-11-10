"""
Single point where LLM_PROVIDER (env var) is turned into a concrete
LLMProvider instance. Nothing else in the codebase should import a
provider class directly or check `settings.llm_provider` — always go
through `get_llm_provider()`.
"""
from functools import lru_cache

from app.core.config import get_settings
from app.llm.base import LLMProvider


@lru_cache
def get_llm_provider() -> LLMProvider:
    settings = get_settings()

    if settings.llm_provider == "grok":
        from app.llm.providers.grok import GrokProvider
        return GrokProvider(api_key=settings.grok_api_key, model=settings.llm_model)

    if settings.llm_provider == "openai":
        from app.llm.providers.openai_provider import OpenAIProvider
        return OpenAIProvider(
            api_key=settings.openai_api_key, model=settings.llm_model, base_url=settings.openai_base_url
        )

    if settings.llm_provider == "gemini":
        from app.llm.providers.gemini_provider import GeminiProvider
        model = settings.llm_model if settings.llm_model.startswith("gemini") else "gemini-2.5-flash"
        return GeminiProvider(api_key=settings.gemini_api_key, model=model)

    if settings.llm_provider == "ollama":
        from app.llm.providers.ollama_provider import OllamaProvider
        return OllamaProvider(base_url=settings.ollama_base_url, model=settings.ollama_model)

    if settings.llm_provider == "mock":
        from app.llm.providers.mock_provider import MockProvider
        return MockProvider(model=settings.llm_model)

    raise ValueError(f"Unknown LLM_PROVIDER: {settings.llm_provider!r}")
