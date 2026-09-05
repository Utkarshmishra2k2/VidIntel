"""
A small in-process, per-client sliding-window rate limiter.

The original project required Redis + fastapi-limiter just to rate limit a
single-user, self-hosted tool — an external service dependency that added
failure modes without much benefit at this scale. This limiter needs no
external services, which is a better fit for "practical and reliable" here.
If this API is ever deployed multi-instance behind a load balancer, swap
this out for a shared store (Redis) — the interface below is the seam.
"""
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request

from config import config

_hits: dict[str, deque] = defaultdict(deque)


def _client_key(request: Request) -> str:
    if request.client:
        return request.client.host
    return "unknown"


async def rate_limit(request: Request) -> None:
    key = _client_key(request)
    now = time.monotonic()
    window = config.RATE_LIMIT_WINDOW_SECONDS
    limit = config.RATE_LIMIT_REQUESTS

    q = _hits[key]
    while q and now - q[0] > window:
        q.popleft()

    if len(q) >= limit:
        raise HTTPException(
            status_code=429,
            detail=f"Too many requests. Please wait a moment and try again (limit: {limit} per {window}s).",
        )

    q.append(now)
