"""
Provider-agnostic LLM interface.

Every concrete provider (Grok, OpenAI, Ollama, ...) implements this same
interface. The rest of the application — the RAG engine, the LangGraph
agent, every tutor tool — talks ONLY to `LLMProvider`, never to a vendor
SDK directly. Switching providers is a matter of changing LLM_PROVIDER in
.env; no application code changes.
"""
from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """Common interface every LLM backend must implement."""

    @abstractmethod
    def complete(
        self,
        messages: list[dict],
        *,
        temperature: float = 0.3,
        max_tokens: int = 1500,
        json_mode: bool = False,
    ) -> str:
        """
        messages: list of {"role": "system"|"user"|"assistant", "content": str}
        Returns the assistant's text response.
        If json_mode=True, the provider should do its best to return valid JSON text
        (via native JSON-mode support if available, or a strong system-prompt nudge).
        """
        raise NotImplementedError

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return an embedding vector per input text, used for RAG retrieval."""
        raise NotImplementedError
