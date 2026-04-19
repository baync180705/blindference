from __future__ import annotations

from dataclasses import dataclass, field

from blindference_node.domain.shared_kernel.ids import NodeAddress


@dataclass(frozen=True, slots=True)
class ExecutorEligibility:
    """Per-node attributes the privacy policy can filter on.

    These attributes are off-chain attestations the operator publishes
    (jurisdiction, ZDR mode, slashing-stake size, etc.). The policy
    decides who is acceptable; this is just the description.
    """

    node: NodeAddress
    jurisdiction: str
    zdr_attested: bool
    slashing_stake_wei: int
    tee_attested: bool = False
    capabilities: frozenset[str] = field(default_factory=frozenset)

    def has_capability(self, capability: str) -> bool:
        return capability in self.capabilities
