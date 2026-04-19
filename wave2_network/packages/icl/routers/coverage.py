from __future__ import annotations

from fastapi import APIRouter, Depends

from models.response_models import CoverageQuoteResponse
from services import ServiceContainer, get_service_container

router = APIRouter(prefix="/v1/coverage", tags=["coverage"])


@router.get("/{request_id}", response_model=CoverageQuoteResponse)
async def get_coverage_quote(
    request_id: str,
    services: ServiceContainer = Depends(get_service_container),
) -> CoverageQuoteResponse:
    quote = await services.coverage_service.get_quote(request_id)
    return CoverageQuoteResponse(**quote)
