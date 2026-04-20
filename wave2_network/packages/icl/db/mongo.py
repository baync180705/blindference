from __future__ import annotations

import logging
from copy import deepcopy
from dataclasses import dataclass
from types import SimpleNamespace
from uuid import uuid4

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import ASCENDING

from config import Settings, get_settings
from db.collections import (
    DISPUTES,
    INFERENCE_REQUESTS,
    MODEL_CATALOG,
    OPERATORS,
    PERMITS,
    QUORUM_ASSIGNMENTS,
    QUORUM_CERTIFICATES,
    VERIFIER_VERDICTS,
)

logger = logging.getLogger("blindference.icl.mongo")

_client: AsyncIOMotorClient | None = None


@dataclass(slots=True)
class InMemoryCursor:
    documents: list[dict]
    index: int = 0

    def __aiter__(self):
        return self

    async def __anext__(self) -> dict:
        if self.index >= len(self.documents):
            raise StopAsyncIteration
        document = deepcopy(self.documents[self.index])
        self.index += 1
        return document


class InMemoryCollection:
    def __init__(self):
        self.documents: list[dict] = []

    async def create_index(self, *_args, **_kwargs) -> None:
        return None

    async def insert_one(self, document: dict) -> SimpleNamespace:
        stored = deepcopy(document)
        stored.setdefault("_id", uuid4().hex)
        self.documents.append(stored)
        return SimpleNamespace(inserted_id=stored["_id"])

    async def find_one(self, query: dict) -> dict | None:
        for document in self.documents:
            if self._matches(document, query):
                return deepcopy(document)
        return None

    async def update_one(self, query: dict, update: dict, upsert: bool = False) -> SimpleNamespace:
        for index, document in enumerate(self.documents):
            if self._matches(document, query):
                new_document = deepcopy(document)
                new_document.update(deepcopy(update.get("$set", {})))
                self.documents[index] = new_document
                return SimpleNamespace(matched_count=1, modified_count=1, upserted_id=None)

        if upsert:
            new_document = deepcopy(query)
            new_document.update(deepcopy(update.get("$set", {})))
            new_document.setdefault("_id", uuid4().hex)
            self.documents.append(new_document)
            return SimpleNamespace(matched_count=0, modified_count=0, upserted_id=new_document["_id"])

        return SimpleNamespace(matched_count=0, modified_count=0, upserted_id=None)

    def find(self, query: dict) -> InMemoryCursor:
        matched = [document for document in self.documents if self._matches(document, query)]
        return InMemoryCursor(deepcopy(matched))

    def _matches(self, document: dict, query: dict) -> bool:
        return all(document.get(key) == value for key, value in query.items())


class InMemoryDatabase:
    def __init__(self):
        self._collections: dict[str, InMemoryCollection] = {}

    def __getitem__(self, name: str) -> InMemoryCollection:
        if name not in self._collections:
            self._collections[name] = InMemoryCollection()
        return self._collections[name]

    async def command(self, command_name: str) -> dict[str, int]:
        if command_name == "ping":
            return {"ok": 1}
        raise ValueError(f"unsupported command: {command_name}")


def get_mongo_client(settings: Settings | None = None) -> AsyncIOMotorClient:
    global _client
    if _client is None:
        resolved_settings = settings or get_settings()
        _client = AsyncIOMotorClient(
            resolved_settings.MONGO_URI,
            serverSelectionTimeoutMS=1_000,
            connectTimeoutMS=1_000,
        )
    return _client


async def get_database(settings: Settings | None = None) -> AsyncIOMotorDatabase:
    resolved_settings = settings or get_settings()
    client = get_mongo_client(resolved_settings)
    return client[resolved_settings.MONGO_DB_NAME]


async def ensure_indexes(database: AsyncIOMotorDatabase) -> None:
    await database[INFERENCE_REQUESTS].create_index(
        [("request_id", ASCENDING)],
        unique=True,
    )
    await database[INFERENCE_REQUESTS].create_index([("task_id", ASCENDING)], unique=True)
    await database[QUORUM_ASSIGNMENTS].create_index([("request_id", ASCENDING)], unique=True)
    await database[VERIFIER_VERDICTS].create_index(
        [("request_id", ASCENDING), ("verifier_address", ASCENDING)],
        unique=True,
    )
    await database[QUORUM_CERTIFICATES].create_index([("request_id", ASCENDING)], unique=True)
    await database[MODEL_CATALOG].create_index([("model_id", ASCENDING)], unique=True)
    await database[DISPUTES].create_index([("request_id", ASCENDING)], unique=True)
    await database[OPERATORS].create_index([("operator_address", ASCENDING)], unique=True)
    await database[PERMITS].create_index([("task_id", ASCENDING)], unique=True)


async def ping_database(database: AsyncIOMotorDatabase) -> bool:
    try:
        await database.command("ping")
        return True
    except Exception as error:  # pragma: no cover - network environment dependent
        logger.warning("MongoDB ping failed: %s", error)
        return False


async def close_database() -> None:
    global _client
    if _client is not None:
        _client.close()
        _client = None


def get_in_memory_database() -> InMemoryDatabase:
    return InMemoryDatabase()
