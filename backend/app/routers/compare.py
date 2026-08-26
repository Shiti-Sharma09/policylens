from fastapi import APIRouter

router = APIRouter(prefix="/compare", tags=["compare"])


@router.get("/ping")
def ping():
    return {"router": "compare", "status": "stub"}
