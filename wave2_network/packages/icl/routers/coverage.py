from fastapi import APIRouter

router = APIRouter(prefix="/v1/coverage", tags=["coverage"])


@router.get("/stub")
async def coverage_stub() -> dict[str, str]:
    return {"message": "coverage router stub"}
