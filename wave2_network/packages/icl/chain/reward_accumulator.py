from __future__ import annotations

from chain.web3_client import Web3Client
from config import Settings


class RewardAccumulatorClient:
    def __init__(self, web3_client: Web3Client, settings: Settings):
        self.web3_client = web3_client
        self.settings = settings
        self.address = web3_client.checksum_address(settings.REWARD_ACCUMULATOR_ADDRESS)

    def is_deployed(self) -> bool:
        return self.web3_client.code_exists(self.address)
