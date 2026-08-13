import json
import requests

from app.llm.base import LLMProvider
from app.llm.local_embeddings import embed_texts


class OllamaProvider(LLMProvider):
    """Local, keyless provider — talks to a locally running `ollama serve`."""

    def __init__(self, base_url: str, model: str):
        self.base_url = base_url.rstrip("/")
        self.model = model

    def complete(
        self,
        messages: list[dict],
        *,
        temperature: float = 0.3,
        max_tokens: int = 1500,
        json_mode: bool = False,
    ) -> str:
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        if json_mode:
            payload["format"] = "json"
        resp = requests.post(f"{self.base_url}/api/chat", json=payload, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        return data.get("message", {}).get("content", "")

    def embed(self, texts: list[str]) -> list[list[float]]:
        # If the user has an embedding-capable model pulled in Ollama, this could
        # call /api/embeddings instead. Default to the local fallback for simplicity.
        return embed_texts(texts)
