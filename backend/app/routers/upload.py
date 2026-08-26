from fastapi import APIRouter

router = APIRouter(prefix="/upload", tags=["upload"])


@router.get("/ping")
def ping():
    return {"router": "upload", "status": "stub"}
