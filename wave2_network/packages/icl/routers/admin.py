from fastapi import APIRouter

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/stub")
async def admin_stub() -> dict[str, str]:
    return {"message": "admin router stub"}
