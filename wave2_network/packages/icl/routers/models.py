from fastapi import APIRouter

router = APIRouter(prefix="/v1/models", tags=["models"])


@router.get("/stub")
async def models_stub() -> dict[str, str]:
    return {"message": "models router stub"}
