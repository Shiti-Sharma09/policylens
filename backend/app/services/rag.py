"""
Policy RAG: retrieval (Day 3) + grounded answer generation (Day 4).

Never fabricates claim-approval language - the prompt explicitly frames answers as
advisory ("this appears to be covered under...") and defers final say to the insurer,
per this project's working conventions (see CLAUDE.md).
"""

from collections.abc import Iterator

from qdrant_client.models import FieldCondition, Filter, MatchValue

from app.services.embeddings import embed_text
from app.services.llm import chat, chat_stream
from app.services.vectorstore import COLLECTION_NAME, get_qdrant_client

SYSTEM_PROMPT = """You are an assistant that answers questions about a vehicle insurance policy, using ONLY the policy excerpts provided in the user's message.

Rules:
- Answer using only the information in the excerpts below. If the excerpts don't contain enough information to answer, say so plainly - do not guess or use outside knowledge about insurance in general.
- Never state or imply that a specific claim will be approved, rejected, or paid out. You may explain what the policy text appears to cover or exclude, but always make clear that the insurer has final say on any actual claim.
- When you use information from an excerpt, mention which section it came from if a section name is given.
- Keep the answer concise and in plain language a non-expert can follow."""


def retrieve_chunks(policy_id: int, query: str, top_k: int = 5) -> list[dict]:
    query_vector = embed_text(query)
    response = get_qdrant_client().query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        query_filter=Filter(must=[FieldCondition(key="policy_id", match=MatchValue(value=policy_id))]),
        limit=top_k,
    )
    return [
        {
            "chunk_text": point.payload["chunk_text"],
            "section_hint": point.payload.get("section_hint"),
            "chunk_index": point.payload["chunk_index"],
            "score": point.score,
        }
        for point in response.points
    ]


def _build_messages(question: str, chunks: list[dict]) -> list[dict]:
    context = "\n\n---\n\n".join(
        f"[Section: {chunk['section_hint'] or 'Unknown'}]\n{chunk['chunk_text']}" for chunk in chunks
    )
    user_content = f"Policy excerpts:\n\n{context}\n\nQuestion: {question}"
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]


_ADVISORY_DISCLAIMER = (
    "\n\n*This is general information based on your policy text, not a claim decision "
    "- the insurer has final say on any actual claim.*"
)


def generate_answer(question: str, chunks: list[dict]) -> str:
    """Never relies on the LLM to remember the advisory framing on its own - the
    disclaimer is appended in code, deterministically, on every real answer."""
    if not chunks:
        return "I couldn't find anything in this policy relevant to that question."
    answer = chat(_build_messages(question, chunks))
    return answer + _ADVISORY_DISCLAIMER


def generate_answer_stream(question: str, chunks: list[dict]) -> Iterator[str]:
    """Same grounded-answer generation as generate_answer(), but yields the answer
    incrementally as Ollama streams tokens, so callers (POST /ask/stream) can forward
    each piece to the frontend for a typing effect instead of blocking the full
    20-90s+ wait. Yields the disclaimer as a final piece too - concatenating
    everything this yields reconstructs the exact same string generate_answer()
    would have returned."""
    if not chunks:
        yield "I couldn't find anything in this policy relevant to that question."
        return
    for token in chat_stream(_build_messages(question, chunks)):
        yield token
    yield _ADVISORY_DISCLAIMER
