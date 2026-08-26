from qdrant_client import QdrantClient

from app.config import settings

_client: QdrantClient | None = None


def get_qdrant_client() -> QdrantClient:
    """
    Embedded local-mode Qdrant client (in-process, on-disk storage,
    no Docker/server). Deviation from suggestions.md/PLAN.md's original
    "Docker Compose" choice - see CLAUDE.md for rationale.
    Note: on-disk storage is exclusive-locked to one process at a time;
    don't run two backend instances against the same QDRANT_LOCAL_PATH.
    """
    global _client
    if _client is None:
        _client = QdrantClient(path=settings.QDRANT_LOCAL_PATH)
    return _client
