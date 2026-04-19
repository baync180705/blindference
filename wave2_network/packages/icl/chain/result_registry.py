from __future__ import annotations

from typing import Any

from chain.web3_client import Web3Client
from config import Settings


class ResultRegistryClient:
    def __init__(self, web3_client: Web3Client, settings: Settings):
        self.web3_client = web3_client
        self.settings = settings
        self.contract = web3_client.get_contract("ResultRegistry", settings.RESULT_REGISTRY_ADDRESS)

    def register_developer(self, task_id: str, developer_address: str) -> dict[str, Any]:
        function = self.contract.functions.registerDeveloper(
            self.web3_client.ensure_bytes32(task_id),
            self.web3_client.checksum_address(developer_address),
        )
        return self.web3_client.send_transaction(function)

    def commit_result(
        self,
        *,
        task_id: str,
        result_hash: str,
        leader: str,
        verifiers: list[str],
        confirm_count: int,
        reject_count: int,
        aggregated_confidence: int,
        model_id: str,
    ) -> dict[str, Any]:
        function = self.contract.functions.commitResult(
            self.web3_client.ensure_bytes32(task_id),
            self.web3_client.ensure_bytes32(result_hash),
            self.web3_client.checksum_address(leader),
            [self.web3_client.checksum_address(verifier) for verifier in verifiers],
            confirm_count,
            reject_count,
            aggregated_confidence,
            self.web3_client.ensure_bytes32(model_id),
        )
        return self.web3_client.send_transaction(function)

    def commit_rejection(
        self,
        *,
        task_id: str,
        leader: str,
        verifiers: list[str],
        model_id: str,
        reason: str,
    ) -> dict[str, Any]:
        function = self.contract.functions.commitRejection(
            self.web3_client.ensure_bytes32(task_id),
            self.web3_client.checksum_address(leader),
            [self.web3_client.checksum_address(verifier) for verifier in verifiers],
            self.web3_client.ensure_bytes32(model_id),
            reason,
        )
        return self.web3_client.send_transaction(function)

    def get_result(self, task_id: str) -> dict[str, Any]:
        result_tuple = self.contract.functions.getResult(self.web3_client.ensure_bytes32(task_id)).call()
        return {
            "task_id": result_tuple[0].hex(),
            "result_hash": result_tuple[1].hex(),
            "leader_address": self.web3_client.checksum_address(result_tuple[2]),
            "verifier_addresses": [
                self.web3_client.checksum_address(verifier) for verifier in result_tuple[3]
            ],
            "confirm_count": int(result_tuple[4]),
            "reject_count": int(result_tuple[5]),
            "aggregated_confidence": int(result_tuple[6]),
            "model_id": result_tuple[7].hex(),
            "committed_at": int(result_tuple[8]),
            "status": int(result_tuple[9]),
            "dispute_deadline": int(result_tuple[10]),
            "coverage_id": result_tuple[11].hex(),
        }
