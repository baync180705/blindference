from __future__ import annotations

from typing import Any

from chain.web3_client import Web3Client
from config import Settings

ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"


class PromptKeyStoreClient:
    def __init__(self, web3_client: Web3Client, settings: Settings):
        self.web3_client = web3_client
        self.settings = settings
        self.address = settings.PROMPT_KEY_STORE_ADDRESS
        self._contract = None

    @property
    def enabled(self) -> bool:
        return self.address.lower() != ZERO_ADDRESS.lower()

    @property
    def contract(self):
        if not self.enabled:
            raise RuntimeError("PromptKeyStore contract is not configured")
        if self._contract is None:
            self._contract = self.web3_client.get_contract("PromptKeyStore", self.address)
        return self._contract

    def store_key(
        self,
        *,
        job_id: str,
        encrypted_high_input: dict[str, Any],
        encrypted_low_input: dict[str, Any],
        allowed_nodes: list[str],
    ) -> dict[str, Any]:
        function = self.contract.functions.storeKey(
            self.web3_client.ensure_bytes32(job_id),
            self._normalize_encrypted_uint256_input(encrypted_high_input),
            self._normalize_encrypted_uint256_input(encrypted_low_input),
            [self.web3_client.checksum_address(address) for address in allowed_nodes],
        )
        return self.web3_client.send_transaction(function)

    def _normalize_encrypted_uint256_input(self, value: dict[str, Any]) -> tuple[int, int, int, bytes]:
        if not isinstance(value, dict):
            raise ValueError("CoFHE encrypted prompt-key input must be an object")

        ct_hash = value.get("ctHash", value.get("ct_hash"))
        security_zone = value.get("securityZone", value.get("security_zone", 0))
        utype = value.get("utype", 8)
        signature = value.get("signature")

        if ct_hash in (None, ""):
            raise ValueError("CoFHE encrypted prompt-key input is missing ctHash")
        if signature in (None, ""):
            raise ValueError("CoFHE encrypted prompt-key input is missing signature")

        return (
            int(str(ct_hash), 0),
            int(security_zone),
            int(utype),
            bytes.fromhex(str(signature).removeprefix("0x")),
        )
