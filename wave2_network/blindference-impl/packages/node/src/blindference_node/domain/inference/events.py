from __future__ import annotations

from dataclasses import dataclass

from blindference_node.domain.inference.encrypted_input import EncryptedInput
from blindference_node.domain.inference.encrypted_output import EncryptedOutput
from blindference_node.domain.privacy.permitted_set import PermittedExecutorSet
from blindference_node.domain.shared_kernel.events import DomainEvent
from blindference_node.domain.shared_kernel.ids import (
    AgentId,
    EscrowId,
    InvocationId,
    NodeAddress,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class InferenceJobOpened(DomainEvent):
    invocation_id: InvocationId
    agent_id: AgentId
    escrow_id: EscrowId
    permitted: PermittedExecutorSet


@dataclass(frozen=True, slots=True, kw_only=True)
class InferenceJobDispatched(DomainEvent):
    invocation_id: InvocationId
    executor: NodeAddress
    cross_verifier: NodeAddress
    encrypted_input: EncryptedInput


@dataclass(frozen=True, slots=True, kw_only=True)
class InferenceJobExecuted(DomainEvent):
    invocation_id: InvocationId
    executor_commit_digest: bytes
    verifier_commit_digest: bytes


@dataclass(frozen=True, slots=True, kw_only=True)
class InferenceJobVerified(DomainEvent):
    invocation_id: InvocationId
    output: EncryptedOutput


@dataclass(frozen=True, slots=True, kw_only=True)
class InferenceJobAttested(DomainEvent):
    invocation_id: InvocationId
    attestation_digest: bytes


@dataclass(frozen=True, slots=True, kw_only=True)
class InferenceJobFinalized(DomainEvent):
    invocation_id: InvocationId
    on_chain_receipt_hash: bytes
