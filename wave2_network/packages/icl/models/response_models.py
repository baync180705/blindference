from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from .text_inference import TextInferenceRequest


class HealthResponse(BaseModel):
    status: str
    chain_connected: bool
    mongo_connected: bool


class NodeMetricsResponse(BaseModel):
    tasks_completed: int
    tasks_accepted: int
    tasks_rejected: int
    reputation_score: int
    total_slash_amount: int
    last_heartbeat: int


class NodeResponse(BaseModel):
    operator_address: str
    model_tiers: list[int]
    location: str
    zdr_compliant: bool
    jurisdiction: str
    min_stake: int
    active: bool
    metrics: NodeMetricsResponse


class QuorumAssignmentResponse(BaseModel):
    leader_address: str
    verifier_addresses: list[str]
    candidate_addresses: list[str]


class QuorumPreviewResponse(BaseModel):
    leader: str
    verifiers: list[str]
    candidates: list[str]


class EncryptedFeatureResponse(BaseModel):
    ct_hash: str
    utype: str | int
    signature: str


class LeaderSubmissionResponse(BaseModel):
    leader_address: str
    risk_score: int | None = None
    confidence: int | None = None
    summary: str | None = None
    provider: str | None = None
    model: str | None = None
    result_hash: str | None = None
    submitted_at: datetime | None = None


class VerifierVerdictResponse(BaseModel):
    verifier_address: str
    submitted: bool = False
    accepted: bool | None = None
    confidence: int | None = None
    reason: str | None = None
    risk_score: int | None = None
    result_hash: str | None = None
    provider: str | None = None
    model: str | None = None
    summary: str | None = None
    updated_at: datetime | None = None


class InferenceRequestResponse(BaseModel):
    job_id: str | None = None
    request_id: str
    task_id: str
    leader_address: str | None = None
    developer_address: str
    model_id: str
    mode: Literal["risk", "text"] = "risk"
    text_request: TextInferenceRequest | None = None
    text_mode: bool = False
    encrypted_features: list[EncryptedFeatureResponse]
    feature_types: list[str]
    loan_id: str | None = None
    coverage_type: str | None = None
    max_fee_gnk: int
    status: Literal["queued", "accepted", "rejected", "disputed"]
    min_tier: int
    zdr_required: bool
    verifier_count: int
    quorum: QuorumAssignmentResponse
    metadata: dict[str, Any] = Field(default_factory=dict)
    prompt_cid: str | None = None
    encrypted_prompt_key_high: str | None = None
    encrypted_prompt_key_low: str | None = None
    encrypted_output_key_high: str | None = None
    encrypted_output_key_low: str | None = None
    output_cid: str | None = None
    commitment_hash: str | None = None
    result_hash: str | None = None
    result_preview: str | None = None
    risk_score: int | None = None
    leader_submission: LeaderSubmissionResponse | None = None
    verifier_verdicts: list[VerifierVerdictResponse] = Field(default_factory=list)
    chain_tx_hash: str | None = None
    aggregated_confidence: int | None = None
    confirm_count: int = 0
    reject_count: int = 0
    created_at: datetime
    updated_at: datetime


class InferenceCommitResponse(BaseModel):
    request_id: str
    task_id: str
    accepted: bool
    confirm_count: int
    reject_count: int
    aggregated_confidence: int
    result_hash: str
    chain_tx_hash: str


class ModelRecordResponse(BaseModel):
    model_id: str
    name: str
    provider: str
    min_tier: int
    zdr_required: bool
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class CoverageQuoteResponse(BaseModel):
    request_id: str
    coverage_available: bool
    recommendation: str


class DisputeResponse(BaseModel):
    request_id: str
    task_id: str
    developer_address: str
    evidence_hash: str
    evidence_uri: str
    notes: str | None = None
    created_at: datetime


class BootstrapNodesResponse(BaseModel):
    registered_addresses: list[str]
    tx_hashes: list[str]
