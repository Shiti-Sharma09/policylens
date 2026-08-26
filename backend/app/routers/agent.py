from fastapi import APIRouter

router = APIRouter(prefix="/agent", tags=["agent"])


@router.get("/ping")
def ping():
    return {"router": "agent", "status": "stub"}
