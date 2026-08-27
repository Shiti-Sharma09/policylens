"""
Embedding service wrapping Ollama's /api/embed endpoint (qwen3-embedding:0.6b, 1024-dim
- confirmed empirically, see CLAUDE.md).

Measured on this machine's CPU: ~3s/chunk (~60-65 tok/s), so a full policy's 60-90 chunks
takes 3-5 minutes. A single request for 90 chunks in one call was tested and timed out
past 3 minutes - requests are batched to keep each Ollama call bounded and responsive.
Never call this synchronously inside an HTTP request handler; see app/services/indexing.py,
which is designed to run as a background task.
"""

import httpx

from app.config import settings

_BATCH_SIZE = 16
_TIMEOUT_SECONDS = 180.0


def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []

    embeddings: list[list[float]] = []
    for i in range(0, len(texts), _BATCH_SIZE):
        batch = texts[i : i + _BATCH_SIZE]
        response = httpx.post(
            f"{settings.OLLAMA_HOST}/api/embed",
            json={"model": settings.OLLAMA_EMBEDDING_MODEL, "input": batch},
            timeout=_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        embeddings.extend(response.json()["embeddings"])
    return embeddings


def embed_text(text: str) -> list[float]:
    return embed_texts([text])[0]
