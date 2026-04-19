from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone

import httpx
from web3 import Web3

from blindference_node.config import NodeSettings


@dataclass(slots=True)
class BlindferenceSignal:
    asset: str
    signal: str
    confidence: int
    provider: str
    model: str
    response_text: str
    timestamp: int

    def response_hash(self, task_id: str) -> str:
        return Web3.to_hex(
            Web3.solidity_keccak(["string", "string", "uint256"], [self.response_text, task_id, self.timestamp])
        )

    def to_payload(self, *, task_id: str) -> str:
        return json.dumps(
            {
                "task_id": task_id,
                "timestamp": self.timestamp,
                "asset": self.asset,
                "signal": self.signal,
                "confidence": self.confidence,
                "provider": self.provider,
                "model": self.model,
                "response_text": self.response_text,
                "response_hash": self.response_hash(task_id),
            },
            sort_keys=True,
        )


class CloudInferenceExecutor:
    def __init__(self, settings: NodeSettings) -> None:
        self.settings = settings

    async def infer(self, *, prompt: str, asset: str, provider: str | None = None, model: str | None = None) -> BlindferenceSignal:
        selected_provider = (provider or self.settings.provider).lower()
        if self.settings.mock_cloud_inference:
            return self._mock_signal(asset=asset, provider=selected_provider, model=model)

        if selected_provider == "groq":
            return await self._groq_signal(prompt=prompt, asset=asset, model=model or self.settings.groq_model)
        if selected_provider == "gemini":
            return await self._gemini_signal(prompt=prompt, asset=asset, model=model or self.settings.gemini_model)

        return self._mock_signal(asset=asset, provider=selected_provider, model=model)

    async def _groq_signal(self, *, prompt: str, asset: str, model: str) -> BlindferenceSignal:
        if not self.settings.groq_api_key:
            return self._mock_signal(asset=asset, provider="groq", model=model)

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.settings.groq_api_key}"},
                json={
                    "model": model,
                    "temperature": 0,
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "Return strict JSON with keys signal, confidence, reasoning. "
                                "signal must be BUY, SELL, or HOLD."
                            ),
                        },
                        {"role": "user", "content": f"Asset: {asset}\nPrompt: {prompt}"},
                    ],
                },
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            return self._parse_model_response(content=content, asset=asset, provider="groq", model=model)

    async def _gemini_signal(self, *, prompt: str, asset: str, model: str) -> BlindferenceSignal:
        if not self.settings.gemini_api_key:
            return self._mock_signal(asset=asset, provider="gemini", model=model)

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                params={"key": self.settings.gemini_api_key},
                json={
                    "generationConfig": {"temperature": 0},
                    "contents": [
                        {
                            "parts": [
                                {
                                    "text": (
                                        "Return strict JSON with keys signal, confidence, reasoning. "
                                        f"Asset: {asset}. Prompt: {prompt}"
                                    )
                                }
                            ]
                        }
                    ],
                },
            )
            response.raise_for_status()
            content = response.json()["candidates"][0]["content"]["parts"][0]["text"]
            return self._parse_model_response(content=content, asset=asset, provider="gemini", model=model)

    def _parse_model_response(self, *, content: str, asset: str, provider: str, model: str) -> BlindferenceSignal:
        parsed = json.loads(content)
        signal = str(parsed.get("signal", "HOLD")).upper()
        if signal not in {"BUY", "SELL", "HOLD"}:
            signal = "HOLD"
        confidence = int(parsed.get("confidence", self.settings.confidence_floor))
        confidence = max(1, min(confidence, 100))
        reasoning = str(parsed.get("reasoning", content)).strip()
        timestamp = int(datetime.now(timezone.utc).timestamp())
        return BlindferenceSignal(
            asset=asset,
            signal=signal,
            confidence=confidence,
            provider=provider,
            model=model,
            response_text=reasoning,
            timestamp=timestamp,
        )

    def _mock_signal(self, *, asset: str, provider: str, model: str | None) -> BlindferenceSignal:
        normalized_asset = asset.upper()
        if normalized_asset == "BTC":
            signal = "HOLD"
            confidence = 79
        elif normalized_asset == "ETH":
            signal = "BUY"
            confidence = 84
        else:
            signal = "SELL"
            confidence = 76

        timestamp = int(datetime.now(timezone.utc).timestamp())
        response_text = (
            f"{signal} {normalized_asset} for the demo horizon. "
            f"Provider={provider or self.settings.provider}, confidence={confidence}."
        )
        return BlindferenceSignal(
            asset=normalized_asset,
            signal=signal,
            confidence=confidence,
            provider=provider or self.settings.provider,
            model=model or self.settings.groq_model,
            response_text=response_text,
            timestamp=timestamp,
        )
