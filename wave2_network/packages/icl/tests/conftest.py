from __future__ import annotations

from collections.abc import AsyncIterator
import os

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from config import DEFAULT_DEMO_OPERATOR_KEYS, get_settings
from main import create_app
from middleware.rate_limit import _REQUEST_BUCKETS


@pytest_asyncio.fixture
async def client() -> AsyncIterator[tuple[AsyncClient, object]]:
    _REQUEST_BUCKETS.clear()
    os.environ["MOCK_CHAIN"] = "true"
    os.environ["DEMO_OPERATOR_PRIVATE_KEYS"] = DEFAULT_DEMO_OPERATOR_KEYS
    get_settings.cache_clear()
    app = create_app(get_settings())

    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as http_client:
            yield http_client, app

    _REQUEST_BUCKETS.clear()
    os.environ.pop("DEMO_OPERATOR_PRIVATE_KEYS", None)
    os.environ.pop("MOCK_CHAIN", None)
