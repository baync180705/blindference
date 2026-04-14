from fastapi import APIRouter

router = APIRouter(prefix="/v1/disputes", tags=["disputes"])


@router.get("/stub")
async def disputes_stub() -> dict[str, str]:
    return {"message": "disputes router stub"}
