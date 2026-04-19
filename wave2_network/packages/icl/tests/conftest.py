from __future__ import annotations

from collections.abc import AsyncIterator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from config import get_settings
from main import create_app
from middleware.rate_limit import _REQUEST_BUCKETS


@pytest_asyncio.fixture
async def client() -> AsyncIterator[tuple[AsyncClient, object]]:
    _REQUEST_BUCKETS.clear()
    get_settings.cache_clear()
    app = create_app(get_settings())

    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as http_client:
            yield http_client, app

    _REQUEST_BUCKETS.clear()
