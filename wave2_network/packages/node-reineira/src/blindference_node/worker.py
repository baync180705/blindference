from __future__ import annotations

import asyncio
import logging
from typing import Any
import re

import httpx

from blindference_node.cofhe_bridge import CofheBridgeClient
from blindference_node.config import NodeSettings
from blindference_node.infrastructure.executors import CloudInferenceExecutor
from blindference_node.infrastructure.executors.cloud_provider import run_text_inference
from blindference_node.text_handler import process_text_task_as_leader, process_text_task_as_verifier


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
        if bool(request.get("text_mode")) or str(request.get("mode", "")).lower() == "text":
            await self._handle_text_request(client, request, role, submission_key)
            return

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

    async def _handle_text_request(
        self,
        client: httpx.AsyncClient,
        request: dict[str, Any],
        role: str,
        submission_key: str,
    ) -> None:
        operator_address = self.cofhe_bridge.operator_address if self.cofhe_bridge else "unknown"
        logger.info(
            "[%s] processing text task request_id=%s task_id=%s role=%s model_id=%s",
            operator_address,
            request.get("request_id"),
            request.get("task_id"),
            role,
            request.get("model_id"),
        )

        config = {
            "icl_base_url": self.settings.icl_base_url,
            "llm_model": self.settings.llm_model,
            "operator_address": self.cofhe_bridge.operator_address if self.cofhe_bridge else "",
            "decrypt_prompt_key": self._decrypt_text_prompt_key,
            "encrypt_output_key": self._encrypt_text_output_key,
            "text_stub_prompt_key_hex": self.settings.text_stub_prompt_key_hex,
            "submit_leader_text_result": lambda job_id, payload: self.submit_leader_text_result(client, job_id, payload),
            "submit_verifier_text_verdict": lambda job_id, payload: self.submit_verifier_text_verdict(client, job_id, payload),
        }

        if role == "leader":
            result = await process_text_task_as_leader(
                request,
                lambda prompt, model_name=None: run_text_inference(prompt, model_name=model_name, settings=self.settings),
                config,
            )
        else:
            result = await process_text_task_as_verifier(
                request,
                lambda prompt, model_name=None: run_text_inference(prompt, model_name=model_name, settings=self.settings),
                config,
            )

        logger.info(
            "[%s] text submission accepted by ICL for task_id=%s result=%s",
            operator_address,
            request.get("task_id"),
            result.get("icl_response"),
        )
        self._submitted_tasks.add(submission_key)

    async def _decrypt_text_prompt_key(self, high_handle: str, low_handle: str) -> bytes:
        if self.cofhe_bridge:
            return await self.cofhe_bridge.decrypt_prompt_key(
                high_handle=high_handle,
                low_handle=low_handle,
            )

        if self.settings.text_stub_prompt_key_hex:
            return bytes.fromhex(self.settings.text_stub_prompt_key_hex.removeprefix("0x"))
        raise ValueError("No CoFHE bridge configured for text prompt-key decryption")

    async def _encrypt_text_output_key(self, values: list[int]) -> dict[str, dict[str, Any]]:
        if self.cofhe_bridge:
            encrypted = await self.cofhe_bridge.encrypt_uint256_values(values=values)
            if len(encrypted) != 2:
                raise ValueError(f"Expected 2 encrypted output-key halves, received {len(encrypted)}")
            return {
                "high": dict(encrypted[0]),
                "low": dict(encrypted[1]),
            }

        return {
            "high": {"ctHash": str(values[0]), "securityZone": 0, "utype": 8, "signature": "0x"},
            "low": {"ctHash": str(values[1]), "securityZone": 0, "utype": 8, "signature": "0x"},
        }

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

    async def submit_leader_text_result(
        self,
        client: httpx.AsyncClient,
        job_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        response = await client.post(
            "/internal/task/result",
            json={"job_id": job_id, **payload},
        )
        response.raise_for_status()
        return response.json()

    async def submit_verifier_text_verdict(
        self,
        client: httpx.AsyncClient,
        job_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        response = await client.post(
            "/internal/task/verify",
            json={"job_id": job_id, **payload},
        )
        response.raise_for_status()
        return response.json()
