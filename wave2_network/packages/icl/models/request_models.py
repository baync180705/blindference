from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class InferenceRequestCreate(BaseModel):
    developer_address: str
    model_id: str
    prompt: str
    min_tier: int = Field(default=1, ge=0, le=2)
    zdr_required: bool = False
    verifier_count: int = Field(default=2, ge=1, le=5)
    metadata: dict[str, Any] = Field(default_factory=dict)


class VerifierVerdictInput(BaseModel):
    verifier_address: str
    accepted: bool
    confidence: int = Field(default=100, ge=0, le=100)
    reason: str | None = None


class InferenceCommitRequest(BaseModel):
    leader_output: str
    leader_confidence: int = Field(default=100, ge=0, le=100)
    result_hash: str | None = None
    verifier_verdicts: list[VerifierVerdictInput] = Field(default_factory=list)
    rejection_reason: str | None = None


class ModelRegistrationRequest(BaseModel):
    model_id: str
    name: str
    provider: str
    min_tier: int = Field(default=1, ge=0, le=2)
    zdr_required: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class DisputeSubmissionRequest(BaseModel):
    developer_address: str
    evidence_hash: str
    evidence_uri: str
    notes: str | None = None


class BootstrapDemoNodesRequest(BaseModel):
    count: int = Field(default=3, ge=1, le=3)
