import json

import redis.asyncio as redis
from aether_common.domain.agent import AgentRegistration


class AgentRegistry:
    REGISTRY_KEY = "aether:agents"

    def __init__(self, redis_client: redis.Redis) -> None:
        self._redis = redis_client

    async def register(self, registration: AgentRegistration) -> None:
        await self._redis.hset(
            self.REGISTRY_KEY,
            registration.name,
            registration.model_dump_json(),
        )

    async def deregister(self, name: str) -> None:
        await self._redis.hdel(self.REGISTRY_KEY, name)

    async def get(self, name: str) -> AgentRegistration | None:
        data = await self._redis.hget(self.REGISTRY_KEY, name)
        if not data:
            return None
        return AgentRegistration.model_validate_json(data)

    async def list_all(self) -> list[AgentRegistration]:
        raw = await self._redis.hgetall(self.REGISTRY_KEY)
        return [AgentRegistration.model_validate_json(v) for v in raw.values()]


class EventBus:
    STREAM_KEY = "aether:events"

    def __init__(self, redis_client: redis.Redis) -> None:
        self._redis = redis_client

    async def publish(self, event_type: str, payload: dict) -> str:
        return await self._redis.xadd(
            self.STREAM_KEY,
            {"event_type": event_type, "payload": json.dumps(payload)},
        )

    async def read_latest(self, count: int = 10, last_id: str = "0") -> list[dict]:
        entries = await self._redis.xread({self.STREAM_KEY: last_id}, count=count, block=1000)
        results: list[dict] = []
        for _stream, messages in entries:
            for msg_id, data in messages:
                results.append(
                    {
                        "id": msg_id,
                        "event_type": data.get("event_type", ""),
                        "payload": json.loads(data.get("payload", "{}")),
                    }
                )
        return results
