from __future__ import annotations

from fastapi import APIRouter, Depends

from middleware.rate_limit import rate_limit_guard
from models.request_models import ModelRegistrationRequest
from models.response_models import ModelRecordResponse
from services import ServiceContainer, get_service_container

router = APIRouter(prefix="/v1/models", tags=["models"])


@router.get("", response_model=list[ModelRecordResponse])
async def list_models(
    _: bool = Depends(rate_limit_guard),
    services: ServiceContainer = Depends(get_service_container),
) -> list[ModelRecordResponse]:
    models = await services.model_registry_service.list_models()
    return [ModelRecordResponse(**model) for model in models]


@router.post("", response_model=ModelRecordResponse)
async def register_model(
    payload: ModelRegistrationRequest,
    services: ServiceContainer = Depends(get_service_container),
) -> ModelRecordResponse:
    record = await services.model_registry_service.register_model(payload)
    return ModelRecordResponse(**record)
