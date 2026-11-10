from openai import OpenAI

from app.llm.base import LLMProvider


class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str, model: str, base_url: str | None = None):
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY is not set. Add it to your .env file (LLM_PROVIDER=openai)."
            )
        self.model = model
        # base_url lets this provider talk to any OpenAI-compatible server
        # (Groq, Together, vLLM, LM Studio ...). Those servers usually lack the
        # embeddings model below, so fall back to local embeddings for them.
        self.base_url = base_url
        self.client = OpenAI(api_key=api_key, base_url=base_url) if base_url else OpenAI(api_key=api_key)

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
        if self.base_url:
            from app.llm.local_embeddings import embed_texts
            return embed_texts(texts)
        response = self.client.embeddings.create(
            model="text-embedding-3-small", input=texts
        )
        return [d.embedding for d in response.data]
