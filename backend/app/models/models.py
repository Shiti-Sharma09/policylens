from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel, Field, UniqueConstraint


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    hashed_password: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Policy(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    filename: str
    structural_type: Optional[str] = None  # "comprehensive" | "third_party_only" | "two_wheeler"
    insurer: Optional[str] = None
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
    is_reference_doc: bool = Field(default=False)  # True for the IRDAI seed docs (Day 2)
    indexed_at: Optional[datetime] = None  # set once chunks are embedded + upserted into Qdrant (Day 3)


class PolicyChunkMeta(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    policy_id: int = Field(foreign_key="policy.id", index=True)
    qdrant_point_id: str = Field(index=True)
    chunk_index: int
    section_hint: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AnswerCache(SQLModel, table=True):
    """Caches (policy_id, question) -> answer, since Qwen3-8B answers take ~20-90s
    on this CPU-only machine (see CLAUDE.md) - a meaningful latency win, not just a nice-to-have."""

    __table_args__ = (UniqueConstraint("policy_id", "question_hash"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    policy_id: int = Field(foreign_key="policy.id", index=True)
    question_hash: str = Field(index=True)  # sha256 of the normalized (lowercased, stripped) question
    question: str
    answer: str
    citations_json: str  # JSON-encoded list of {chunk_text, section_hint, chunk_index, score}
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Claim(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    policy_id: int = Field(foreign_key="policy.id", index=True)
    damage_type: Optional[str] = None
    status: str = Field(default="draft")  # advisory only - never "approved/rejected"
    created_at: datetime = Field(default_factory=datetime.utcnow)
