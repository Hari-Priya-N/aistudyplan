import re

from app.llm.base import LLMProvider
from app.rag.vector_store import query_chunks

SYNTHESIS_SYSTEM_PROMPT = """You are a citation-grounded tutor. Answer the student's question \
using ONLY the provided source excerpts. Every claim must be traceable to a source. \
If the excerpts don't contain enough information to answer confidently, say so plainly \
instead of guessing. After your answer, do not fabricate sources beyond the ones given."""

# Chroma returns cosine distance; below this distance we treat the top match as
# "confident enough" to answer from. Above it, we decline rather than hallucinate.
CONFIDENCE_DISTANCE_THRESHOLD = 0.55

_STOPWORDS = {
    "what", "which", "when", "where", "why", "how", "does", "explain", "about", "with", "from", "that",
    "this", "there", "their", "they", "them", "into", "your", "you", "can", "could", "would", "should",
    "the", "and", "for", "are", "was", "were", "have", "has", "use", "uses", "used", "using", "between",
    "difference", "tell", "give", "show", "please", "mean", "means", "define", "work", "works",
}


def _keywords(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if len(w) > 2 and w not in _STOPWORDS}


def _keyword_overlap(question: str, documents: list[str]) -> float:
    """Share of the question's keywords found in the retrieved text (keyword fallback path)."""
    q = _keywords(question)
    if not q:
        return 0.0
    found = _keywords(" ".join(documents))
    return len(q & found) / len(q)


def answer_content_question(llm: LLMProvider, document_ids: list[str], question: str, top_k: int = 5) -> dict:
    query_embedding = llm.embed([question])[0]
    results = query_chunks(query_embedding, document_ids=document_ids, top_k=top_k)

    documents = results.get("documents", [[]])[0]
    distances = results.get("distances", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]

    # Hybrid confidence check: accept if the vector match is close OR enough of the
    # question's keywords literally appear in the retrieved excerpts.
    semantic_ok = bool(distances) and min(distances) <= CONFIDENCE_DISTANCE_THRESHOLD
    keyword_ok = _keyword_overlap(question, documents) >= 0.5
    if not documents or not (semantic_ok or keyword_ok):
        return {
            "content": (
                "I don't have enough grounded material on that yet — try uploading the "
                "relevant syllabus/notes section, or rephrase the question."
            ),
            "citations": [],
        }

    context_block = "\n\n---\n\n".join(
        f"[Source {i+1}] {doc}" for i, doc in enumerate(documents)
    )
    messages = [
        {"role": "system", "content": SYNTHESIS_SYSTEM_PROMPT},
        {"role": "user", "content": f"Sources:\n{context_block}\n\nQuestion: {question}"},
    ]
    answer = llm.complete(messages, temperature=0.2, max_tokens=800)

    citations = [
        {"source_index": i + 1, "excerpt": doc[:200], "metadata": meta}
        for i, (doc, meta) in enumerate(zip(documents, metadatas))
    ]

    # Citation enforcement: a content answer without any citation is treated as a
    # synthesis failure and retried once with a stricter instruction.
    if not citations:
        messages.append({"role": "user", "content": "Retry: you must cite at least one source."})
        answer = llm.complete(messages, temperature=0.1, max_tokens=800)

    return {"content": answer, "citations": citations}
