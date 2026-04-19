from __future__ import annotations

import asyncio
from typing import Any

import httpx

from blindference_node.config import NodeSettings
from blindference_node.infrastructure.executors import CloudInferenceExecutor


class BlindferenceDemoWorker:
    def __init__(self, settings: NodeSettings) -> None:
        self.settings = settings
        self.executor = CloudInferenceExecutor(settings)

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

            metadata = request.get("metadata", {})
            asset = str(metadata.get("asset", self._extract_asset(request.get("prompt", ""))))
            provider = str(metadata.get("provider", self.settings.provider))
            model = str(metadata.get("model", self._model_for_provider(provider)))
            signal = await self.executor.infer(
                prompt=request["prompt"],
                asset=asset,
                provider=provider,
                model=model,
            )

            verifier_verdicts = [
                {
                    "verifier_address": verifier_address,
                    "accepted": True,
                    "confidence": signal.confidence,
                    "reason": f"Matched {signal.signal} thesis from {signal.provider}.",
                }
                for verifier_address in request["quorum"]["verifier_addresses"]
            ]

            leader_output = signal.to_payload(task_id=request["task_id"])
            payload = {
                "leader_output": leader_output,
                "leader_confidence": signal.confidence,
                "result_hash": signal.response_hash(request["task_id"]),
                "verifier_verdicts": verifier_verdicts,
            }
            commit_response = await client.post(f"/v1/inference/{request['request_id']}/commit", json=payload)
            commit_response.raise_for_status()

    def _extract_asset(self, prompt: str) -> str:
        upper = prompt.upper()
        for asset in ("ETH", "BTC", "SOL"):
            if asset in upper:
                return asset
        return "ETH"

    def _model_for_provider(self, provider: str) -> str:
        if provider.lower() == "gemini":
            return self.settings.gemini_model
        return self.settings.groq_model
