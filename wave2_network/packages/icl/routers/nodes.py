from fastapi import APIRouter

router = APIRouter(prefix="/v1/nodes", tags=["nodes"])


@router.get("/stub")
async def nodes_stub() -> dict[str, str]:
    return {"message": "nodes router stub"}
