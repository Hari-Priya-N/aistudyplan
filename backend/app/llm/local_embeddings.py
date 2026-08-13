"""
Local embedding fallback -- no network access, no model download required.

Not every LLM provider offers an embeddings endpoint (Grok/xAI does not at
the time of writing; a local Ollama model may not either). Rather than make
RAG availability depend on downloading a model file from the internet at
runtime (which fails in network-restricted / air-gapped environments), this
uses a deterministic hashing-trick bag-of-words vectorizer: every token is
hashed into one of N dimensions, sign-weighted to reduce collision bias,
then L2-normalized. Cosine similarity over these vectors behaves like a
keyword/overlap similarity measure -- it is what the doc's RAG section
calls the "keyword fallback" retrieval path, used here as the default so
the whole ingestion -> retrieval pipeline works offline out of the box.

For production-grade *semantic* retrieval, prefer a provider with a real
embeddings API (OpenAIProvider already calls text-embedding-3-small) or
swap this module for a downloaded sentence-transformers model once network
access to the model host is available.
"""
import hashlib
import math
import re

DIMENSIONS = 384  # matches common small-embedding-model size for drop-in compatibility

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


def _hash_index(token: str) -> int:
    return int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16) % DIMENSIONS


def _hash_sign(token: str) -> int:
    return 1 if int(hashlib.md5((token + "_sign").encode("utf-8")).hexdigest(), 16) % 2 == 0 else -1


def _embed_one(text: str) -> list[float]:
    vec = [0.0] * DIMENSIONS
    for tok in _tokenize(text):
        idx = _hash_index(tok)
        vec[idx] += _hash_sign(tok)
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def embed_texts(texts: list[str]) -> list[list[float]]:
    return [_embed_one(t) for t in texts]
