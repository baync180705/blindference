from __future__ import annotations

from typing import Protocol

from blindference_node.domain.shared_kernel.ids import NodeAddress


class NodeAttestationProvider(Protocol):
    """Read-side port over the on-chain `NodeAttestationRegistry`.

    `attestation_type` is a 32-byte canonical identifier (typically
    `keccak256("zdr.v1")`, `keccak256("hipaa-baa.v1")`, etc.).

    `counterparty=None` queries the public attestation slot;
    a non-None counterparty queries the bilateral slot for that counterparty.
    """

    def has_valid(
        self,
        *,
        node: NodeAddress,
        attestation_type: bytes,
        counterparty: NodeAddress | None = None,
    ) -> bool: ...
