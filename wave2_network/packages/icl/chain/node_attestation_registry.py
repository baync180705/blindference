from __future__ import annotations

from typing import Any

from chain.web3_client import Web3Client
from config import Settings


class NodeAttestationRegistryClient:
    def __init__(self, web3_client: Web3Client, settings: Settings):
        self.web3_client = web3_client
        self.settings = settings
        self.contract = web3_client.get_contract(
            "NodeAttestationRegistry",
            settings.NODE_ATTESTATION_REGISTRY_ADDRESS,
        )

    def has_valid(self, node_address: str, attestation_type: str, counterparty: str) -> bool:
        return bool(
            self.contract.functions.hasValid(
                self.web3_client.checksum_address(node_address),
                self.web3_client.ensure_bytes32(attestation_type),
                self.web3_client.checksum_address(counterparty),
            ).call()
        )

    def digest(
        self,
        *,
        node_address: str,
        attestation_type: str,
        document_hash: str,
        counterparty: str,
        effective_at: int,
        expires_at: int,
    ) -> str:
        return self.contract.functions.digest(
            self.web3_client.checksum_address(node_address),
            self.web3_client.ensure_bytes32(attestation_type),
            self.web3_client.ensure_bytes32(document_hash),
            self.web3_client.checksum_address(counterparty),
            effective_at,
            expires_at,
        ).call().hex()

    def commit(
        self,
        *,
        node_address: str,
        attestation_type: str,
        document_hash: str,
        counterparty: str,
        effective_at: int,
        expires_at: int,
        signature: bytes,
        private_key: str | None = None,
    ) -> dict[str, Any]:
        function = self.contract.functions.commit(
            self.web3_client.checksum_address(node_address),
            self.web3_client.ensure_bytes32(attestation_type),
            self.web3_client.ensure_bytes32(document_hash),
            self.web3_client.checksum_address(counterparty),
            effective_at,
            expires_at,
            signature,
        )
        return self.web3_client.send_transaction(function, private_key=private_key)
