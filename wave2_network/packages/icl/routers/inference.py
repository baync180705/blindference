from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from middleware.rate_limit import rate_limit_guard
from models.request_models import (
    InferenceCommitRequest,
    LeaderResultSubmissionRequest,
    InferencePermitAttachmentRequest,
    InferenceRequestCreate,
    VerifierVerdictSubmissionRequest,
)
from models.response_models import InferenceCommitResponse, InferenceRequestResponse, QuorumPreviewResponse
from services import ServiceContainer, get_service_container

router = APIRouter(prefix="/v1/inference", tags=["inference"])


@router.get("", response_model=list[InferenceRequestResponse])
async def list_inference_requests(
    _: bool = Depends(rate_limit_guard),
    services: ServiceContainer = Depends(get_service_container),
) -> list[InferenceRequestResponse]:
    return await services.quorum_service.list_requests()


@router.get("/quorum-preview", response_model=QuorumPreviewResponse)
async def get_quorum_preview(
    model_id: str,
    min_tier: int = 1,
    verifier_count: int = 2,
    zdr_required: bool = False,
    services: ServiceContainer = Depends(get_service_container),
) -> QuorumPreviewResponse:
    del model_id
    try:
        preview = await services.quorum_service.preview_quorum(
            min_tier=min_tier,
            zdr_required=zdr_required,
            verifier_count=verifier_count,
        )
        return QuorumPreviewResponse(
            leader=preview["leader_address"],
            verifiers=preview["verifier_addresses"],
            candidates=preview["candidate_addresses"],
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


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


@router.post("/{request_id}/leader-result")
async def submit_leader_result(
    request_id: str,
    payload: LeaderResultSubmissionRequest,
    _: bool = Depends(rate_limit_guard),
    services: ServiceContainer = Depends(get_service_container),
) -> dict[str, object]:
    try:
        return await services.quorum_service.submit_leader_result(request_id, payload)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.post("/{request_id}/verdicts")
async def submit_verifier_verdict(
    request_id: str,
    payload: VerifierVerdictSubmissionRequest,
    _: bool = Depends(rate_limit_guard),
    services: ServiceContainer = Depends(get_service_container),
) -> dict[str, object]:
    try:
        return await services.quorum_service.submit_verifier_verdict(request_id, payload)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.get("/task/{task_id}", response_model=InferenceRequestResponse)
async def get_inference_request_by_task_id(
    task_id: str,
    services: ServiceContainer = Depends(get_service_container),
) -> InferenceRequestResponse:
    try:
        return await services.quorum_service.get_request_by_task_id(task_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.get("/{request_id}", response_model=InferenceRequestResponse)
async def get_inference_request(
    request_id: str,
    services: ServiceContainer = Depends(get_service_container),
) -> InferenceRequestResponse:
    try:
        return await services.quorum_service.get_request(request_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.patch("/{task_id}/permit")
async def attach_inference_permit(
    task_id: str,
    payload: InferencePermitAttachmentRequest,
    _: bool = Depends(rate_limit_guard),
    services: ServiceContainer = Depends(get_service_container),
) -> dict[str, str]:
    try:
        return await services.quorum_service.attach_permit(task_id, payload)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


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
