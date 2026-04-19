from __future__ import annotations

import pytest

from blindference_node.domain.shared_kernel.ids import NodeAddress
from blindference_node.infrastructure.attestations import InMemoryNodeAttestationProvider


@pytest.mark.unit
def test_grant_then_has_valid(attestation_zdr: bytes) -> None:
    provider = InMemoryNodeAttestationProvider()
    node = NodeAddress("0x1111111111111111111111111111111111111111")
    assert provider.has_valid(node=node, attestation_type=attestation_zdr) is False

    provider.grant(node=node, attestation_type=attestation_zdr)
    assert provider.has_valid(node=node, attestation_type=attestation_zdr) is True


@pytest.mark.unit
def test_revoke_invalidates(attestation_zdr: bytes) -> None:
    provider = InMemoryNodeAttestationProvider()
    node = NodeAddress("0x1111111111111111111111111111111111111111")

    provider.grant(node=node, attestation_type=attestation_zdr)
    provider.revoke(node=node, attestation_type=attestation_zdr)
    assert provider.has_valid(node=node, attestation_type=attestation_zdr) is False


@pytest.mark.unit
def test_public_and_bilateral_are_independent(
    attestation_hipaa: bytes,
) -> None:
    provider = InMemoryNodeAttestationProvider()
    node = NodeAddress("0x1111111111111111111111111111111111111111")
    counterparty = NodeAddress("0x2222222222222222222222222222222222222222")

    provider.grant(node=node, attestation_type=attestation_hipaa)
    provider.grant(node=node, attestation_type=attestation_hipaa, counterparty=counterparty)

    assert provider.has_valid(node=node, attestation_type=attestation_hipaa) is True
    assert (
        provider.has_valid(node=node, attestation_type=attestation_hipaa, counterparty=counterparty)
        is True
    )

    provider.revoke(node=node, attestation_type=attestation_hipaa)
    assert provider.has_valid(node=node, attestation_type=attestation_hipaa) is False
    assert (
        provider.has_valid(node=node, attestation_type=attestation_hipaa, counterparty=counterparty)
        is True
    )
