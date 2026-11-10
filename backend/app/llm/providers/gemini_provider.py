"""
Google Gemini provider (public cloud LLM, has a free tier — handy for hosting
the demo online).

Gemini exposes an OpenAI-compatible endpoint, so this reuses the `openai` SDK
pointed at Google's base URL. The key is read only from GEMINI_API_KEY.
Embeddings use the local hashing embedder, like the Grok provider, so RAG
keeps working without a separate embeddings quota.
"""
import re

from openai import OpenAI

from app.llm.base import LLMProvider
from app.llm.local_embeddings import embed_texts

GEMINI_OPENAI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"


class GeminiProvider(LLMProvider):
    def __init__(self, api_key: str, model: str):
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not set. Add it to your .env file (LLM_PROVIDER=gemini).")
        self.model = model
        self.client = OpenAI(api_key=api_key, base_url=GEMINI_OPENAI_BASE_URL)

    def complete(
        self,
        messages: list[dict],
        *,
        temperature: float = 0.3,
        max_tokens: int = 1500,
        json_mode: bool = False,
    ) -> str:
        kwargs = {}
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )
        text = response.choices[0].message.content or ""
        if json_mode:  # some models wrap JSON in ```json fences
            text = re.sub(r"^\s*```(?:json)?\s*|\s*```\s*$", "", text)
        return text

    def embed(self, texts: list[str]) -> list[list[float]]:
        return embed_texts(texts)
