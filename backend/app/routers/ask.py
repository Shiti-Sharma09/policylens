from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from qdrant_client.models import FieldCondition, Filter, MatchValue
from sqlmodel import Session

from app.db import get_session
from app.dependencies import get_current_user
from app.models.models import Policy, User
from app.services.embeddings import embed_text
from app.services.vectorstore import COLLECTION_NAME, get_qdrant_client

router = APIRouter(prefix="/ask", tags=["ask"])


@router.get("/ping")
def ping():
    return {"router": "ask", "status": "stub"}


class RetrieveRequest(BaseModel):
    policy_id: int
    query: str
    top_k: int = 5


class RetrievedChunk(BaseModel):
    chunk_text: str
    section_hint: str | None
    chunk_index: int
    score: float


@router.post("/retrieve", response_model=list[RetrievedChunk])
def retrieve(
    body: RetrieveRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Raw retrieval, no LLM yet (Day 3) - embeds the query and returns the top-k most
    similar chunks for one policy, with citation metadata (section_hint, chunk_index)."""
    policy = session.get(Policy, body.policy_id)
    if policy is None or (policy.user_id != current_user.id and not policy.is_reference_doc):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found")
    if policy.indexed_at is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Policy is still being indexed - try again in a minute",
        )

    query_vector = embed_text(body.query)
    response = get_qdrant_client().query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        query_filter=Filter(must=[FieldCondition(key="policy_id", match=MatchValue(value=body.policy_id))]),
        limit=body.top_k,
    )

    return [
        RetrievedChunk(
            chunk_text=point.payload["chunk_text"],
            section_hint=point.payload.get("section_hint"),
            chunk_index=point.payload["chunk_index"],
            score=point.score,
        )
        for point in response.points
    ]
