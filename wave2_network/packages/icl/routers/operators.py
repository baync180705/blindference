from fastapi import APIRouter

router = APIRouter(prefix="/internal", tags=["operators"])


@router.get("/stub")
async def operators_stub() -> dict[str, str]:
    return {"message": "operators router stub"}
