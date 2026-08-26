from qdrant_client import QdrantClient

from app.config import settings

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
