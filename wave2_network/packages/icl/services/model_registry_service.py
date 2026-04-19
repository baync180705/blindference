from __future__ import annotations

from datetime import datetime, timezone

from db.collections import MODEL_CATALOG
from models.db_models import ModelCatalogRecord
from models.request_models import ModelRegistrationRequest


class ModelRegistryService:
    def __init__(self, database):
        self.database = database
        self.collection = database[MODEL_CATALOG]

    async def ensure_default_models(self) -> None:
        defaults = [
            ModelCatalogRecord(
                model_id="groq-llm-default",
                name="Groq Hosted LLM",
                provider="groq",
                min_tier=1,
                zdr_required=False,
                metadata={"mode": "hosted-api", "agent_id": 1, "protocol_registry": "AgentConfigRegistry"},
            ),
            ModelCatalogRecord(
                model_id="gemini-llm-default",
                name="Google Gemini Hosted LLM",
                provider="google-gemini",
                min_tier=1,
                zdr_required=False,
                metadata={"mode": "hosted-api", "agent_id": 2, "protocol_registry": "AgentConfigRegistry"},
            ),
        ]

        for record in defaults:
            existing = await self.collection.find_one({"model_id": record.model_id})
            if existing is None:
                await self.collection.insert_one(record.model_dump())

    async def list_models(self) -> list[dict]:
        cursor = self.collection.find({})
        models: list[dict] = []
        async for document in cursor:
            document.pop("_id", None)
            models.append(document)
        models.sort(key=lambda model: model["model_id"])
        return models

    async def get_model(self, model_id: str) -> dict | None:
        document = await self.collection.find_one({"model_id": model_id})
        if document is None:
            return None
        document.pop("_id", None)
        return document

    async def register_model(self, payload: ModelRegistrationRequest) -> dict:
        now = datetime.now(timezone.utc)
        record = ModelCatalogRecord(
            model_id=payload.model_id,
            name=payload.name,
            provider=payload.provider,
            min_tier=payload.min_tier,
            zdr_required=payload.zdr_required,
            metadata=payload.metadata,
            created_at=now,
            updated_at=now,
        )
        await self.collection.update_one(
            {"model_id": payload.model_id},
            {"$set": record.model_dump()},
            upsert=True,
        )
        return record.model_dump()
