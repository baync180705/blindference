from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from fastapi import Request

if TYPE_CHECKING:
    from services.chain_service import ChainService
    from services.coverage_service import CoverageService
    from services.model_registry_service import ModelRegistryService
    from services.node_selector import NodeSelector
    from services.quorum_service import QuorumService
    from services.verdict_aggregator import VerdictAggregator
    from config import Settings


@dataclass(slots=True)
class ServiceContainer:
    settings: "Settings"
    database: object
    chain_service: "ChainService"
    node_selector: "NodeSelector"
    verdict_aggregator: "VerdictAggregator"
    coverage_service: "CoverageService"
    model_registry_service: "ModelRegistryService"
    quorum_service: "QuorumService"


def get_service_container(request: Request) -> ServiceContainer:
    return request.app.state.services
