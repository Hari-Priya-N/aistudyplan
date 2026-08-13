"""
Grok (xAI) provider.

xAI exposes an OpenAI-compatible /v1/chat/completions API, so we reuse the
`openai` SDK pointed at xAI's base URL. The API key is read only from the
GROK_API_KEY environment variable — never hardcoded.
"""
from openai import OpenAI

from app.llm.base import LLMProvider
from app.llm.local_embeddings import embed_texts


class GrokProvider(LLMProvider):
    def __init__(self, api_key: str, model: str):
        if not api_key:
            raise ValueError(
                "GROK_API_KEY is not set. Add it to your .env file (LLM_PROVIDER=grok)."
            )
        self.model = model
        self.client = OpenAI(api_key=api_key, base_url="https://api.x.ai/v1")

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
        return response.choices[0].message.content or ""

    def embed(self, texts: list[str]) -> list[list[float]]:
        # xAI has no embeddings endpoint at time of writing — use local fallback.
        return embed_texts(texts)
