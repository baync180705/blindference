from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto

from eth_utils import keccak

from blindference_node.domain.inference.commit import (
    CommitMismatch,
    ExecutionCommit,
    ExecutionReveal,
    ExecutionRole,
)
from blindference_node.domain.inference.encrypted_input import EncryptedInput
from blindference_node.domain.inference.encrypted_output import EncryptedOutput
from blindference_node.domain.inference.events import (
    InferenceJobAttested,
    InferenceJobDispatched,
    InferenceJobExecuted,
    InferenceJobFinalized,
    InferenceJobOpened,
    InferenceJobVerified,
)
from blindference_node.domain.privacy.permitted_set import PermittedExecutorSet
from blindference_node.domain.shared_kernel.events import DomainEvent
from blindference_node.domain.shared_kernel.ids import (
    AgentId,
    EscrowId,
    InvocationId,
    NodeAddress,
)


class InferenceJobState(Enum):
    REQUESTED = auto()
    DISPATCHED = auto()
    EXECUTED = auto()
    VERIFIED = auto()
    ATTESTED = auto()
    FINALIZED = auto()


class IllegalTransition(Exception):
    pass


@dataclass(slots=True)
class InferenceJob:
    """Vertical-neutral aggregate for one Blindference inference invocation.

    Lifecycle:

        REQUESTED   protocol accepted the invocation; permitted set known
          → DISPATCHED   executor + cross-verifier picked deterministically;
                         encrypted input handed off
          → EXECUTED     both posted commit-hash to chain
          → VERIFIED     both revealed salts; outputs match (else: escalate)
          → ATTESTED     attestation digest computed, ready for on-chain submit
          → FINALIZED    Reineira `submitFinalVerdict` returned; gates fired

    All quorum-mechanics invariants (executor ≠ verifier, both in permitted
    set, commit-reveal digest match) are enforced inside the aggregate.
    Reputation, rewards, and arbitration are handled by separate aggregates
    in later phases.
    """

    invocation_id: InvocationId
    agent_id: AgentId
    escrow_id: EscrowId
    permitted: PermittedExecutorSet
    opened_at: datetime
    state: InferenceJobState = InferenceJobState.REQUESTED
    executor: NodeAddress | None = None
    cross_verifier: NodeAddress | None = None
    encrypted_input: EncryptedInput | None = None
    executor_commit: ExecutionCommit | None = None
    verifier_commit: ExecutionCommit | None = None
    verified_output: EncryptedOutput | None = None
    attestation_digest: bytes | None = None
    on_chain_receipt_hash: bytes | None = None
    _events: list[DomainEvent] = field(default_factory=list, repr=False)

    @classmethod
    def open(
        cls,
        *,
        invocation_id: InvocationId,
        agent_id: AgentId,
        escrow_id: EscrowId,
        permitted: PermittedExecutorSet,
        opened_at: datetime,
    ) -> InferenceJob:
        job = cls(
            invocation_id=invocation_id,
            agent_id=agent_id,
            escrow_id=escrow_id,
            permitted=permitted,
            opened_at=opened_at,
        )
        job._record(
            InferenceJobOpened(
                occurred_at=opened_at,
                invocation_id=invocation_id,
                agent_id=agent_id,
                escrow_id=escrow_id,
                permitted=permitted,
            )
        )
        return job

    def dispatch(
        self,
        *,
        executor: NodeAddress,
        cross_verifier: NodeAddress,
        encrypted_input: EncryptedInput,
        at: datetime,
    ) -> None:
        self._require(InferenceJobState.REQUESTED, "dispatch")

        if executor == cross_verifier:
            raise IllegalTransition("executor and cross_verifier must differ (no self-voting)")
        if not self.permitted.includes(executor):
            raise IllegalTransition(f"executor {executor.value} not in permitted set")
        if not self.permitted.includes(cross_verifier):
            raise IllegalTransition(f"cross_verifier {cross_verifier.value} not in permitted set")

        self.executor = executor
        self.cross_verifier = cross_verifier
        self.encrypted_input = encrypted_input
        self.state = InferenceJobState.DISPATCHED

        self._record(
            InferenceJobDispatched(
                occurred_at=at,
                invocation_id=self.invocation_id,
                executor=executor,
                cross_verifier=cross_verifier,
                encrypted_input=encrypted_input,
            )
        )

    def record_commits(
        self,
        *,
        executor_commit: ExecutionCommit,
        verifier_commit: ExecutionCommit,
        at: datetime,
    ) -> None:
        self._require(InferenceJobState.DISPATCHED, "record_commits")

        if executor_commit.role is not ExecutionRole.EXECUTOR:
            raise IllegalTransition("executor_commit must have role EXECUTOR")
        if verifier_commit.role is not ExecutionRole.CROSS_VERIFIER:
            raise IllegalTransition("verifier_commit must have role CROSS_VERIFIER")
        if executor_commit.node != self.executor:
            raise IllegalTransition(f"executor_commit from wrong node {executor_commit.node.value}")
        if verifier_commit.node != self.cross_verifier:
            raise IllegalTransition(f"verifier_commit from wrong node {verifier_commit.node.value}")

        self.executor_commit = executor_commit
        self.verifier_commit = verifier_commit
        self.state = InferenceJobState.EXECUTED

        self._record(
            InferenceJobExecuted(
                occurred_at=at,
                invocation_id=self.invocation_id,
                executor_commit_digest=executor_commit.digest,
                verifier_commit_digest=verifier_commit.digest,
            )
        )

    def verify_reveals(
        self,
        *,
        executor_reveal: ExecutionReveal,
        verifier_reveal: ExecutionReveal,
        at: datetime,
    ) -> None:
        self._require(InferenceJobState.EXECUTED, "verify_reveals")
        assert self.executor_commit is not None and self.verifier_commit is not None

        if not executor_reveal.matches(self.executor_commit):
            raise CommitMismatch("executor reveal does not match commit")
        if not verifier_reveal.matches(self.verifier_commit):
            raise CommitMismatch("cross-verifier reveal does not match commit")

        if executor_reveal.output.ciphertext_handle != verifier_reveal.output.ciphertext_handle:
            raise CommitMismatch("executor and cross-verifier produced different outputs")

        self.verified_output = executor_reveal.output
        self.state = InferenceJobState.VERIFIED

        self._record(
            InferenceJobVerified(
                occurred_at=at,
                invocation_id=self.invocation_id,
                output=executor_reveal.output,
            )
        )

    def attest(self, *, at: datetime) -> bytes:
        self._require(InferenceJobState.VERIFIED, "attest")
        assert self.verified_output is not None and self.executor_commit is not None
        assert self.verifier_commit is not None

        digest = keccak(
            self.invocation_id.to_bytes(32, "big")
            + self.agent_id.to_bytes(32, "big")
            + self.executor_commit.digest
            + self.verifier_commit.digest
            + self.verified_output.ciphertext_handle
        )

        self.attestation_digest = digest
        self.state = InferenceJobState.ATTESTED

        self._record(
            InferenceJobAttested(
                occurred_at=at,
                invocation_id=self.invocation_id,
                attestation_digest=digest,
            )
        )
        return digest

    def finalize(self, *, on_chain_receipt_hash: bytes, at: datetime) -> None:
        self._require(InferenceJobState.ATTESTED, "finalize")
        if len(on_chain_receipt_hash) != 32:
            raise IllegalTransition("on_chain_receipt_hash must be 32 bytes")

        self.on_chain_receipt_hash = on_chain_receipt_hash
        self.state = InferenceJobState.FINALIZED

        self._record(
            InferenceJobFinalized(
                occurred_at=at,
                invocation_id=self.invocation_id,
                on_chain_receipt_hash=on_chain_receipt_hash,
            )
        )

    def pull_events(self) -> list[DomainEvent]:
        out, self._events = self._events, []
        return out

    def _require(self, expected: InferenceJobState, op: str) -> None:
        if self.state is not expected:
            raise IllegalTransition(
                f"Cannot {op} from state {self.state.name}; expected {expected.name}"
            )

    def _record(self, event: DomainEvent) -> None:
        self._events.append(event)
