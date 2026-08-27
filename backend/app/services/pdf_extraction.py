"""PDF text extraction, using pdfplumber for layout-aware text pulls."""

import io
import re

import pdfplumber


def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    pages = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            if text.strip():
                pages.append(text)

    full_text = "\n\n".join(pages)
    # Collapse repeated whitespace left over from PDF layout artifacts, but keep paragraph breaks.
    full_text = re.sub(r"[ \t]+", " ", full_text)
    full_text = re.sub(r"\n{3,}", "\n\n", full_text)
    return full_text.strip()
