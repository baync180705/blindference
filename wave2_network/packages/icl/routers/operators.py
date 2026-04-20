from __future__ import annotations

from fastapi import APIRouter, Depends

from models.request_models import BootstrapDemoNodesRequest, NodeRuntimeRegistrationRequest
from models.response_models import BootstrapNodesResponse
from services import ServiceContainer, get_service_container

router = APIRouter(prefix="/internal/operators", tags=["operators"])


@router.get("")
async def list_demo_operator_wallets(
    services: ServiceContainer = Depends(get_service_container),
) -> dict[str, object]:
    return {
        "configured_operator_count": len(services.settings.demo_operator_private_keys),
        "configured_operator_addresses": [
            services.chain_service.web3_client.account_from_private_key(private_key).address
            for private_key in services.settings.demo_operator_private_keys
        ],
    }


@router.post("/bootstrap", response_model=BootstrapNodesResponse)
async def bootstrap_operators(
    payload: BootstrapDemoNodesRequest,
    services: ServiceContainer = Depends(get_service_container),
) -> BootstrapNodesResponse:
    result = await services.chain_service.bootstrap_demo_nodes(payload.count)
    return BootstrapNodesResponse(**result)


@router.get("/runtimes")
async def list_registered_node_runtimes(
    services: ServiceContainer = Depends(get_service_container),
) -> list[dict[str, str]]:
    return await services.quorum_service.list_node_runtimes()


@router.post("/runtime")
async def register_node_runtime(
    payload: NodeRuntimeRegistrationRequest,
    services: ServiceContainer = Depends(get_service_container),
) -> dict[str, str]:
    return await services.quorum_service.register_node_runtime(
        operator_address=payload.operator_address,
        callback_url=payload.callback_url,
    )
