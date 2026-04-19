from __future__ import annotations

from chain.web3_client import Web3Client
from config import Settings


class ModelRegistryClient:
    def __init__(self, web3_client: Web3Client, settings: Settings):
        self.web3_client = web3_client
        self.settings = settings
        self.address = web3_client.checksum_address(settings.MODEL_REGISTRY_ADDRESS)

    def is_deployed(self) -> bool:
        return self.web3_client.w3.eth.get_code(self.address) != b""
