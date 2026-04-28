from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from models.internal_models import LeaderTextResultSubmission, VerifierTextVerdict
from services import ServiceContainer, get_service_container

router = APIRouter(prefix="/internal/task", tags=["internal-task"])


@router.post("/result")
async def submit_internal_task_result(
    payload: dict[str, Any],
    services: ServiceContainer = Depends(get_service_container),
) -> dict[str, object]:
    job_id = payload.get("job_id")
    if not isinstance(job_id, str) or not job_id:
        raise HTTPException(status_code=400, detail="job_id is required")

    try:
        return await services.quorum_service.submit_internal_task_result(job_id, payload)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.post("/verify")
async def submit_internal_task_verification(
    payload: dict[str, Any],
    services: ServiceContainer = Depends(get_service_container),
) -> dict[str, object]:
    job_id = payload.get("job_id")
    if not isinstance(job_id, str) or not job_id:
        raise HTTPException(status_code=400, detail="job_id is required")

    try:
        return await services.quorum_service.submit_internal_task_verification(job_id, payload)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
