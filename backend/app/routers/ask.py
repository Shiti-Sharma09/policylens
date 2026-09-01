import hashlib
import json

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel import Session, select

from app.db import get_session
from app.dependencies import get_current_user
from app.models.models import AnswerCache, Policy, User
from app.services.rag import generate_answer, retrieve_chunks

router = APIRouter(prefix="/ask", tags=["ask"])


@router.get("/ping")
def ping():
    return {"router": "ask", "status": "stub"}


class RetrievedChunk(BaseModel):
    chunk_text: str
    section_hint: str | None
    chunk_index: int
    score: float


def _get_accessible_policy(session: Session, policy_id: int, current_user: User) -> Policy:
    policy = session.get(Policy, policy_id)
    if policy is None or (policy.user_id != current_user.id and not policy.is_reference_doc):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found")
    if policy.indexed_at is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Policy is still being indexed - try again in a minute",
        )
    return policy


class RetrieveRequest(BaseModel):
    policy_id: int
    query: str
    top_k: int = 5


@router.post("/retrieve", response_model=list[RetrievedChunk])
def retrieve(
    body: RetrieveRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Raw retrieval, no LLM (Day 3) - embeds the query and returns the top-k most
    similar chunks for one policy, with citation metadata (section_hint, chunk_index)."""
    _get_accessible_policy(session, body.policy_id, current_user)
    chunks = retrieve_chunks(body.policy_id, body.query, body.top_k)
    return [RetrievedChunk(**chunk) for chunk in chunks]


class AskRequest(BaseModel):
    policy_id: int
    question: str
    top_k: int = 5


class AskResponse(BaseModel):
    answer: str
    citations: list[RetrievedChunk]
    cached: bool


def _hash_question(question: str) -> str:
    normalized = question.strip().lower()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


@router.post("", response_model=AskResponse)
def ask(
    body: AskRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Retrieve + Qwen3-8B (think:false) -> a grounded answer with citations.
    Real answers take ~20-90s on this CPU-only machine - callers must show a loading
    state, not assume this is fast. Identical (policy_id, question) pairs are cached."""
    _get_accessible_policy(session, body.policy_id, current_user)

    question_hash = _hash_question(body.question)
    cached = session.exec(
        select(AnswerCache).where(
            AnswerCache.policy_id == body.policy_id, AnswerCache.question_hash == question_hash
        )
    ).first()
    if cached:
        return AskResponse(answer=cached.answer, citations=json.loads(cached.citations_json), cached=True)

    chunks = retrieve_chunks(body.policy_id, body.question, body.top_k)
    answer = generate_answer(body.question, chunks)

    session.add(
        AnswerCache(
            policy_id=body.policy_id,
            question_hash=question_hash,
            question=body.question,
            answer=answer,
            citations_json=json.dumps(chunks),
        )
    )
    session.commit()

    return AskResponse(answer=answer, citations=[RetrievedChunk(**chunk) for chunk in chunks], cached=False)
