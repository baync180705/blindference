from __future__ import annotations

from dataclasses import dataclass

from blindference_node.domain.shared_kernel.ids import NodeAddress


@dataclass(frozen=True, slots=True)
class PermittedExecutorSet:
    """The exact set of node operators authorized to decrypt this invocation's data.

    Confidentiality model: same trust level as sharing data with a cloud provider —
    these operators see the plaintext to run the model. Anyone outside this set
    sees only the FHE-encrypted handle that lives on-chain.

    Enforcement: CoFHE permission grants gate the decryption keys; on-chain
    slashing + legal commitments back the privacy contract.
    """

    leader: NodeAddress
    verifiers: tuple[NodeAddress, ...]

    def __post_init__(self) -> None:
        if len(self.verifiers) < 1:
            raise ValueError("At least one verifier is required")
        all_nodes = (self.leader, *self.verifiers)
        if len({n.value for n in all_nodes}) != len(all_nodes):
            raise ValueError("Leader and verifiers must all be distinct")

    @property
    def quorum_size(self) -> int:
        return 1 + len(self.verifiers)

    def includes(self, node: NodeAddress) -> bool:
        return node == self.leader or node in self.verifiers

    def all(self) -> tuple[NodeAddress, ...]:
        return (self.leader, *self.verifiers)
