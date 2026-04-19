from __future__ import annotations

from chain.web3_client import Web3Client
from config import Settings


class ReputationRegistryClient:
    def __init__(self, web3_client: Web3Client, settings: Settings):
        self.web3_client = web3_client
        self.settings = settings
        self.contract = web3_client.get_contract(
            "ReputationRegistry",
            settings.REPUTATION_REGISTRY_ADDRESS,
        )

    def reputation_of(self, node_address: str) -> dict[str, int]:
        value = self.contract.functions.reputationOf(
            self.web3_client.checksum_address(node_address)
        ).call()
        return {
            "score": int(value[0]),
            "cycle_reset_at": int(value[1]),
            "cycles_active": int(value[2]),
            "cycles_guilty": int(value[3]),
        }
