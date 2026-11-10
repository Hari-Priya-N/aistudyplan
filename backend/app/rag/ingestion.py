import uuid
from sqlalchemy.orm import Session

from app import models
from app.llm.factory import get_llm_provider
from app.rag.chunking import extract_text, chunk_text
from app.rag.topic_extraction import extract_knowledge_graph
from app.rag.vector_store import add_chunks


def ingest_document(db: Session, document: models.Document, file_path: str, user_id: str):
    """
    Runs the full pipeline described in the doc's Data Ingestion section:
    parse -> chunk -> topic extraction (knowledge graph) -> vectorization.
    Any re-upload of a document should call this again (refresh).
    """
    try:
        raw_text = extract_text(file_path, document.filename)
        chunks = chunk_text(raw_text)

        llm = get_llm_provider()

        # --- Topic extraction -> knowledge graph stored in the relational DB ---
        topic_tree = extract_knowledge_graph(llm, raw_text)
        order = 0
        for topic_data in topic_tree:
            parent_topic = models.Topic(
                document_id=document.id,
                title=topic_data.get("title", "Untitled Topic"),
                difficulty=topic_data.get("difficulty", "medium"),
                order_index=order,
            )
            db.add(parent_topic)
            db.flush()  # get parent_topic.id before adding children
            order += 1

            for sub in topic_data.get("subtopics", []):
                child = models.Topic(
                    document_id=document.id,
                    parent_id=parent_topic.id,
                    title=sub.get("title", "Untitled Subtopic"),
                    difficulty=sub.get("difficulty", "medium"),
                    order_index=order,
                )
                db.add(child)
                order += 1

        db.commit()

        # --- Vectorization -> chunks stored in Chroma for RAG retrieval ---
        store_chunks(db, llm, document, chunks, user_id)

        document.status = "ready"
        db.add(document)
        db.commit()

    except Exception as exc:  # noqa: BLE001 — ingestion must never crash the request thread
        document.status = "failed"
        db.add(document)
        db.commit()
        raise exc


def store_chunks(db: Session, llm, document: models.Document, chunks: list[str], user_id: str):
    """Save chunks to the DB (durable copy) and to Chroma (vector index)."""
    if not chunks:
        return
    ids = [str(uuid.uuid4()) for _ in chunks]
    for i, (cid, text) in enumerate(zip(ids, chunks)):
        db.add(models.DocumentChunk(id=cid, document_id=document.id, chunk_index=i, content=text))
    db.commit()
    embeddings = llm.embed(chunks)
    metadatas = [
        {"document_id": document.id, "user_id": user_id, "chunk_index": i} for i in range(len(chunks))
    ]
    add_chunks(ids=ids, documents=chunks, embeddings=embeddings, metadatas=metadatas)
