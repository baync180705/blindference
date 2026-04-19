from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


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


class InferenceRequestResponse(BaseModel):
    request_id: str
    task_id: str
    developer_address: str
    model_id: str
    prompt: str
    status: Literal["queued", "accepted", "rejected", "disputed"]
    min_tier: int
    zdr_required: bool
    verifier_count: int
    quorum: QuorumAssignmentResponse
    metadata: dict[str, Any] = Field(default_factory=dict)
    result_hash: str | None = None
    result_preview: str | None = None
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
