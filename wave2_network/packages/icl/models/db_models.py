from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class InferenceRequestRecord(BaseModel):
    request_id: str = Field(default_factory=lambda: uuid4().hex)
    task_id: str
    invocation_id: int
    developer_address: str
    model_id: str
    encrypted_features: list[dict[str, str | int]]
    feature_types: list[str]
    loan_id: str | None = None
    coverage_type: str | None = None
    max_fee_gnk: int = 0
    min_tier: int
    zdr_required: bool
    verifier_count: int
    leader_address: str
    verifier_addresses: list[str]
    status: Literal["queued", "accepted", "rejected", "disputed"] = "queued"
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)
    result_hash: str | None = None
    result_preview: str | None = None
    risk_score: int | None = None
    chain_tx_hash: str | None = None
    aggregated_confidence: int | None = None
    confirm_count: int = 0
    reject_count: int = 0
    dispute_deadline: datetime | None = None


class QuorumAssignmentRecord(BaseModel):
    request_id: str
    task_id: str
    leader_address: str
    verifier_addresses: list[str]
    candidate_addresses: list[str]
    created_at: datetime = Field(default_factory=utcnow)


class VerifierVerdictRecord(BaseModel):
    request_id: str
    task_id: str
    verifier_address: str
    accepted: bool | None = None
    confidence: int
    reason: str | None = None
    result_hash: str | None = None
    risk_score: int | None = None
    provider: str | None = None
    model: str | None = None
    summary: str | None = None
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class QuorumCertificateRecord(BaseModel):
    request_id: str
    task_id: str
    model_id: str
    leader_address: str
    verifier_addresses: list[str]
    result_hash: str
    confirm_count: int
    reject_count: int
    aggregated_confidence: int
    accepted: bool
    chain_tx_hash: str
    created_at: datetime = Field(default_factory=utcnow)


class ModelCatalogRecord(BaseModel):
    model_id: str
    name: str
    provider: str
    min_tier: int = 1
    zdr_required: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class DisputeRecord(BaseModel):
    request_id: str
    task_id: str
    developer_address: str
    evidence_hash: str
    evidence_uri: str
    notes: str | None = None
    created_at: datetime = Field(default_factory=utcnow)


class PermitEntryRecord(BaseModel):
    node_address: str
    permit: str
    status: str = "shared-permit-provided"
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class PermitRecord(BaseModel):
    task_id: str
    permits: list[PermitEntryRecord]
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class OperatorRecord(BaseModel):
    operator_address: str
    model_tiers: list[int]
    location: str
    zdr_compliant: bool
    jurisdiction: str
    min_stake: int
    registered_at: datetime = Field(default_factory=utcnow)
    last_heartbeat: datetime = Field(default_factory=utcnow)
    attestation_type: str
    attestation_document_hash: str
    attestation_counterparty: str = "0x0000000000000000000000000000000000000000"
    attestation_effective_at: int
    attestation_expires_at: int
    tasks_completed: int = 0
    tasks_accepted: int = 0
    tasks_rejected: int = 0
    active: bool = True


class NodeRuntimeRecord(BaseModel):
    operator_address: str
    callback_url: str
    registered_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
