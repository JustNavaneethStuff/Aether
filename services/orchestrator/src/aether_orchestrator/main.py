from uuid import UUID

import redis.asyncio as redis
import structlog
from aether_common.config.settings import BaseServiceSettings
from aether_common.domain.api_models import OrchestrationRequest, OrchestrationResult
from aether_common.domain.enums import HealthState
from aether_common.infrastructure.agent_bus import AgentCommunicationBus, CheckpointStore
from aether_common.infrastructure.redis_clients import AgentRegistry, EventBus
from aether_common.observability.telemetry import (
    CorrelationIdMiddleware,
    get_metrics,
    instrument_fastapi,
    setup_logging,
    setup_tracing,
)
from aether_orchestrator.application.orchestration import (
    AgentClient,
    MemoryClient,
    OrchestrationService,
)
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from pydantic_settings import SettingsConfigDict

logger = structlog.get_logger()


class OrchestratorSettings(BaseServiceSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    service_name: str = "orchestrator"
    memory_service_url: str = "http://localhost:8002"
    host: str = "0.0.0.0"
    port: int = 8001


class ResumeRequest(BaseModel):
    conversation_id: UUID


settings = OrchestratorSettings()


def create_app() -> FastAPI:
    setup_logging(settings.service_name, settings.log_level, settings.log_format)
    setup_tracing(settings.service_name)

    app = FastAPI(title="Aether Orchestrator", version="0.2.0")
    app.add_middleware(CorrelationIdMiddleware)

    redis_client = redis.from_url(settings.redis_url, decode_responses=True)
    registry = AgentRegistry(redis_client)
    event_bus = EventBus(redis_client)
    checkpoint_store = CheckpointStore(redis_client)
    agent_bus = AgentCommunicationBus(redis_client)
    memory_client = MemoryClient(settings.memory_service_url)
    agent_client = AgentClient(registry)
    orchestration = OrchestrationService(
        memory_client, agent_client, event_bus, checkpoint_store, agent_bus
    )

    @app.get("/health")
    async def health() -> dict:
        return {"status": HealthState.HEALTHY.value, "service": settings.service_name}

    @app.get("/ready")
    async def ready() -> dict:
        try:
            await redis_client.ping()
            return {"status": HealthState.HEALTHY.value}
        except Exception as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    @app.get("/metrics")
    async def metrics() -> Response:
        return Response(content=get_metrics(), media_type="text/plain")

    @app.get("/v1/agents")
    async def list_agents() -> list[dict]:
        agents = await registry.list_all()
        return [a.model_dump(mode="json") for a in agents]

    @app.get("/v1/tools")
    async def list_tools() -> list[dict]:
        from aether_common.plugins.registry import BuiltinTools

        return [t.model_dump() for t in BuiltinTools.get_definitions()]

    @app.post("/v1/orchestrate", response_model=OrchestrationResult)
    async def orchestrate(request: OrchestrationRequest) -> OrchestrationResult:
        task_graph, results, final_response = await orchestration.run(
            request.conversation_id, request.message
        )
        return OrchestrationResult(
            conversation_id=request.conversation_id,
            task_graph=task_graph,
            agent_results=results,
            final_response=final_response,
        )

    @app.post("/v1/orchestrate/resume", response_model=OrchestrationResult)
    async def resume_workflow(request: ResumeRequest) -> OrchestrationResult:
        try:
            task_graph, results, final_response = await orchestration.resume(request.conversation_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return OrchestrationResult(
            conversation_id=request.conversation_id,
            task_graph=task_graph,
            agent_results=results,
            final_response=final_response,
        )

    @app.get("/v1/workflows/{conversation_id}/checkpoint")
    async def get_checkpoint(conversation_id: UUID) -> dict:
        checkpoint = await checkpoint_store.get(str(conversation_id))
        if not checkpoint:
            raise HTTPException(status_code=404, detail="No checkpoint found")
        return checkpoint

    instrument_fastapi(app)
    return app


app = create_app()


def main() -> None:
    import uvicorn

    uvicorn.run(
        "aether_orchestrator.main:app", host=settings.host, port=settings.port, reload=False
    )
