import time

import redis.asyncio as redis


class RateLimiter:
    """Fixed-window rate limiter using Redis."""

    def __init__(self, redis_client: redis.Redis, limit: int = 60, window_seconds: int = 60) -> None:
        self._redis = redis_client
        self._limit = limit
        self._window = window_seconds

    def _key(self, client_id: str) -> str:
        window_id = int(time.time()) // self._window
        return f"aether:ratelimit:{client_id}:{window_id}"

    async def is_allowed(self, client_id: str) -> tuple[bool, int]:
        key = self._key(client_id)
        count = await self._redis.incr(key)
        if count == 1:
            await self._redis.expire(key, self._window)
        remaining = max(0, self._limit - count)
        return count <= self._limit, remaining
