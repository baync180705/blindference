from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone

import httpx
from web3 import Web3

from blindference_node.config import NodeSettings


def build_risk_prompt(features: list[int]) -> str:
    credit_score, amount, age, defaults = features
    return (
        "You are a credit risk assessor. Based on the following applicant data:\n"
        f"- Credit score: {credit_score}\n"
        f"- Loan amount requested: ${amount}\n"
        f"- Account age: {age} days\n"
        f"- Previous defaults: {defaults}\n"
        "Output a single integer between 0 and 100 representing the risk score "
        "(0 = lowest risk, 100 = highest risk). Reply with ONLY the number."
    )


@dataclass(slots=True)
class BlindferenceRiskAssessment:
    risk_score: int
    confidence: int
    provider: str
    model: str
    response_text: str
    timestamp: int
    features: list[int]

    def response_hash(self) -> str:
        return Web3.to_hex(Web3.solidity_keccak(["uint256"], [self.risk_score]))

    def to_payload(self, *, task_id: str, loan_id: str | None) -> str:
        return json.dumps(
            {
                "task_id": task_id,
                "loan_id": loan_id,
                "timestamp": self.timestamp,
                "risk_score": self.risk_score,
                "confidence": self.confidence,
                "provider": self.provider,
                "model": self.model,
                "summary": self.response_text,
                "response_hash": self.response_hash(),
            },
            sort_keys=True,
        )


class CloudInferenceExecutor:
    def __init__(self, settings: NodeSettings) -> None:
        self.settings = settings

    async def infer(
        self,
        *,
        features: list[int],
        provider: str | None = None,
        model: str | None = None,
    ) -> BlindferenceRiskAssessment:
        selected_provider = (provider or self.settings.provider).lower()
        prompt = build_risk_prompt(features)
        if self.settings.mock_cloud_inference:
            return self._mock_risk_assessment(features=features, provider=selected_provider, model=model)

        if selected_provider == "groq":
            return await self._groq_risk_assessment(prompt=prompt, features=features, model=model or self.settings.groq_model)
        if selected_provider == "gemini":
            return await self._gemini_risk_assessment(
                prompt=prompt,
                features=features,
                model=model or self.settings.gemini_model,
            )

        return self._mock_risk_assessment(features=features, provider=selected_provider, model=model)

    async def _groq_risk_assessment(
        self,
        *,
        prompt: str,
        features: list[int],
        model: str,
    ) -> BlindferenceRiskAssessment:
        if not self.settings.groq_api_key:
            return self._mock_risk_assessment(features=features, provider="groq", model=model)

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.settings.groq_api_key}"},
                json={
                    "model": model,
                    "temperature": 0,
                    "messages": [
                        {"role": "system", "content": "Reply with only a single integer from 0 to 100."},
                        {"role": "user", "content": prompt},
                    ],
                },
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            return self._parse_model_response(content=content, features=features, provider="groq", model=model)

    async def _gemini_risk_assessment(
        self,
        *,
        prompt: str,
        features: list[int],
        model: str,
    ) -> BlindferenceRiskAssessment:
        if not self.settings.gemini_api_key:
            return self._mock_risk_assessment(features=features, provider="gemini", model=model)

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                params={"key": self.settings.gemini_api_key},
                json={
                    "generationConfig": {"temperature": 0},
                    "contents": [{"parts": [{"text": prompt}]}],
                },
            )
            response.raise_for_status()
            content = response.json()["candidates"][0]["content"]["parts"][0]["text"]
            return self._parse_model_response(content=content, features=features, provider="gemini", model=model)

    def _parse_model_response(
        self,
        *,
        content: str,
        features: list[int],
        provider: str,
        model: str,
    ) -> BlindferenceRiskAssessment:
        match = re.search(r"\b(\d{1,3})\b", content)
        risk_score = int(match.group(1)) if match else self._heuristic_score(features)
        risk_score = max(0, min(risk_score, 100))
        confidence = max(self.settings.confidence_floor, 80)
        timestamp = int(datetime.now(timezone.utc).timestamp())
        return BlindferenceRiskAssessment(
            risk_score=risk_score,
            confidence=confidence,
            provider=provider,
            model=model,
            response_text=f"Model returned risk score {risk_score} for features {features}. Raw response: {content.strip()}",
            timestamp=timestamp,
            features=features,
        )

    def _mock_risk_assessment(
        self,
        *,
        features: list[int],
        provider: str,
        model: str | None,
    ) -> BlindferenceRiskAssessment:
        risk_score = self._heuristic_score(features)
        timestamp = int(datetime.now(timezone.utc).timestamp())
        return BlindferenceRiskAssessment(
            risk_score=risk_score,
            confidence=max(self.settings.confidence_floor, 82),
            provider=provider or self.settings.provider,
            model=model or self.settings.groq_model,
            response_text=(
                "Mock risk assessment derived from numeric features: "
                f"credit_score={features[0]}, loan_amount={features[1]}, account_age={features[2]}, "
                f"previous_defaults={features[3]}."
            ),
            timestamp=timestamp,
            features=features,
        )

    def _heuristic_score(self, features: list[int]) -> int:
        credit_score, amount, age, defaults = features
        score = 0
        score += max(0, min(100, int((850 - credit_score) / 5)))
        score += max(0, min(30, int(amount / 2000)))
        score += max(0, min(25, defaults * 12))
        score -= max(0, min(20, int(age / 365)))
        return max(0, min(100, score))
