"""
Splits extracted policy text into overlapping chunks for embedding (Day 3).

Paragraph-aware: packs whole paragraphs into a chunk up to CHUNK_SIZE_CHARS,
then carries the trailing CHUNK_OVERLAP_CHARS of one chunk into the next so a
clause split across a chunk boundary still has surrounding context on both sides.
"""

from app.config import settings


def chunk_text(
    text: str,
    chunk_size: int = None,
    overlap: int = None,
) -> list[str]:
    chunk_size = chunk_size or settings.CHUNK_SIZE_CHARS
    overlap = overlap or settings.CHUNK_OVERLAP_CHARS

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        return []

    chunks: list[str] = []
    current = ""

    for para in paragraphs:
        candidate = f"{current}\n\n{para}" if current else para

        if len(candidate) <= chunk_size:
            current = candidate
            continue

        if current:
            chunks.append(current)
            tail = current[-overlap:] if overlap else ""
            current = f"{tail}\n\n{para}" if tail else para
        else:
            # a single paragraph longer than chunk_size - hard-split it
            for i in range(0, len(para), chunk_size - overlap):
                chunks.append(para[i : i + chunk_size])
            current = ""

        # if the hard-split path above already emitted the paragraph, don't also
        # let a too-long `current` slip through the final append below
        if len(current) > chunk_size:
            chunks.append(current)
            current = ""

    if current:
        chunks.append(current)

    return chunks
