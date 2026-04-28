from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .text_inference import TextInferenceRequest


class EncryptedFeature(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    ct_hash: str = Field(alias="ctHash")
    utype: str | int
    signature: str

    def to_wire(self) -> dict[str, str | int]:
        return {
            "ctHash": self.ct_hash,
            "utype": self.utype,
            "signature": self.signature,
        }


class PermitEntry(BaseModel):
    node: str
    permit: str | dict[str, Any]


class InferenceRequestCreate(BaseModel):
    developer_address: str
    model_id: str | None = None
    mode: str = Field(default="risk", description="'risk' or 'text'")
    text_request: TextInferenceRequest | None = None
    encrypted_features: list[EncryptedFeature] = Field(default_factory=list)
    encrypted_input: list[EncryptedFeature] | EncryptedFeature | None = None
    permits: list[PermitEntry] = Field(default_factory=list)
    leader_address: str | None = None
    verifier_addresses: list[str] = Field(default_factory=list)
    feature_types: list[str] = Field(default_factory=list)
    loan_id: str | None = None
    coverage_type: str | None = None
    max_fee_gnk: int = Field(default=0, ge=0)
    min_tier: int = Field(default=1, ge=0, le=2)
    zdr_required: bool = False
    verifier_count: int = Field(default=2, ge=1, le=5)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def normalized_encrypted_features(self) -> list[EncryptedFeature]:
        if isinstance(self.encrypted_input, list):
            return self.encrypted_input
        if self.encrypted_input is not None:
            return [self.encrypted_input]
        return self.encrypted_features


class InferenceRequest(InferenceRequestCreate):
    pass


class VerifierVerdictInput(BaseModel):
    verifier_address: str
    accepted: bool
    confidence: int = Field(default=100, ge=0, le=100)
    reason: str | None = None


class InferenceCommitRequest(BaseModel):
    risk_score: int = Field(ge=0, le=100)
    leader_confidence: int = Field(default=100, ge=0, le=100)
    leader_summary: str | None = None
    provider: str | None = None
    model: str | None = None
    result_hash: str | None = None
    verifier_verdicts: list[VerifierVerdictInput] = Field(default_factory=list)
    rejection_reason: str | None = None


class InferencePermitAttachmentRequest(BaseModel):
    node: str | None = None
    permit: str | dict[str, Any]


class LeaderResultSubmissionRequest(BaseModel):
    leader_address: str
    risk_score: int = Field(ge=0, le=100)
    leader_confidence: int = Field(default=100, ge=0, le=100)
    leader_summary: str | None = None
    provider: str | None = None
    model: str | None = None
    result_hash: str | None = None


class VerifierVerdictSubmissionRequest(BaseModel):
    verifier_address: str
    confidence: int = Field(default=100, ge=0, le=100)
    accepted: bool | None = None
    reason: str | None = None
    risk_score: int | None = Field(default=None, ge=0, le=100)
    result_hash: str | None = None
    provider: str | None = None
    model: str | None = None
    summary: str | None = None


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


class NodeRuntimeRegistrationRequest(BaseModel):
    operator_address: str
    callback_url: str
