"""
Embeds a policy's staged chunks (Day 2's chunk_store JSON) and upserts them into Qdrant.

Slow by nature (~3s/chunk on this machine's CPU, see embeddings.py) - designed to be run
as a background task or standalone script, never inline in an HTTP request handler.
"""

from qdrant_client.models import PointStruct

from app.services.chunk_store import load_chunks
from app.services.embeddings import embed_texts
from app.services.vectorstore import COLLECTION_NAME, ensure_collection, get_qdrant_client


def index_policy(policy_id: int, insurer: str | None, structural_type: str | None) -> int:
    """Returns the number of chunks indexed (0 if the policy has no staged chunks)."""
    chunks = load_chunks(policy_id)
    if not chunks:
        return 0

    ensure_collection()
    # Embed the section heading together with the body - tested empirically (see
    # PROGRESS.md's Day 3 notes): a query like "what is covered under third party
    # liability" scored a relevant chunk BELOW an irrelevant one (0.478 vs 0.485)
    # when only the body was embedded, since the chunk text itself never repeats
    # the heading's keywords. Prepending the heading raised the relevant chunk's
    # score to 0.584, clearly ahead of the irrelevant chunk. chunk_text in the
    # payload stays heading-free - that's for display, not for embedding.
    embed_inputs = [
        f"{chunk['section_hint']}\n\n{chunk['text']}" if chunk.get("section_hint") else chunk["text"]
        for chunk in chunks
    ]
    vectors = embed_texts(embed_inputs)

    points = [
        PointStruct(
            id=chunk["qdrant_point_id"],
            vector=vector,
            payload={
                "policy_id": policy_id,
                "chunk_index": chunk["chunk_index"],
                "chunk_text": chunk["text"],
                "section_hint": chunk.get("section_hint"),
                "insurer": insurer,
                "structural_type": structural_type,
            },
        )
        for chunk, vector in zip(chunks, vectors)
    ]
    get_qdrant_client().upsert(collection_name=COLLECTION_NAME, points=points)
    return len(points)
