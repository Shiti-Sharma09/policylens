import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlmodel import Session, select

from app.config import settings
from app.db import get_session
from app.dependencies import get_current_user
from app.models.models import Policy, PolicyChunkMeta, User
from app.services.chunk_store import save_chunks
from app.services.chunking import chunk_text
from app.services.file_storage import save_encrypted_pdf
from app.services.pdf_extraction import extract_text_from_pdf_bytes

router = APIRouter(prefix="/upload", tags=["upload"])


class PolicyResponse(BaseModel):
    id: int
    filename: str
    structural_type: str | None
    insurer: str | None
    is_reference_doc: bool
    chunk_count: int


@router.get("/ping")
def ping():
    return {"router": "upload", "status": "stub"}


@router.post("/policy", response_model=PolicyResponse, status_code=status.HTTP_201_CREATED)
async def upload_policy(
    file: UploadFile = File(...),
    structural_type: str | None = Form(None),
    insurer: str | None = Form(None),
    is_reference_doc: bool = Form(False),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only PDF files are accepted")

    raw_bytes = await file.read()
    max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
    if len(raw_bytes) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds {settings.MAX_UPLOAD_MB}MB limit",
        )

    text = extract_text_from_pdf_bytes(raw_bytes)
    if not text:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No extractable text found in PDF (scanned/image-only PDFs aren't supported yet)",
        )

    save_encrypted_pdf(raw_bytes)

    policy = Policy(
        user_id=current_user.id,
        filename=file.filename,
        structural_type=structural_type,
        insurer=insurer,
        is_reference_doc=is_reference_doc,
    )
    session.add(policy)
    session.commit()
    session.refresh(policy)

    chunks = chunk_text(text)
    staged_chunks = []
    for i, chunk in enumerate(chunks):
        point_id = str(uuid.uuid4())
        session.add(
            PolicyChunkMeta(
                policy_id=policy.id,
                qdrant_point_id=point_id,
                chunk_index=i,
                section_hint=chunk["section_hint"],
            )
        )
        staged_chunks.append(
            {
                "qdrant_point_id": point_id,
                "chunk_index": i,
                "text": chunk["text"],
                "section_hint": chunk["section_hint"],
            }
        )
    session.commit()

    save_chunks(policy.id, staged_chunks)

    return PolicyResponse(
        id=policy.id,
        filename=policy.filename,
        structural_type=policy.structural_type,
        insurer=policy.insurer,
        is_reference_doc=policy.is_reference_doc,
        chunk_count=len(chunks),
    )


@router.get("/policies", response_model=list[PolicyResponse])
def list_policies(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    policies = session.exec(select(Policy).where(Policy.user_id == current_user.id)).all()
    result = []
    for policy in policies:
        chunk_count = len(
            session.exec(select(PolicyChunkMeta).where(PolicyChunkMeta.policy_id == policy.id)).all()
        )
        result.append(
            PolicyResponse(
                id=policy.id,
                filename=policy.filename,
                structural_type=policy.structural_type,
                insurer=policy.insurer,
                is_reference_doc=policy.is_reference_doc,
                chunk_count=chunk_count,
            )
        )
    return result
