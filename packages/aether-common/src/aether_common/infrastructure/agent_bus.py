import json
from typing import Any

import redis.asyncio as redis
from aether_common.domain.workflow import AgentMessage


class AgentCommunicationBus:
    """Redis pub/sub for inter-agent messaging within a conversation."""

    def __init__(self, redis_client: redis.Redis) -> None:
        self._redis = redis_client

    def _channel(self, conversation_id: str) -> str:
        return f"aether:agent-bus:{conversation_id}"

    async def publish(self, message: AgentMessage) -> None:
        await self._redis.publish(self._channel(str(message.conversation_id)), message.model_dump_json())

    async def subscribe(self, conversation_id: str):
        pubsub = self._redis.pubsub()
        await pubsub.subscribe(self._channel(conversation_id))
        return pubsub


class CheckpointStore:
    CHECKPOINT_PREFIX = "aether:checkpoint:"

    def __init__(self, redis_client: redis.Redis) -> None:
        self._redis = redis_client

    def _key(self, conversation_id: str) -> str:
        return f"{self.CHECKPOINT_PREFIX}{conversation_id}"

    async def save(self, conversation_id: str, checkpoint: dict[str, Any]) -> None:
        await self._redis.setex(self._key(conversation_id), 86400, json.dumps(checkpoint, default=str))

    async def get(self, conversation_id: str) -> dict[str, Any] | None:
        data = await self._redis.get(self._key(conversation_id))
        if not data:
            return None
        return json.loads(data)

    async def delete(self, conversation_id: str) -> None:
        await self._redis.delete(self._key(conversation_id))
