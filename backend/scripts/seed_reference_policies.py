"""
Seeds the 8 IRDAI-filed policy wordings (data/irdai_policies/) through the same
upload -> extract -> chunk -> embed -> upsert pipeline as a real user upload, tagged
is_reference_doc=True. These double as RAG test data (Day 3/4) and the gap-analysis
reference library (Day 5).

Run from backend/, with the venv active and the .venv on PATH:
    python -m scripts.seed_reference_policies

Idempotent: re-running skips any filename already seeded (by filename, not by whether
it's indexed - if you already have these 8 policies from before Day 3, use
scripts/backfill_embeddings.py to index them instead of re-running this).

Slow: embedding is ~3s/chunk on this machine's CPU (see embeddings.py), so seeding
all 8 from scratch takes ~25-30 minutes total. That's expected, not a bug.
"""

import secrets
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlmodel import Session, select

from app.db import engine, init_db
from app.models.models import Policy, PolicyChunkMeta, User
from app.security import hash_password
from app.services.chunk_store import save_chunks
from app.services.chunking import chunk_text
from app.services.file_storage import save_encrypted_pdf
from app.services.indexing import index_policy
from app.services.pdf_extraction import extract_text_from_pdf_bytes
from app.services.policy_metadata import detect_tenure_years

REFERENCE_USER_EMAIL = "reference@policylens.local"

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "irdai_policies"

# filename -> (insurer, structural_type)
FILE_MAP = {
    "hdfc_ergo_private_car_comprehensive.pdf": ("HDFC ERGO", "comprehensive"),
    "hdfc_ergo_private_car_tp_only.pdf": ("HDFC ERGO", "third_party_only"),
    "hdfc_ergo_two_wheeler.pdf": ("HDFC ERGO", "two_wheeler"),
    "hdfc_ergo_two_wheeler_standalone_od.pdf": ("HDFC ERGO", "standalone_own_damage"),
    "icici_lombard_private_car_comprehensive.pdf": ("ICICI Lombard", "comprehensive"),
    "icici_lombard_private_car_tp_only.pdf": ("ICICI Lombard", "third_party_only"),
    "icici_lombard_two_wheeler.pdf": ("ICICI Lombard", "two_wheeler"),
    "icici_lombard_two_wheeler_standalone_od.pdf": ("ICICI Lombard", "standalone_own_damage"),
}


def get_or_create_reference_user(session: Session) -> User:
    user = session.exec(select(User).where(User.email == REFERENCE_USER_EMAIL)).first()
    if user:
        return user
    # random, never-used password - this account exists only to own reference-doc rows, not to log in
    user = User(email=REFERENCE_USER_EMAIL, hashed_password=hash_password(secrets.token_urlsafe(32)))
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def seed():
    init_db()

    if not DATA_DIR.exists():
        print(f"ERROR: {DATA_DIR} not found.")
        sys.exit(1)

    with Session(engine) as session:
        reference_user = get_or_create_reference_user(session)

        for filename, (insurer, structural_type) in FILE_MAP.items():
            existing = session.exec(
                select(Policy).where(Policy.filename == filename, Policy.is_reference_doc == True)  # noqa: E712
            ).first()
            if existing:
                print(f"SKIP  {filename} (already seeded as policy id={existing.id})")
                continue

            pdf_path = DATA_DIR / filename
            if not pdf_path.exists():
                print(f"MISSING  {filename} not found in {DATA_DIR}, skipping")
                continue

            raw_bytes = pdf_path.read_bytes()
            text = extract_text_from_pdf_bytes(raw_bytes)
            if not text:
                print(f"WARN  {filename}: no extractable text, skipping")
                continue

            file_path = save_encrypted_pdf(raw_bytes)
            tenure_years = detect_tenure_years(text)

            policy = Policy(
                user_id=reference_user.id,
                filename=filename,
                structural_type=structural_type,
                insurer=insurer,
                is_reference_doc=True,
                tenure_years=tenure_years,
                file_path=file_path,
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

            print(f"OK    {filename} -> policy id={policy.id}, {len(chunks)} chunks - embedding now (~3s/chunk)...")
            start = time.time()
            index_policy(policy.id, insurer, structural_type)
            policy.indexed_at = datetime.now(timezone.utc)
            session.add(policy)
            session.commit()
            print(f"      indexed in {time.time() - start:.0f}s")


if __name__ == "__main__":
    seed()
