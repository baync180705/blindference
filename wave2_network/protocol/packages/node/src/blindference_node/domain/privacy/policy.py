from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field

from blindference_node.application.ports.attestations import NodeAttestationProvider
from blindference_node.domain.privacy.eligibility import ExecutorEligibility
from blindference_node.domain.privacy.permitted_set import PermittedExecutorSet
from blindference_node.domain.shared_kernel.ids import NodeAddress


class PolicyViolation(Exception):
    pass


@dataclass(frozen=True, slots=True)
class PrivacyPolicy:
    """Filter that decides which nodes may be granted decryption permission.

    Two layers of enforcement:

    * `accepts(eligibility)` — node-level filter against self-published
      attributes (jurisdiction, ZDR, TEE, capabilities, stake size).
    * `assert_set_compliant(permitted, eligibilities, attestations)` — set-level
      check that includes on-chain `NodeAttestationRegistry` lookups for any
      `required_attestations` (signed off-chain commitments such as ZDR or
      bilateral legal agreements).

    Selection is always explicit. The policy filters; the agent or invocation
    caller picks the actual `PermittedExecutorSet` from the filtered pool.
    """

    minimum_quorum_size: int
    minimum_slashing_stake_wei: int
    require_zdr: bool
    require_tee: bool = False
    allowed_jurisdictions: frozenset[str] = field(default_factory=frozenset)
    required_capabilities: frozenset[str] = field(default_factory=frozenset)
    required_attestations: frozenset[bytes] = field(default_factory=frozenset)
    bilateral_counterparty: NodeAddress | None = None

    def accepts(self, eligibility: ExecutorEligibility) -> bool:
        if eligibility.slashing_stake_wei < self.minimum_slashing_stake_wei:
            return False
        if self.require_zdr and not eligibility.zdr_attested:
            return False
        if self.require_tee and not eligibility.tee_attested:
            return False
        if (
            self.allowed_jurisdictions
            and eligibility.jurisdiction not in self.allowed_jurisdictions
        ):
            return False
        return self.required_capabilities.issubset(eligibility.capabilities)

    def filter(self, candidates: Iterable[ExecutorEligibility]) -> list[ExecutorEligibility]:
        return [c for c in candidates if self.accepts(c)]

    def assert_set_compliant(
        self,
        permitted: PermittedExecutorSet,
        eligibilities: dict[NodeAddress, ExecutorEligibility],
        attestations: NodeAttestationProvider | None = None,
    ) -> None:
        if permitted.quorum_size < self.minimum_quorum_size:
            raise PolicyViolation(
                f"Quorum size {permitted.quorum_size} < minimum {self.minimum_quorum_size}"
            )

        for node in permitted.all():
            elig = eligibilities.get(node)
            if elig is None:
                raise PolicyViolation(f"No eligibility profile for node {node.value}")
            if not self.accepts(elig):
                raise PolicyViolation(f"Node {node.value} fails policy")

            if self.required_attestations:
                if attestations is None:
                    raise PolicyViolation(
                        "Policy requires attestations but no NodeAttestationProvider supplied"
                    )
                for attestation_type in self.required_attestations:
                    if not attestations.has_valid(
                        node=node,
                        attestation_type=attestation_type,
                        counterparty=self.bilateral_counterparty,
                    ):
                        raise PolicyViolation(
                            f"Node {node.value} missing attestation 0x{attestation_type.hex()}"
                        )
