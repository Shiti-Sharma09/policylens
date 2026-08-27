"""PDF text extraction, using pdfplumber for layout-aware text pulls."""

import io
import re
from collections import Counter

import pdfplumber

# A line repeated on this fraction of pages or more is treated as a running
# header/footer/watermark (e.g. "Visit Help Section on www.hdfcergo.com...")
# rather than policy content, and stripped before chunking sees it.
_BOILERPLATE_THRESHOLD = 0.3
_MIN_PAGES_FOR_BOILERPLATE_DETECTION = 4


def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        page_texts = [page.extract_text() or "" for page in pdf.pages]
    page_texts = [t for t in page_texts if t.strip()]

    boilerplate = _detect_boilerplate_lines(page_texts)

    cleaned_pages = []
    for page_text in page_texts:
        kept_lines = [
            line for line in page_text.split("\n") if line.strip() and line.strip() not in boilerplate
        ]
        cleaned_pages.append("\n".join(kept_lines))

    full_text = "\n\n".join(cleaned_pages)
    # Collapse repeated whitespace left over from PDF layout artifacts, but keep paragraph breaks.
    full_text = re.sub(r"[ \t]+", " ", full_text)
    full_text = re.sub(r"\n{3,}", "\n\n", full_text)
    return full_text.strip()


def _detect_boilerplate_lines(page_texts: list[str]) -> set[str]:
    num_pages = len(page_texts)
    if num_pages < _MIN_PAGES_FOR_BOILERPLATE_DETECTION:
        return set()

    line_page_counts = Counter()
    for page_text in page_texts:
        unique_lines_on_page = {line.strip() for line in page_text.split("\n") if line.strip()}
        line_page_counts.update(unique_lines_on_page)

    return {
        line
        for line, count in line_page_counts.items()
        if count / num_pages >= _BOILERPLATE_THRESHOLD
    }
