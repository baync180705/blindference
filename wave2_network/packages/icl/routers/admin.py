from __future__ import annotations

from fastapi import APIRouter, Body, Depends

from db.collections import get_collection_names
from models.request_models import BootstrapDemoNodesRequest
from models.response_models import BootstrapNodesResponse
from services import ServiceContainer, get_service_container

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/status")
async def admin_status(
    services: ServiceContainer = Depends(get_service_container),
) -> dict[str, object]:
    return {
        "collections": get_collection_names(),
        "chain_connected": await services.chain_service.is_connected(),
        "model_registry_ready": await services.chain_service.model_registry_ready(),
        "reward_accumulator_ready": await services.chain_service.reward_accumulator_ready(),
    }


@router.post("/bootstrap-demo-nodes", response_model=BootstrapNodesResponse)
async def bootstrap_demo_nodes(
    payload: BootstrapDemoNodesRequest = Body(default=BootstrapDemoNodesRequest()),
    services: ServiceContainer = Depends(get_service_container),
) -> BootstrapNodesResponse:
    result = await services.chain_service.bootstrap_demo_nodes(payload.count)
    return BootstrapNodesResponse(**result)
