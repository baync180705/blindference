from __future__ import annotations


class CoverageService:
    async def get_quote(self, request_id: str) -> dict[str, object]:
        return {
            "request_id": request_id,
            "coverage_available": True,
            "recommendation": "Coverage hooks are ready for Reineira integration; using placeholder local quote for now.",
        }
