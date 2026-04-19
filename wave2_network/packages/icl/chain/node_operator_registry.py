from __future__ import annotations

from typing import Any

from chain.web3_client import Web3Client
from config import Settings


class NodeOperatorRegistryClient:
    def __init__(self, web3_client: Web3Client, settings: Settings):
        self.web3_client = web3_client
        self.settings = settings
        self.contract = web3_client.get_contract(
            "NodeOperatorRegistry",
            settings.NODE_OPERATOR_REGISTRY_ADDRESS,
        )

    def get_active_nodes(self, min_tier: int, zdr_required: bool) -> list[str]:
        return [
            self.web3_client.checksum_address(address)
            for address in self.contract.functions.getActiveNodes(min_tier, zdr_required).call()
        ]

    def get_node_info(self, node_address: str) -> dict[str, Any]:
        node_tuple = self.contract.functions.nodes(
            self.web3_client.checksum_address(node_address)
        ).call()
        inferred_tiers = self._infer_model_tiers(int(node_tuple[5]))
        return {
            "operator_address": self.web3_client.checksum_address(node_tuple[0]),
            "ipfs_cid": node_tuple[1],
            "model_tiers": inferred_tiers,
            "location": node_tuple[2],
            "zdr_compliant": bool(node_tuple[3]),
            "jurisdiction": node_tuple[4],
            "min_stake": int(node_tuple[5]),
            "registered_at": int(node_tuple[6]),
            "last_heartbeat": int(node_tuple[7]),
            "tasks_completed": int(node_tuple[8]),
            "tasks_accepted": int(node_tuple[9]),
            "tasks_rejected": int(node_tuple[10]),
            "total_slash_amount": int(node_tuple[11]),
            "reputation_score": int(node_tuple[12]),
            "active": bool(node_tuple[13]),
        }

    def get_node_metrics(self, node_address: str) -> dict[str, int]:
        metrics = self.contract.functions.getNodeMetrics(
            self.web3_client.checksum_address(node_address)
        ).call()
        return {
            "tasks_completed": int(metrics[0]),
            "tasks_accepted": int(metrics[1]),
            "tasks_rejected": int(metrics[2]),
            "reputation_score": int(metrics[3]),
            "total_slash_amount": int(metrics[4]),
            "last_heartbeat": int(metrics[5]),
        }

    def is_active(self, node_address: str) -> bool:
        return bool(
            self.contract.functions.isActive(
                self.web3_client.checksum_address(node_address)
            ).call()
        )

    def register_node(
        self,
        *,
        private_key: str,
        ipfs_cid: str,
        model_tiers: list[int],
        location: str,
        zdr_compliant: bool,
        jurisdiction: str,
        stake_wei: int,
    ) -> dict[str, Any]:
        function = self.contract.functions.register(
            ipfs_cid,
            model_tiers,
            location,
            zdr_compliant,
            jurisdiction,
        )
        return self.web3_client.send_transaction(function, private_key=private_key, value=stake_wei)

    def update_heartbeat(self, *, private_key: str) -> dict[str, Any]:
        function = self.contract.functions.updateHeartbeat()
        return self.web3_client.send_transaction(function, private_key=private_key)

    def _infer_model_tiers(self, min_stake: int) -> list[int]:
        if min_stake >= 50_000:
            return [2]
        if min_stake >= 15_000:
            return [1]
        if min_stake > 0:
            return [0]
        return []
