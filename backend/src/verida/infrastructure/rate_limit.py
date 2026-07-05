"""Redis-backed sliding-window rate limiter for VERIDA.

Design:
- Sliding window algorithm using sorted sets in Redis
- Generic error messages — never reveals whether an email exists
- Decoratable: use ``@rate_limit(...)`` on FastAPI route handlers
- Falls back gracefully when Redis is unavailable (logs warning, allows request)

Usage::

    from verida.infrastructure.rate_limit import rate_limit

    @router.post("/login")
    @rate_limit(requests=10, window_seconds=60, key_prefix="auth:login")
    async def login(request: Request, ...):
        ...

The key is ``{key_prefix}:{client_ip_truncated}`` where the IP is truncated
to the /24 prefix to avoid identifying individual users behind NAT.

Rate limit errors return HTTP 429 with a generic message and Retry-After header.
"""

from __future__ import annotations

import asyncio
import functools
import hashlib
import time
from typing import Any, Callable

import structlog
from fastapi import HTTPException, Request, status

logger = structlog.get_logger(__name__)


def _truncate_ip(ip: str) -> str:
    """Truncate IPv4 to /24, IPv6 to /48 prefix for rate-limit key.

    This prevents accurate per-user identification while still allowing
    per-network rate limiting.
    """
    if not ip:
        return "unknown"
    try:
        if ":" in ip:
            # IPv6: keep first 3 groups (48-bit prefix)
            parts = ip.split(":")
            return ":".join(parts[:3]) + "::/48"
        else:
            # IPv4: keep first 3 octets (/24 prefix)
            parts = ip.split(".")
            return ".".join(parts[:3]) + ".0/24"
    except Exception:
        return "unknown"


def _get_client_ip(request: Request) -> str:
    """Extract client IP, respecting X-Forwarded-For (single trusted proxy)."""
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Take the first IP (leftmost = real client behind single proxy)
        return forwarded_for.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


async def _sliding_window_check(
    redis: Any,
    key: str,
    requests: int,
    window_seconds: int,
) -> tuple[bool, int]:
    """Sliding window rate limit check using a Redis sorted set.

    Returns (allowed, retry_after_seconds).
    ``retry_after_seconds`` is 0 if allowed.
    """
    now_ms = int(time.time() * 1000)
    window_ms = window_seconds * 1000
    cutoff_ms = now_ms - window_ms

    pipe = redis.pipeline()
    # Remove expired entries
    pipe.zremrangebyscore(key, 0, cutoff_ms)
    # Count current window
    pipe.zcard(key)
    # Add current request
    pipe.zadd(key, {str(now_ms): now_ms})
    # Set TTL
    pipe.expire(key, window_seconds + 1)
    results = await pipe.execute()

    current_count = results[1]  # count BEFORE adding this request

    if current_count >= requests:
        # Rate limited — compute retry after
        oldest_ms_result = await redis.zrange(key, 0, 0, withscores=True)
        if oldest_ms_result:
            oldest_ms = oldest_ms_result[0][1]
            retry_after = max(1, int((oldest_ms + window_ms - now_ms) / 1000))
        else:
            retry_after = window_seconds
        return False, retry_after

    return True, 0


def rate_limit(
    requests: int = 60,
    window_seconds: int = 60,
    key_prefix: str = "rl",
) -> Callable:
    """Decorator that applies sliding-window rate limiting to a FastAPI endpoint.

    Parameters
    ----------
    requests:
        Maximum number of requests allowed in the window.
    window_seconds:
        Length of the sliding window in seconds.
    key_prefix:
        Prefix for the Redis key. Should be unique per endpoint.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Find Request in args/kwargs
            request: Request | None = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            if request is None:
                request = kwargs.get("request")

            if request is not None:
                try:
                    from verida.config import get_settings
                    import redis.asyncio as aioredis

                    settings = get_settings()
                    redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)

                    client_ip = _get_client_ip(request)
                    truncated_ip = _truncate_ip(client_ip)
                    key = f"{key_prefix}:{truncated_ip}"

                    allowed, retry_after = await _sliding_window_check(
                        redis_client, key, requests, window_seconds
                    )

                    await redis_client.aclose()

                    if not allowed:
                        logger.warning(
                            "rate_limit_exceeded",
                            key_prefix=key_prefix,
                            ip_prefix=truncated_ip,
                        )
                        raise HTTPException(
                            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                            detail="Too many requests. Please try again later.",
                            headers={"Retry-After": str(retry_after)},
                        )
                except HTTPException:
                    raise
                except Exception as exc:
                    # Redis unavailable — log and allow (fail-open for availability)
                    logger.warning(
                        "rate_limit_redis_unavailable",
                        error=str(exc),
                        key_prefix=key_prefix,
                    )

            return await func(*args, **kwargs)

        return wrapper
    return decorator


class SlidingWindowRateLimiter:
    """Standalone sliding-window rate limiter for use in middleware or services.

    Can be used without the decorator when more fine-grained control is needed.
    """

    def __init__(
        self,
        redis_url: str,
        requests: int = 60,
        window_seconds: int = 60,
    ) -> None:
        self._redis_url = redis_url
        self._requests = requests
        self._window_seconds = window_seconds
        self._redis: Any = None

    async def _get_redis(self) -> Any:
        if self._redis is None:
            import redis.asyncio as aioredis
            self._redis = aioredis.from_url(self._redis_url, decode_responses=True)
        return self._redis

    async def is_allowed(self, identifier: str, key_prefix: str = "rl") -> tuple[bool, int]:
        """Check if the identifier is within rate limits.

        Returns (allowed, retry_after_seconds).
        """
        try:
            redis = await self._get_redis()
            key = f"{key_prefix}:{identifier}"
            return await _sliding_window_check(
                redis, key, self._requests, self._window_seconds
            )
        except Exception as exc:
            logger.warning("rate_limiter_error", error=str(exc))
            return True, 0  # Fail open

    async def close(self) -> None:
        if self._redis:
            await self._redis.aclose()
