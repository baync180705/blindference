from __future__ import annotations

from typing import Any

from chain.web3_client import Web3Client
from config import Settings


ROLE_EXECUTOR = 0
ROLE_CROSS_VERIFIER = 1


class ExecutionCommitmentRegistryClient:
    STATUS_NAMES = {
        0: "none",
        1: "dispatched",
        2: "partial_commit",
        3: "both_committed",
        4: "partial_reveal",
        5: "verified",
        6: "escalated",
    }

    def __init__(self, web3_client: Web3Client, settings: Settings):
        self.web3_client = web3_client
        self.settings = settings
        self.contract = web3_client.get_contract(
            "ExecutionCommitmentRegistry",
            settings.EXECUTION_COMMITMENT_REGISTRY_ADDRESS,
        )

    def dispatch(
        self,
        *,
        invocation_id: int,
        escrow_id: int,
        agent_id: int,
        executor: str,
        cross_verifier: str,
        commit_deadline: int,
        reveal_deadline: int,
    ) -> dict[str, Any]:
        function = self.contract.functions.dispatch(
            invocation_id,
            escrow_id,
            agent_id,
            self.web3_client.checksum_address(executor),
            self.web3_client.checksum_address(cross_verifier),
            commit_deadline,
            reveal_deadline,
        )
        return self.web3_client.send_transaction(function)

    def commit_digest(self, *, role: int, node: str, output_handle: str, salt: str) -> str:
        return self.contract.functions.commitDigest(
            role,
            self.web3_client.checksum_address(node),
            self.web3_client.ensure_bytes32(output_handle),
            self.web3_client.ensure_bytes32(salt),
        ).call().hex()

    def commit(
        self,
        *,
        invocation_id: int,
        role: int,
        digest: str,
        private_key: str,
    ) -> dict[str, Any]:
        function = self.contract.functions.commit(
            invocation_id,
            role,
            self.web3_client.ensure_bytes32(digest),
        )
        return self.web3_client.send_transaction(function, private_key=private_key)

    def reveal(
        self,
        *,
        invocation_id: int,
        role: int,
        output_handle: str,
        salt: str,
        private_key: str,
    ) -> dict[str, Any]:
        function = self.contract.functions.reveal(
            invocation_id,
            role,
            self.web3_client.ensure_bytes32(output_handle),
            self.web3_client.ensure_bytes32(salt),
        )
        return self.web3_client.send_transaction(function, private_key=private_key)

    def invocation(self, invocation_id: int) -> dict[str, Any]:
        value = self.contract.functions.invocation(invocation_id).call()
        status = int(value[13])
        return {
            "escrow_id": int(value[0]),
            "agent_id": int(value[1]),
            "executor": self.web3_client.checksum_address(value[2]),
            "cross_verifier": self.web3_client.checksum_address(value[3]),
            "dispatched_at": int(value[4]),
            "commit_deadline": int(value[5]),
            "reveal_deadline": int(value[6]),
            "executor_commit": value[7].hex(),
            "verifier_commit": value[8].hex(),
            "executor_output": value[9].hex(),
            "verifier_output": value[10].hex(),
            "executor_revealed": bool(value[11]),
            "verifier_revealed": bool(value[12]),
            "status_code": status,
            "status": self.STATUS_NAMES.get(status, "unknown"),
        }

    def status_of(self, invocation_id: int) -> str:
        status_code = int(self.contract.functions.statusOf(invocation_id).call())
        return self.STATUS_NAMES.get(status_code, "unknown")

    def verified_output(self, invocation_id: int) -> str:
        return self.contract.functions.verifiedOutput(invocation_id).call().hex()
