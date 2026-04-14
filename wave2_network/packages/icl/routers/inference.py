from fastapi import APIRouter

router = APIRouter(prefix="/v1/inference", tags=["inference"])


@router.get("/stub")
async def inference_stub() -> dict[str, str]:
    return {"message": "inference router stub"}
