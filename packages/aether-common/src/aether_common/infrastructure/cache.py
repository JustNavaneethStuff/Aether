import json
from typing import Any

import redis.asyncio as redis

CONTEXT_TTL_SECONDS = 3600
MESSAGES_TTL_SECONDS = 300


class ContextCache:
    def __init__(self, redis_client: redis.Redis) -> None:
        self._redis = redis_client

    def _key(self, conversation_id: str) -> str:
        return f"aether:context:{conversation_id}"

    def _messages_key(self, conversation_id: str) -> str:
        return f"aether:messages:{conversation_id}"

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
        await self._redis.delete(self._messages_key(conversation_id))

    async def get_messages(self, conversation_id: str) -> list[dict[str, Any]] | None:
        data = await self._redis.get(self._messages_key(conversation_id))
        if not data:
            return None
        return json.loads(data)

    async def set_messages(self, conversation_id: str, messages: list[dict[str, Any]]) -> None:
        await self._redis.setex(
            self._messages_key(conversation_id),
            MESSAGES_TTL_SECONDS,
            json.dumps(messages, default=str),
        )
