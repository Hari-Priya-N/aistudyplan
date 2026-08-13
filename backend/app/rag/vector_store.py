import chromadb
from chromadb import Documents, EmbeddingFunction, Embeddings
from chromadb.config import Settings as ChromaSettings
from functools import lru_cache

from app.core.config import get_settings
from app.llm.local_embeddings import embed_texts

COLLECTION_NAME = "tutor_chunks"


class _LocalEmbeddingFunction(EmbeddingFunction):
    """
    Explicit embedding function so chromadb never falls back to instantiating
    its bundled ONNX MiniLM default (which tries to download model weights
    from the internet on first use and hangs in network-restricted
    environments). We always pass embeddings explicitly on add()/query()
    anyway, from the same LLM-provider-aware embedding pipeline used
    elsewhere — this is only here to satisfy chromadb's collection API.
    """

    def __call__(self, input: Documents) -> Embeddings:
        return embed_texts(list(input))


@lru_cache
def get_chroma_client():
    settings = get_settings()
    chroma_settings = ChromaSettings(anonymized_telemetry=False)
    if settings.chroma_mode == "http":
        return chromadb.HttpClient(
            host=settings.chroma_host, port=settings.chroma_port, settings=chroma_settings
        )
    return chromadb.PersistentClient(
        path=settings.chroma_persist_dir, settings=chroma_settings
    )


def get_collection():
    client = get_chroma_client()
    return client.get_or_create_collection(
        name=COLLECTION_NAME, embedding_function=_LocalEmbeddingFunction()
    )


def add_chunks(
    ids: list[str],
    documents: list[str],
    embeddings: list[list[float]],
    metadatas: list[dict],
):
    collection = get_collection()
    collection.add(ids=ids, documents=documents, embeddings=embeddings, metadatas=metadatas)


def query_chunks(
    query_embedding: list[float],
    user_id: str,
    top_k: int = 5,
) -> dict:
    collection = get_collection()
    return collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        where={"user_id": user_id},
    )


def delete_document_chunks(document_id: str):
    collection = get_collection()
    collection.delete(where={"document_id": document_id})
