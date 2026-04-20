from __future__ import annotations

import asyncio
from typing import Any
import re

import httpx

from blindference_node.cofhe_bridge import CofheBridgeClient
from blindference_node.config import NodeSettings
from blindference_node.infrastructure.executors import CloudInferenceExecutor


class BlindferenceDemoWorker:
    def __init__(self, settings: NodeSettings) -> None:
        self.settings = settings
        self.executor = CloudInferenceExecutor(settings)
        self._submitted_tasks: set[str] = set()
        self.cofhe_bridge = (
            CofheBridgeClient(
                script_path=settings.cofhe_bridge_script,
                rpc_url=settings.cofhe_rpc_url,
                chain_id=settings.cofhe_chain_id,
                private_key=settings.operator_private_key,
            )
            if settings.operator_private_key
            else None
        )

    async def run(self) -> None:
        iteration = 0
        async with httpx.AsyncClient(base_url=self.settings.icl_base_url, timeout=30.0) as client:
            while True:
                iteration += 1
                await self._process_once(client)
                if self.settings.max_iterations and iteration >= self.settings.max_iterations:
                    return
                await asyncio.sleep(self.settings.poll_interval_seconds)

    async def _process_once(self, client: httpx.AsyncClient) -> None:
        response = await client.get("/v1/inference")
        response.raise_for_status()
        requests: list[dict[str, Any]] = response.json()

        for request in requests:
            if request.get("status") != "queued":
                continue
            role = self._role_for_request(request)
            if role is None:
                continue
            submission_key = f"{request['request_id']}:{role}"
            if submission_key in self._submitted_tasks:
                continue

            metadata = request.get("metadata", {})
            provider = str(metadata.get("provider", self.settings.provider))
            model = str(metadata.get("model", self._model_for_provider(provider)))
            try:
                decrypted_features = await self._decrypt_features(
                    request.get("encrypted_features", []),
                    metadata,
                )
            except ValueError as error:
                if "Missing shared CoFHE permit" in str(error):
                    continue
                raise
            assessment = await self.executor.infer(
                features=decrypted_features,
                provider=provider,
                model=model,
            )

            if role == "leader":
                payload = {
                    "leader_address": self.cofhe_bridge.operator_address if self.cofhe_bridge else request["leader_address"],
                    "risk_score": assessment.risk_score,
                    "leader_confidence": assessment.confidence,
                    "leader_summary": assessment.response_text,
                    "provider": assessment.provider,
                    "model": assessment.model,
                    "result_hash": assessment.response_hash(),
                }
                response = await client.post(f"/v1/inference/{request['request_id']}/leader-result", json=payload)
            else:
                payload = {
                    "verifier_address": self.cofhe_bridge.operator_address if self.cofhe_bridge else "",
                    "confidence": assessment.confidence,
                    "accepted": None,
                    "reason": None,
                    "risk_score": assessment.risk_score,
                    "provider": assessment.provider,
                    "model": assessment.model,
                    "summary": assessment.response_text,
                    "result_hash": assessment.response_hash(),
                }
                response = await client.post(f"/v1/inference/{request['request_id']}/verdicts", json=payload)
            response.raise_for_status()
            self._submitted_tasks.add(submission_key)

    async def _decrypt_features(
        self,
        encrypted_features: list[dict[str, Any]],
        metadata: dict[str, Any],
    ) -> list[int]:
        decrypted: list[int] = []
        for feature in encrypted_features:
            ct_hash = str(feature.get("ct_hash") or feature.get("ctHash") or "")
            match = re.match(r"^mock:[^:]+:(-?\d+)$", ct_hash)
            if match:
                decrypted.append(int(match.group(1)))

        if len(decrypted) == len(encrypted_features):
            return decrypted

        if not self.cofhe_bridge:
            raise ValueError("Missing operator private key for CoFHE decryption.")

        permit = self._resolve_shared_permit(metadata)
        if not permit:
            raise ValueError("Missing shared CoFHE permit for this node.")

        return await self.cofhe_bridge.decrypt_for_view(
            encrypted_features=encrypted_features,
            permit=permit,
        )

    def _resolve_shared_permit(self, metadata: dict[str, Any]) -> str | None:
        operator_address = self.cofhe_bridge.operator_address.lower() if self.cofhe_bridge else ""
        for permit_record in metadata.get("permits", []):
            node_address = str(
                permit_record.get("node_address")
                or permit_record.get("node")
                or ""
            ).lower()
            serialized = permit_record.get("permit")
            status = permit_record.get("status")
            if (
                serialized
                and node_address == operator_address
                and status in {"shared-permit-attached", "shared-permit-provided"}
            ):
                return str(serialized)
        return None

    def _role_for_request(self, request: dict[str, Any]) -> str | None:
        if not self.settings.operator_private_key or not self.cofhe_bridge:
            return None
        operator_address = self.cofhe_bridge.operator_address.lower()
        assigned_leader = (request.get("leader_address") or request.get("quorum", {}).get("leader_address") or "").lower()
        verifier_addresses = [
            str(address).lower() for address in request.get("quorum", {}).get("verifier_addresses", [])
        ]
        if operator_address == assigned_leader:
            return "leader"
        if operator_address in verifier_addresses:
            return "verifier"
        return None

    def _model_for_provider(self, provider: str) -> str:
        if provider.lower() in {"gemini", "google-gemini"}:
            return self.settings.gemini_model
        return self.settings.groq_model
