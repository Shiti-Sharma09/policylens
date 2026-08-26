from fastapi import APIRouter

router = APIRouter(prefix="/damage", tags=["damage"])


@router.get("/ping")
def ping():
    return {"router": "damage", "status": "stub"}
