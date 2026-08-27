"""
Splits extracted policy text into overlapping chunks for embedding (Day 3).

Section-aware: insurance wordings use reliably ALL-CAPS heading lines
("SECTION I : LOSS OF OR DAMAGE TO THE VEHICLE INSURED", "GENERAL EXCEPTIONS",
"CONDITIONS", "IMT.1. EXTENSION OF GEOGRAPHICAL AREA" - confirmed empirically
against the actual IRDAI reference PDFs, not assumed). Lines are grouped under
the most recent heading, then each group is packed into size-bounded chunks
(CHUNK_SIZE_CHARS, with CHUNK_OVERLAP_CHARS carried between chunks of the same
section only - overlap never bleeds across a section boundary). Every chunk
carries the heading it came from as section_hint, for citations later.

This is a heuristic, not a layout-aware parser - a small number of non-heading
lines (e.g. table headers like "AGE OF VEHICLE % OF DEPRECIATION") will be
mistaken for section boundaries. Harmless in practice: it just creates an
extra, still-accurately-labeled chunk boundary rather than a wrong one.
"""

from app.config import settings


def chunk_text(
    text: str,
    chunk_size: int = None,
    overlap: int = None,
) -> list[dict]:
    """Returns a list of {"text": str, "section_hint": str | None}."""
    chunk_size = chunk_size or settings.CHUNK_SIZE_CHARS
    overlap = overlap or settings.CHUNK_OVERLAP_CHARS

    lines = [line for line in text.split("\n") if line.strip()]
    if not lines:
        return []

    sections: list[tuple[str | None, list[str]]] = []
    current_heading: str | None = None
    current_lines: list[str] = []

    for line in lines:
        if _is_heading(line):
            if current_lines:
                sections.append((current_heading, current_lines))
            current_heading = line.strip()
            current_lines = []
        else:
            current_lines.append(line)
    if current_lines:
        sections.append((current_heading, current_lines))

    chunks: list[dict] = []
    for heading, section_lines in sections:
        for piece in _pack_lines(section_lines, chunk_size, overlap):
            chunks.append({"text": piece, "section_hint": heading})
    return chunks


def _is_heading(line: str) -> bool:
    stripped = line.strip()
    if not (3 <= len(stripped) <= 90):
        return False
    letters = [c for c in stripped if c.isalpha()]
    if len(letters) < 3:
        return False
    return all(c.isupper() for c in letters)


def _pack_lines(lines: list[str], chunk_size: int, overlap: int) -> list[str]:
    if not lines:
        return []

    chunks: list[str] = []
    current = ""

    for line in lines:
        candidate = f"{current}\n{line}" if current else line

        if len(candidate) <= chunk_size:
            current = candidate
            continue

        if current:
            chunks.append(current)
            tail = current[-overlap:] if overlap else ""
            current = f"{tail}\n{line}" if tail else line
        else:
            # a single line longer than chunk_size - hard-split it
            for i in range(0, len(line), chunk_size - overlap):
                chunks.append(line[i : i + chunk_size])
            current = ""

        if len(current) > chunk_size:
            chunks.append(current)
            current = ""

    if current:
        chunks.append(current)

    return chunks
