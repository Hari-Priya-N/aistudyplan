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


_EMPTY = {"documents": [[]], "distances": [[]], "metadatas": [[]], "ids": [[]]}


def query_chunks(
    query_embedding: list[float],
    document_ids: list[str],
    top_k: int = 5,
) -> dict:
    """
    Search only inside the given documents — the caller passes the documents
    the current user may see (see app/services/access.py), so a student only
    ever retrieves content from their own subjects.
    """
    if not document_ids:
        return _EMPTY
    collection = get_collection()
    where = (
        {"document_id": document_ids[0]}
        if len(document_ids) == 1
        else {"document_id": {"$in": list(document_ids)}}
    )
    try:
        return collection.query(query_embeddings=[query_embedding], n_results=top_k, where=where)
    except Exception:  # e.g. empty collection / fewer chunks than top_k on old chroma
        return _EMPTY


def delete_document_chunks(document_id: str):
    collection = get_collection()
    collection.delete(where={"document_id": document_id})


def rebuild_index_if_empty(db, embed_fn) -> int:
    """
    Re-create the Chroma index from the DocumentChunk table when the index is
    empty (fresh container on a host with an ephemeral disk). Returns the
    number of chunks re-indexed.
    """
    from app import models

    collection = get_collection()
    if collection.count() > 0:
        return 0
    chunks = (
        db.query(models.DocumentChunk, models.Document.user_id)
        .join(models.Document, models.Document.id == models.DocumentChunk.document_id)
        .all()
    )
    if not chunks:
        return 0
    batch = 200
    for i in range(0, len(chunks), batch):
        part = chunks[i:i + batch]
        texts = [c.content for c, _ in part]
        add_chunks(
            ids=[c.id for c, _ in part],
            documents=texts,
            embeddings=embed_fn(texts),
            metadatas=[
                {"document_id": c.document_id, "user_id": uid, "chunk_index": c.chunk_index} for c, uid in part
            ],
        )
    return len(chunks)
