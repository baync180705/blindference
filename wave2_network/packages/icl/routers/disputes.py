from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from models.request_models import DisputeSubmissionRequest
from models.response_models import DisputeResponse
from services import ServiceContainer, get_service_container

router = APIRouter(prefix="/v1/disputes", tags=["disputes"])


@router.post("/{request_id}", response_model=DisputeResponse)
async def submit_dispute(
    request_id: str,
    payload: DisputeSubmissionRequest,
    services: ServiceContainer = Depends(get_service_container),
) -> DisputeResponse:
    try:
        dispute = await services.quorum_service.submit_dispute(request_id, payload)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return DisputeResponse(**dispute)


@router.get("/{request_id}", response_model=DisputeResponse)
async def get_dispute(
    request_id: str,
    services: ServiceContainer = Depends(get_service_container),
) -> DisputeResponse:
    dispute = await services.quorum_service.get_dispute(request_id)
    if dispute is None:
        raise HTTPException(status_code=404, detail="dispute not found")
    return DisputeResponse(**dispute)
