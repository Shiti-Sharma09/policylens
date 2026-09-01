"""
Chat completion wrapper for Ollama's /api/chat (qwen3:8b).

Qwen3's default "thinking" mode was measured at 27+ minutes for a single answer versus
~20s with it disabled (see CLAUDE.md's "Validated on actual hardware" note) - think:false
is a hard requirement for every call here, not a tunable default. Even with thinking off,
real answers take ~20-90s on this CPU-only machine; callers must show a loading state,
not assume this is fast.
"""

import httpx

from app.config import settings

# A real RAG answer (~250-300 output tokens, grounded in retrieved context) was measured
# at 134s end-to-end on this CPU-only machine - notably longer than Day 1's ~20-90s
# estimate, which was based on a short-answer test prompt, not a full RAG-context one.
# 300s gives real answers headroom without cutting them off.
_TIMEOUT_SECONDS = 300.0


def chat(messages: list[dict]) -> str:
    response = httpx.post(
        f"{settings.OLLAMA_HOST}/api/chat",
        json={
            "model": settings.OLLAMA_LLM_MODEL,
            "messages": messages,
            "think": settings.OLLAMA_THINK,
            "stream": False,
        },
        timeout=_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return response.json()["message"]["content"]
