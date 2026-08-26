from fastapi import APIRouter

router = APIRouter(prefix="/ask", tags=["ask"])


@router.get("/ping")
def ping():
    return {"router": "ask", "status": "stub"}
