from uuid import UUID

import httpx
import redis.asyncio as redis
from aether_common.config.settings import BaseServiceSettings
from aether_common.domain.api_models import (
    CreateConversationRequest,
    CreateConversationResponse,
    OrchestrationRequest,
    SendMessageRequest,
)
from aether_common.domain.enums import HealthState
from aether_common.infrastructure.redis_clients import AgentRegistry
from aether_common.observability.telemetry import (
    CorrelationIdMiddleware,
    get_metrics,
    instrument_fastapi,
    setup_logging,
    setup_tracing,
)
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response, StreamingResponse
from pydantic_settings import SettingsConfigDict


class GatewaySettings(BaseServiceSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    service_name: str = "api-gateway"
    orchestrator_url: str = "http://localhost:8001"
    memory_service_url: str = "http://localhost:8002"
    response_builder_url: str = "http://localhost:8003"
    host: str = "0.0.0.0"
    port: int = 8000


settings = GatewaySettings()


def create_app() -> FastAPI:
    setup_logging(settings.service_name, settings.log_level, settings.log_format)
    setup_tracing(settings.service_name)

    app = FastAPI(title="Aether API Gateway", version="0.1.0")
    app.add_middleware(CorrelationIdMiddleware)
    redis_client = redis.from_url(settings.redis_url, decode_responses=True)
    registry = AgentRegistry(redis_client)

    @app.get("/health")
    async def health() -> dict:
        services = {
            "orchestrator": settings.orchestrator_url,
            "memory": settings.memory_service_url,
            "response_builder": settings.response_builder_url,
        }
        status = HealthState.HEALTHY.value
        details: dict[str, str] = {}
        async with httpx.AsyncClient(timeout=5.0) as client:
            for name, url in services.items():
                try:
                    resp = await client.get(f"{url}/health")
                    details[name] = resp.json().get("status", "unknown")
                except Exception as exc:
                    details[name] = f"unhealthy: {exc}"
                    status = HealthState.DEGRADED.value
        return {"status": status, "service": settings.service_name, "dependencies": details}

    @app.get("/metrics")
    async def metrics() -> Response:
        return Response(content=get_metrics(), media_type="text/plain")

    @app.post("/v1/conversations", response_model=CreateConversationResponse)
    async def create_conversation(request: CreateConversationRequest) -> CreateConversationResponse:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.memory_service_url}/v1/conversations",
                json=request.model_dump(mode="json"),
            )
            response.raise_for_status()
            return CreateConversationResponse.model_validate(response.json())

    @app.get("/v1/conversations/{conversation_id}")
    async def get_conversation(conversation_id: UUID) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.memory_service_url}/v1/conversations/{conversation_id}"
            )
            if response.status_code == 404:
                raise HTTPException(status_code=404, detail="Conversation not found")
            response.raise_for_status()
            return response.json()

    @app.get("/v1/conversations/{conversation_id}/messages")
    async def list_messages(conversation_id: UUID) -> list[dict]:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.memory_service_url}/v1/conversations/{conversation_id}/messages"
            )
            response.raise_for_status()
            return response.json()

    @app.post("/v1/conversations/{conversation_id}/messages")
    async def send_message(conversation_id: UUID, request: SendMessageRequest) -> StreamingResponse:
        async with httpx.AsyncClient(timeout=300.0) as client:
            orch_response = await client.post(
                f"{settings.orchestrator_url}/v1/orchestrate",
                json=OrchestrationRequest(
                    conversation_id=conversation_id,
                    message=request.content,
                    metadata=request.metadata,
                ).model_dump(mode="json"),
            )
            orch_response.raise_for_status()
            result = orch_response.json()

            stream_response = await client.post(
                f"{settings.response_builder_url}/v1/stream",
                json=result,
            )
            stream_response.raise_for_status()

            async def proxy_stream():
                async for chunk in stream_response.aiter_bytes():
                    yield chunk

            return StreamingResponse(proxy_stream(), media_type="text/event-stream")

    @app.get("/v1/agents")
    async def list_agents() -> list[dict]:
        agents = await registry.list_all()
        return [a.model_dump(mode="json") for a in agents]

    instrument_fastapi(app)
    return app


app = create_app()


def main() -> None:
    import uvicorn

    uvicorn.run("aether_gateway.main:app", host=settings.host, port=settings.port, reload=False)
