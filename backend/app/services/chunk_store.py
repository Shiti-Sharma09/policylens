"""
Staging area for chunk text between Day 2 (upload/chunk) and Day 3 (embed/upsert into Qdrant).

Per suggestions.md's architecture, SQLite holds only metadata (PolicyChunkMeta:
policy_id, qdrant_point_id, chunk_index) - actual chunk text is meant to live in
Qdrant's payload once embedded. Until Day 3 wires up embedding, chunk text is
staged here as JSON, keyed by the same qdrant_point_id Day 3 will use on upsert.
"""

import json
from pathlib import Path

_STORAGE_ROOT = Path(__file__).resolve().parent.parent.parent / "storage" / "chunks"


def save_chunks(policy_id: int, chunks: list[dict]) -> str:
    """chunks: list of {"qdrant_point_id": str, "chunk_index": int, "text": str}."""
    _STORAGE_ROOT.mkdir(parents=True, exist_ok=True)
    path = _STORAGE_ROOT / f"{policy_id}.json"
    path.write_text(json.dumps(chunks, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(path.relative_to(_STORAGE_ROOT.parent.parent))


def load_chunks(policy_id: int) -> list[dict]:
    path = _STORAGE_ROOT / f"{policy_id}.json"
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))
