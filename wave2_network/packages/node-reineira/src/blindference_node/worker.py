from __future__ import annotations

import asyncio
import logging
from typing import Any
import re

import httpx

from blindference_node.cofhe_bridge import CofheBridgeClient
from blindference_node.config import NodeSettings
from blindference_node.infrastructure.executors import CloudInferenceExecutor


logger = logging.getLogger("blindference.node")


class BlindferenceDemoWorker:
    def __init__(self, settings: NodeSettings) -> None:
        self.settings = settings
        self.executor = CloudInferenceExecutor(settings)
        self._submitted_tasks: set[str] = set()
        self._task_queue: asyncio.Queue[tuple[dict[str, Any], str]] = asyncio.Queue()
        self.cofhe_bridge = (
            CofheBridgeClient(
                script_path=settings.cofhe_bridge_script,
                rpc_url=settings.rpc_url,
                chain_id=settings.cofhe_chain_id,
                private_key=settings.operator_private_key,
            )
            if settings.operator_private_key
            else None
        )

    async def run(self) -> None:
        async with httpx.AsyncClient(base_url=self.settings.icl_base_url, timeout=30.0) as client:
            while True:
                request, role = await self._task_queue.get()
                try:
                    submission_key = f"{request['request_id']}:{role}"
                    if submission_key in self._submitted_tasks:
                        continue
                    await self._handle_request(client, request, role, submission_key)
                except Exception:
                    logger.exception(
                        "Task processing failed for request_id=%s task_id=%s role=%s",
                        request.get("request_id"),
                        request.get("task_id"),
                        role,
                    )
                finally:
                    self._task_queue.task_done()

    async def enqueue_task(self, request: dict[str, Any], role: str) -> None:
        await self._task_queue.put((request, role))
        logger.info(
            "Queued pushed task request_id=%s task_id=%s role=%s queue_size=%s",
            request.get("request_id"),
            request.get("task_id"),
            role,
            self._task_queue.qsize(),
        )

    async def _handle_request(
        self,
        client: httpx.AsyncClient,
        request: dict[str, Any],
        role: str,
        submission_key: str,
    ) -> None:
        operator_address = self.cofhe_bridge.operator_address if self.cofhe_bridge else "unknown"
        logger.info(
            "[%s] picked task request_id=%s task_id=%s role=%s model_id=%s",
            operator_address,
            request.get("request_id"),
            request.get("task_id"),
            role,
            request.get("model_id"),
        )

        metadata = request.get("metadata", {})
        provider = str(metadata.get("provider", self.settings.provider))
        model = str(metadata.get("model", self._model_for_provider(provider)))

        logger.info("[%s] checking permit for task_id=%s", operator_address, request.get("task_id"))
        try:
            decrypted_features = await self._decrypt_features(
                request.get("encrypted_features", []),
                metadata,
            )
        except ValueError as error:
            if "Missing shared CoFHE permit" in str(error):
                logger.info("[%s] permit not attached yet for task_id=%s", operator_address, request.get("task_id"))
                return
            raise

        logger.info(
            "[%s] decrypted features for task_id=%s values=%s",
            operator_address,
            request.get("task_id"),
            decrypted_features,
        )
        logger.info(
            "[%s] starting inference for task_id=%s provider=%s model=%s",
            operator_address,
            request.get("task_id"),
            provider,
            model,
        )
        assessment = await self.executor.infer(
            features=decrypted_features,
            provider=provider,
            model=model,
        )
        result_hash = assessment.response_hash()
        logger.info(
            "[%s] completed inference for task_id=%s risk_score=%s result_hash=%s",
            operator_address,
            request.get("task_id"),
            assessment.risk_score,
            result_hash,
        )

        if role == "leader":
            payload = {
                "leader_address": self.cofhe_bridge.operator_address if self.cofhe_bridge else request["leader_address"],
                "risk_score": assessment.risk_score,
                "leader_confidence": assessment.confidence,
                "leader_summary": assessment.response_text,
                "provider": assessment.provider,
                "model": assessment.model,
                "result_hash": result_hash,
            }
            logger.info("[%s] submitting leader result for task_id=%s", operator_address, request.get("task_id"))
            response = await client.post(f"/v1/inference/{request['request_id']}/leader-result", json=payload)
        else:
            payload = {
                "verifier_address": self.cofhe_bridge.operator_address if self.cofhe_bridge else "",
                "confidence": assessment.confidence,
                "accepted": True,
                "reason": None,
                "risk_score": assessment.risk_score,
                "provider": assessment.provider,
                "model": assessment.model,
                "summary": assessment.response_text,
                "result_hash": result_hash,
            }
            logger.info("[%s] submitting verifier verdict for task_id=%s", operator_address, request.get("task_id"))
            response = await client.post(f"/v1/inference/{request['request_id']}/verdicts", json=payload)
        response.raise_for_status()
        logger.info(
            "[%s] submission accepted by ICL for task_id=%s response=%s",
            operator_address,
            request.get("task_id"),
            response.text,
        )
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

        # Mock CoFHE decrypt path — used when the threshold network cannot be reached
        # because the browser-generated ctHashes have no on-chain ACL entry.
        # Enabled via BLINDFERENCE_NODE_MOCK_COFHE_DECRYPT=true.
        # The entire rest of the pipeline (LLM inference, quorum, on-chain commitment)
        # remains real; only the decryption step is substituted with representative values.
        if self.settings.mock_cofhe_decrypt:
            n = len(encrypted_features)
            # Representative loan-risk feature defaults that produce a non-trivial risk score.
            # Order matches the frontend: credit_score, loan_amount, account_age, prev_defaults.
            defaults = [680, 25000, 730, 0]
            mock_values = (defaults * ((n // len(defaults)) + 1))[:n]
            operator_address = self.cofhe_bridge.operator_address if self.cofhe_bridge else "unknown"
            logger.warning(
                "[%s] MOCK_COFHE_DECRYPT enabled: returning placeholder feature values %s "
                "(threshold network ACL auth not available for browser-encrypted ctHashes)",
                operator_address,
                mock_values,
            )
            return mock_values

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

    def _model_for_provider(self, provider: str) -> str:
        if provider.lower() in {"gemini", "google-gemini"}:
            return self.settings.gemini_model
        return self.settings.groq_model
