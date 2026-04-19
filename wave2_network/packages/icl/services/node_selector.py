from __future__ import annotations

from services.chain_service import ChainService


class NodeSelector:
    def __init__(self, chain_service: ChainService):
        self.chain_service = chain_service

    async def select_quorum(
        self,
        *,
        min_tier: int,
        zdr_required: bool,
        verifier_count: int,
    ) -> dict[str, list[str] | str]:
        candidate_addresses = await self.chain_service.get_active_nodes(min_tier, zdr_required)
        if len(candidate_addresses) < verifier_count + 1:
            raise ValueError("not enough active nodes available for the requested quorum")

        candidate_snapshots = [
            await self.chain_service.get_node_snapshot(candidate_address)
            for candidate_address in candidate_addresses
        ]
        candidate_snapshots.sort(
            key=lambda snapshot: (
                -snapshot["metrics"]["reputation_score"],
                -snapshot["metrics"]["tasks_accepted"],
                snapshot["metrics"]["tasks_rejected"],
                snapshot["operator_address"],
            )
        )

        leader = candidate_snapshots[0]["operator_address"]
        verifiers = [
            snapshot["operator_address"]
            for snapshot in candidate_snapshots[1 : verifier_count + 1]
        ]
        ordered_candidates = [
            snapshot["operator_address"] for snapshot in candidate_snapshots
        ]

        return {
            "leader_address": leader,
            "verifier_addresses": verifiers,
            "candidate_addresses": ordered_candidates,
        }
