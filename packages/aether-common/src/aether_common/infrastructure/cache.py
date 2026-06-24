import json
from typing import Any

import redis.asyncio as redis

CONTEXT_TTL_SECONDS = 3600


class ContextCache:
    def __init__(self, redis_client: redis.Redis) -> None:
        self._redis = redis_client

    def _key(self, conversation_id: str) -> str:
        return f"aether:context:{conversation_id}"

    async def get(self, conversation_id: str) -> dict[str, Any] | None:
        data = await self._redis.get(self._key(conversation_id))
        if not data:
            return None
        return json.loads(data)

    async def set(self, conversation_id: str, context: dict[str, Any]) -> None:
        await self._redis.setex(
            self._key(conversation_id),
            CONTEXT_TTL_SECONDS,
            json.dumps(context, default=str),
        )

    async def delete(self, conversation_id: str) -> None:
        await self._redis.delete(self._key(conversation_id))
