from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from eth_account import Account
from eth_account.messages import encode_defunct
from eth_account.signers.local import LocalAccount
from hexbytes import HexBytes
from web3 import HTTPProvider, Web3
from web3.contract import Contract

from config import Settings


class Web3Client:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.w3 = Web3(HTTPProvider(settings.ARBITRUM_SEPOLIA_RPC, request_kwargs={"timeout": 30}))
        self.account: LocalAccount = Account.from_key(settings.ICL_SERVICE_PRIVATE_KEY)

    def is_connected(self) -> bool:
        try:
            return self.w3.is_connected()
        except Exception:
            return False

    def checksum_address(self, address: str) -> str:
        return Web3.to_checksum_address(address)

    def account_from_private_key(self, private_key: str) -> LocalAccount:
        return Account.from_key(private_key)

    def ensure_bytes32(self, value: str | bytes | HexBytes) -> HexBytes:
        if isinstance(value, HexBytes):
            return value
        if isinstance(value, bytes):
            return HexBytes(value)
        if value.startswith("0x") and len(value) == 66:
            return HexBytes(value)
        if len(value) == 64:
            return HexBytes(f"0x{value}")
        return Web3.keccak(text=value)

    def keccak_text(self, value: str) -> str:
        return Web3.keccak(text=value).hex()

    def task_id_to_invocation_id(self, task_id: str) -> int:
        normalized = task_id[2:] if task_id.startswith("0x") else task_id
        return int(normalized, 16)

    def sign_digest(self, digest: str | bytes | HexBytes, *, private_key: str) -> HexBytes:
        signer = self.account_from_private_key(private_key)
        payload = self.ensure_bytes32(digest)
        signed = Account.sign_message(encode_defunct(primitive=payload), private_key=signer.key)
        return HexBytes(signed.signature)

    def _artifact_candidates(self, contract_name: str) -> list[Path]:
        return [
            self.settings.contracts_out_dir / f"{contract_name}.sol" / f"{contract_name}.json",
            self.settings.contracts_dir / "artifacts" / "contracts" / f"{contract_name}.sol" / f"{contract_name}.json",
        ]

    @lru_cache(maxsize=16)
    def load_abi(self, contract_name: str) -> list[dict[str, Any]]:
        for artifact_path in self._artifact_candidates(contract_name):
            if artifact_path.exists():
                payload = json.loads(artifact_path.read_text())
                return payload["abi"]
        raise FileNotFoundError(f"Unable to locate ABI for {contract_name}")

    def get_contract(self, contract_name: str, address: str) -> Contract:
        return self.w3.eth.contract(
            address=self.checksum_address(address),
            abi=self.load_abi(contract_name),
        )

    def code_exists(self, address: str) -> bool:
        return self.w3.eth.get_code(self.checksum_address(address)) != b""

    def send_transaction(
        self,
        contract_function: Any,
        *,
        private_key: str | None = None,
        value: int = 0,
    ) -> dict[str, Any]:
        signer = self.account if private_key is None else self.account_from_private_key(private_key)
        nonce = self.w3.eth.get_transaction_count(signer.address)
        transaction = contract_function.build_transaction(
            {
                "from": signer.address,
                "nonce": nonce,
                "chainId": self.w3.eth.chain_id,
                "value": value,
                **self._fee_params(),
            }
        )
        estimated_gas = self.w3.eth.estimate_gas(transaction)
        transaction["gas"] = int(estimated_gas * 1.2)

        signed_transaction = signer.sign_transaction(transaction)
        tx_hash = self.w3.eth.send_raw_transaction(signed_transaction.raw_transaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        return {
            "tx_hash": tx_hash.hex(),
            "receipt": receipt,
        }

    def _fee_params(self) -> dict[str, int]:
        latest_block = self.w3.eth.get_block("latest")
        base_fee = latest_block.get("baseFeePerGas")
        if base_fee is None:
            return {"gasPrice": int(self.w3.eth.gas_price)}

        gas_price = int(self.w3.eth.gas_price)
        try:
            priority_fee = int(self.w3.eth.max_priority_fee)
        except Exception:
            priority_fee = max(gas_price // 10, 1_000_000)

        max_fee = max(int(base_fee) * 2 + priority_fee, gas_price * 2)
        return {
            "type": 2,
            "maxPriorityFeePerGas": priority_fee,
            "maxFeePerGas": max_fee,
        }
