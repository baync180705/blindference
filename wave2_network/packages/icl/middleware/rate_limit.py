from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request

_REQUEST_BUCKETS: dict[str, deque[float]] = defaultdict(deque)
WINDOW_SECONDS = 60
MAX_REQUESTS_PER_WINDOW = 120
LOOPBACK_HOSTS = {"127.0.0.1", "::1", "localhost"}


async def rate_limit_guard(request: Request) -> bool:
    client_host = request.client.host if request.client else "local"
    if client_host in LOOPBACK_HOSTS:
        return True

    key = f"{client_host}:{request.url.path}"
    bucket = _REQUEST_BUCKETS[key]
    now = time.time()

    while bucket and now - bucket[0] > WINDOW_SECONDS:
        bucket.popleft()

    if len(bucket) >= MAX_REQUESTS_PER_WINDOW:
        raise HTTPException(status_code=429, detail="rate limit exceeded")

    bucket.append(now)
    return True
