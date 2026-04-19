from __future__ import annotations

from blindference_node.domain.shared_kernel.ids import NodeAddress


class InMemoryNodeAttestationProvider:
    """Test/dev stand-in for the on-chain `NodeAttestationRegistry`."""

    def __init__(self) -> None:
        self._set: set[tuple[str, bytes, str | None]] = set()

    def grant(
        self,
        *,
        node: NodeAddress,
        attestation_type: bytes,
        counterparty: NodeAddress | None = None,
    ) -> None:
        self._set.add((node.value, attestation_type, counterparty.value if counterparty else None))

    def revoke(
        self,
        *,
        node: NodeAddress,
        attestation_type: bytes,
        counterparty: NodeAddress | None = None,
    ) -> None:
        self._set.discard(
            (node.value, attestation_type, counterparty.value if counterparty else None)
        )

    def has_valid(
        self,
        *,
        node: NodeAddress,
        attestation_type: bytes,
        counterparty: NodeAddress | None = None,
    ) -> bool:
        return (
            node.value,
            attestation_type,
            counterparty.value if counterparty else None,
        ) in self._set
