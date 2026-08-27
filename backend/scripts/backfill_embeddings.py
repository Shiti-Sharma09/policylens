"""
Indexes any Policy row that has staged chunks (Day 2) but no embeddings in Qdrant yet
(indexed_at is None) - e.g. the 8 reference policies and any test uploads seeded/uploaded
before Day 3's indexing step existed.

Run from backend/, with the venv active:
    python -m scripts.backfill_embeddings

Idempotent and safe to re-run (Qdrant upsert overwrites by point ID). Slow: ~3s/chunk
on this machine's CPU - expect several minutes per policy, longer for the full 8.
"""

import time
from datetime import datetime, timezone

from sqlmodel import Session, select

from app.db import engine
from app.models.models import Policy
from app.services.indexing import index_policy


def backfill():
    with Session(engine) as session:
        pending = session.exec(select(Policy).where(Policy.indexed_at == None)).all()  # noqa: E711

        if not pending:
            print("Nothing to backfill - every policy is already indexed.")
            return

        print(f"{len(pending)} policies need indexing.")
        for policy in pending:
            print(f"Indexing policy {policy.id} ({policy.filename})...")
            start = time.time()
            count = index_policy(policy.id, policy.insurer, policy.structural_type)
            if count == 0:
                print(f"  SKIP - no staged chunks found for policy {policy.id}")
                continue

            policy.indexed_at = datetime.now(timezone.utc)
            session.add(policy)
            session.commit()
            print(f"  indexed {count} chunks in {time.time() - start:.0f}s")


if __name__ == "__main__":
    backfill()
