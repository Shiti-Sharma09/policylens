from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

from app.config import settings

COLLECTION_NAME = "policy_chunks"

_client: QdrantClient | None = None


def get_qdrant_client() -> QdrantClient:
    """
    Connects to the Qdrant instance started via `docker compose up -d`
    (see docker-compose.yml). Must be running before the backend starts -
    the FastAPI lifespan calls this on startup and will fail to connect
    otherwise.
    """
    global _client
    if _client is None:
        _client = QdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT)
    return _client


def ensure_collection() -> None:
    """Creates the policy_chunks collection if it doesn't already exist. Idempotent."""
    client = get_qdrant_client()
    existing = {c.name for c in client.get_collections().collections}
    if COLLECTION_NAME not in existing:
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=settings.EMBEDDING_DIMENSION, distance=Distance.COSINE),
        )
