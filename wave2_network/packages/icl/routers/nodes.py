from __future__ import annotations

from fastapi import APIRouter, Depends

from middleware.rate_limit import rate_limit_guard
from models.response_models import NodeMetricsResponse, NodeResponse
from services import ServiceContainer, get_service_container

router = APIRouter(prefix="/v1/nodes", tags=["nodes"])


@router.get("/active", response_model=list[NodeResponse])
async def list_active_nodes(
    min_tier: int = 0,
    zdr_required: bool = False,
    _: bool = Depends(rate_limit_guard),
    services: ServiceContainer = Depends(get_service_container),
) -> list[NodeResponse]:
    addresses = await services.chain_service.get_active_nodes(min_tier, zdr_required)
    snapshots = [await services.chain_service.get_node_snapshot(address) for address in addresses]
    return [
        NodeResponse(
            operator_address=snapshot["operator_address"],
            model_tiers=snapshot["model_tiers"],
            location=snapshot["location"],
            zdr_compliant=snapshot["zdr_compliant"],
            jurisdiction=snapshot["jurisdiction"],
            min_stake=snapshot["min_stake"],
            active=snapshot["active"],
            metrics=NodeMetricsResponse(**snapshot["metrics"]),
        )
        for snapshot in snapshots
    ]


@router.get("/{node_address}", response_model=NodeResponse)
async def get_node(
    node_address: str,
    services: ServiceContainer = Depends(get_service_container),
) -> NodeResponse:
    snapshot = await services.chain_service.get_node_snapshot(node_address)
    return NodeResponse(
        operator_address=snapshot["operator_address"],
        model_tiers=snapshot["model_tiers"],
        location=snapshot["location"],
        zdr_compliant=snapshot["zdr_compliant"],
        jurisdiction=snapshot["jurisdiction"],
        min_stake=snapshot["min_stake"],
        active=snapshot["active"],
        metrics=NodeMetricsResponse(**snapshot["metrics"]),
    )
