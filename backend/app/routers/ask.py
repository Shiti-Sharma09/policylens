import hashlib
import json
from collections.abc import Iterator

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlmodel import Session, select

from app.db import engine, get_session
from app.dependencies import get_current_user
from app.models.models import AnswerCache, Policy, User
from app.services.rag import generate_answer, generate_answer_stream, retrieve_chunks

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


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


def _stream_cached(answer: str, citations: list[dict]) -> Iterator[str]:
    """A cache hit already has the full answer text in ~50ms - there's nothing to
    actually stream. We still emit it word-by-word so the frontend's typing
    animation behaves consistently whether or not this particular question was
    cached, rather than the UI needing two different rendering paths."""
    words = answer.split(" ")
    for i, word in enumerate(words):
        piece = word if i == 0 else " " + word
        yield _sse({"type": "token", "text": piece})
    yield _sse({"type": "done", "citations": citations, "cached": True})


def _stream_live(policy_id: int, question: str, question_hash: str, chunks: list[dict]) -> Iterator[str]:
    full_text = ""
    for piece in generate_answer_stream(question, chunks):
        full_text += piece
        yield _sse({"type": "token", "text": piece})

    # Opens its own session rather than reusing the request-scoped one from
    # Depends(get_session) - same pattern as upload.py's background indexing task -
    # because this generator keeps running (streaming to the client) long after a
    # request-scoped dependency would normally be torn down.
    with Session(engine) as bg_session:
        bg_session.add(
            AnswerCache(
                policy_id=policy_id,
                question_hash=question_hash,
                question=question,
                answer=full_text,
                citations_json=json.dumps(chunks),
            )
        )
        bg_session.commit()

    yield _sse({"type": "done", "citations": chunks, "cached": False})


@router.post("/stream")
def ask_stream(
    body: AskRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Same retrieval + generation as POST /ask, but as a Server-Sent Events stream:
    each answer token is pushed to the client as soon as Ollama produces it, instead
    of the client waiting the full 20-90s+ for one response body. The frontend shows
    this as a typing animation. A final `done` event carries citations and whether
    this was a cache hit, matching AskResponse's shape."""
    _get_accessible_policy(session, body.policy_id, current_user)
    question_hash = _hash_question(body.question)

    cached = session.exec(
        select(AnswerCache).where(
            AnswerCache.policy_id == body.policy_id, AnswerCache.question_hash == question_hash
        )
    ).first()
    if cached:
        citations = json.loads(cached.citations_json)
        return StreamingResponse(_stream_cached(cached.answer, citations), media_type="text/event-stream")

    chunks = retrieve_chunks(body.policy_id, body.question, body.top_k)
    return StreamingResponse(
        _stream_live(body.policy_id, body.question, question_hash, chunks),
        media_type="text/event-stream",
    )
