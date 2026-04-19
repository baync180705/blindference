from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from middleware.rate_limit import rate_limit_guard
from models.request_models import InferenceCommitRequest, InferenceRequestCreate
from models.response_models import InferenceCommitResponse, InferenceRequestResponse
from services import ServiceContainer, get_service_container

router = APIRouter(prefix="/v1/inference", tags=["inference"])


@router.get("", response_model=list[InferenceRequestResponse])
async def list_inference_requests(
    _: bool = Depends(rate_limit_guard),
    services: ServiceContainer = Depends(get_service_container),
) -> list[InferenceRequestResponse]:
    return await services.quorum_service.list_requests()


@router.post("/requests", response_model=InferenceRequestResponse)
async def create_inference_request(
    payload: InferenceRequestCreate,
    _: bool = Depends(rate_limit_guard),
    services: ServiceContainer = Depends(get_service_container),
) -> InferenceRequestResponse:
    try:
        return await services.quorum_service.create_request(payload)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.get("/{request_id}", response_model=InferenceRequestResponse)
async def get_inference_request(
    request_id: str,
    services: ServiceContainer = Depends(get_service_container),
) -> InferenceRequestResponse:
    try:
        return await services.quorum_service.get_request(request_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post("/{request_id}/commit", response_model=InferenceCommitResponse)
async def commit_inference_request(
    request_id: str,
    payload: InferenceCommitRequest,
    _: bool = Depends(rate_limit_guard),
    services: ServiceContainer = Depends(get_service_container),
) -> InferenceCommitResponse:
    try:
        return await services.quorum_service.commit_request(request_id, payload)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
