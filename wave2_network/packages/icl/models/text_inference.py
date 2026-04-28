from __future__ import annotations

from pydantic import BaseModel, Field


class EncryptedPromptKey(BaseModel):
    high: str = Field(..., description="FHE-encrypted high 128 bits of the AES key (bigint string)")
    low: str = Field(..., description="FHE-encrypted low 128 bits of the AES key (bigint string)")


class TextInferenceRequest(BaseModel):
    prompt_cid: str = Field(..., description="IPFS CID of the AES-GCM encrypted prompt blob")
    encrypted_prompt_key: EncryptedPromptKey
    model_id: str | None = None
    coverage_enabled: bool = False


class QuorumCertificate(BaseModel):
    verifier_addresses: list[str]
    confirmations: int
    confidence: int


class TextInferenceResult(BaseModel):
    job_id: str
    status: str
    output_cid: str | None = None
    commitment_hash: str | None = None
    encrypted_output_key_high: str | None = None
    encrypted_output_key_low: str | None = None
    quorum: QuorumCertificate | None = None
    dispute_deadline: int | None = None
