from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class LeaderTextResultSubmission(BaseModel):
    job_id: str
    output_cid: str
    commitment_hash: str
    encrypted_output_key_high: str | None = None
    encrypted_output_key_low: str | None = None
    encrypted_output_key_inputs: dict[str, dict[str, Any]] | None = None
    verdict: str | None = None
    confidence: int | None = Field(default=None, ge=0, le=100)


class VerifierTextVerdict(BaseModel):
    job_id: str
    verifier_address: str
    commitment_hash: str
    verdict: str
    confidence: int = Field(ge=0, le=100)
