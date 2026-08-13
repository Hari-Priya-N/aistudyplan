import re
from pypdf import PdfReader


def extract_text_from_pdf(file_path: str) -> str:
    reader = PdfReader(file_path)
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n\n".join(pages)


def extract_text(file_path: str, filename: str) -> str:
    if filename.lower().endswith(".pdf"):
        return extract_text_from_pdf(file_path)
    # .txt / .json / plain text fallback
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def chunk_text(text: str, target_chars: int = 1200, overlap: int = 150) -> list[str]:
    """
    Semantically-aware chunking: split on paragraph/heading boundaries first,
    then greedily pack paragraphs into chunks near `target_chars`, so chunks
    stay coherent instead of cutting mid-sentence (fixed-length windows).
    """
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]

    chunks: list[str] = []
    current = ""
    for para in paragraphs:
        if len(current) + len(para) + 2 <= target_chars:
            current = f"{current}\n\n{para}" if current else para
        else:
            if current:
                chunks.append(current)
            # carry a small overlap forward for continuity
            tail = current[-overlap:] if current else ""
            current = f"{tail}\n\n{para}" if tail else para
    if current:
        chunks.append(current)

    return chunks or ([text] if text.strip() else [])
