"""PDF processing: extract text, parse structure, and chunk semantically."""

import fitz  # PyMuPDF
from typing import Optional


def extract_text_from_pdf(file_path: str) -> list[dict]:
    """Extract text from PDF page by page using PyMuPDF.

    Returns list of {"page": int, "text": str, "title": str}
    """
    doc = fitz.open(file_path)
    pages = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text("text")  # Plain text extraction

        # Try to detect page title from first meaningful line
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        title = lines[0] if lines else f"Page {page_num + 1}"

        if text.strip():
            pages.append({
                "page": page_num + 1,
                "text": text.strip(),
                "title": title,
            })

    doc.close()
    return pages


def semantic_chunk(text: str, max_chars: int = 800, overlap_chars: int = 100) -> list[str]:
    """Split text into semantic chunks based on paragraph boundaries.

    Strategy:
    1. Split by double newline (paragraph boundaries)
    2. Merge paragraphs until hitting max_chars
    3. Add overlap from previous chunk for continuity
    """
    paragraphs = text.split("\n\n")
    paragraphs = [p.strip() for p in paragraphs if p.strip()]

    if not paragraphs:
        return []

    chunks = []
    current_chunk = ""
    overlap_text = ""

    for para in paragraphs:
        if len(current_chunk) + len(para) < max_chars:
            current_chunk += para + "\n\n"
        else:
            if current_chunk.strip():
                chunks.append(overlap_text + current_chunk.strip())
            overlap_text = current_chunk[-overlap_chars:] if len(current_chunk) > overlap_chars else current_chunk
            current_chunk = para + "\n\n"

    if current_chunk.strip():
        chunks.append(overlap_text + current_chunk.strip())

    # Filter out very short chunks
    chunks = [c for c in chunks if len(c) >= 50]

    return chunks


def process_pdf(file_path: str, max_chunk_chars: int = 800, overlap_chars: int = 100) -> list[dict]:
    """Full pipeline: extract text from PDF → semantic chunk.

    Returns list of {"index": int, "text": str, "page": int, "title": str}
    """
    pages = extract_text_from_pdf(file_path)
    all_chunks = []

    for page_data in pages:
        page_chunks = semantic_chunk(
            page_data["text"],
            max_chars=max_chunk_chars,
            overlap_chars=overlap_chars,
        )
        for chunk_text in page_chunks:
            all_chunks.append({
                "index": len(all_chunks),
                "text": chunk_text,
                "page": page_data["page"],
                "title": page_data["title"],
            })

    return all_chunks
