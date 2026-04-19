from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from eth_utils import keccak

from blindference_node.domain.inference.encrypted_input import EncryptedInput
from blindference_node.domain.inference.encrypted_output import EncryptedOutput
from blindference_node.domain.privacy.eligibility import ExecutorEligibility
from blindference_node.domain.privacy.permitted_set import PermittedExecutorSet
from blindference_node.domain.privacy.policy import PrivacyPolicy
from blindference_node.domain.shared_kernel.ids import (
    AgentId,
    EscrowId,
    InvocationId,
    NodeAddress,
)
from blindference_node.infrastructure.attestations import InMemoryNodeAttestationProvider

ATTESTATION_ZDR = keccak(text="zdr.v1")
ATTESTATION_HIPAA = keccak(text="hipaa-baa.v1")


@pytest.fixture
def attestation_zdr() -> bytes:
    return ATTESTATION_ZDR


@pytest.fixture
def attestation_hipaa() -> bytes:
    return ATTESTATION_HIPAA


@pytest.fixture
def now() -> datetime:
    return datetime(2026, 4, 19, 12, 0, 0, tzinfo=UTC)


class FrozenClock:
    def __init__(self, instant: datetime) -> None:
        self._instant = instant

    def now(self) -> datetime:
        return self._instant

    def epoch_seconds(self) -> int:
        return int(self._instant.timestamp())

    def advance(self, delta: timedelta) -> None:
        self._instant += delta


@pytest.fixture
def frozen_clock(now: datetime) -> Iterator[FrozenClock]:
    yield FrozenClock(now)


@pytest.fixture
def leader() -> NodeAddress:
    return NodeAddress("0x1111111111111111111111111111111111111111")


@pytest.fixture
def verifiers() -> tuple[NodeAddress, ...]:
    return (
        NodeAddress("0x2222222222222222222222222222222222222222"),
        NodeAddress("0x3333333333333333333333333333333333333333"),
        NodeAddress("0x4444444444444444444444444444444444444444"),
    )


@pytest.fixture
def permitted(leader: NodeAddress, verifiers: tuple[NodeAddress, ...]) -> PermittedExecutorSet:
    return PermittedExecutorSet(leader=leader, verifiers=verifiers)


@pytest.fixture
def eligibility_set(
    leader: NodeAddress, verifiers: tuple[NodeAddress, ...]
) -> list[ExecutorEligibility]:
    base = {
        "jurisdiction": "us-east-1",
        "zdr_attested": True,
        "slashing_stake_wei": 10_000_000_000_000_000_000,
        "tee_attested": False,
        "capabilities": frozenset({"inference.v1"}),
    }
    return [
        ExecutorEligibility(node=leader, **base),
        *(ExecutorEligibility(node=v, **base) for v in verifiers),
    ]


@pytest.fixture
def privacy_policy() -> PrivacyPolicy:
    return PrivacyPolicy(
        minimum_quorum_size=4,
        minimum_slashing_stake_wei=1_000_000_000_000_000_000,
        require_zdr=True,
        allowed_jurisdictions=frozenset({"us-east-1", "eu-central-1"}),
        required_capabilities=frozenset({"inference.v1"}),
    )


@pytest.fixture
def attestations(
    permitted: PermittedExecutorSet, attestation_zdr: bytes
) -> InMemoryNodeAttestationProvider:
    """All permitted nodes have a valid public ZDR attestation by default."""
    provider = InMemoryNodeAttestationProvider()
    for node in permitted.all():
        provider.grant(node=node, attestation_type=attestation_zdr)
    return provider


@pytest.fixture
def invocation_id() -> InvocationId:
    return InvocationId(7)


@pytest.fixture
def agent_id() -> AgentId:
    return AgentId(1001)


@pytest.fixture
def escrow_id() -> EscrowId:
    return EscrowId(9001)


@pytest.fixture
def encrypted_input() -> EncryptedInput:
    return EncryptedInput(
        ciphertext_handle=b"\xab" * 32,
        permission_grant_id=b"\xcd" * 32,
        sealed_at_epoch=1_700_000_000,
        metadata={"input_type": "generic"},
    )


@pytest.fixture
def encrypted_output() -> EncryptedOutput:
    return EncryptedOutput(
        ciphertext_handle=b"\xff" * 32,
        model_version=7,
        metadata={"decimals": 4},
    )
