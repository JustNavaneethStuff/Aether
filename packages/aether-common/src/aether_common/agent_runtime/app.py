"""Shared agent service factory for Aether specialized agents."""

from collections.abc import Awaitable, Callable

import redis.asyncio as redis
import structlog
from aether_common.config.settings import BaseServiceSettings
from aether_common.domain.agent import (
    AgentRegistration,
    AgentResult,
    ExecuteAgentRequest,
    ExecuteAgentResponse,
    HealthStatus,
)
from aether_common.domain.enums import AgentCapability, HealthState
from aether_common.infrastructure.redis_clients import AgentRegistry
from aether_common.observability.telemetry import (
    CorrelationIdMiddleware,
    get_metrics,
    instrument_fastapi,
    setup_logging,
    setup_tracing,
)
from fastapi import FastAPI
from fastapi.responses import Response

logger = structlog.get_logger()

ExecuteFn = Callable[[ExecuteAgentRequest], Awaitable[AgentResult]]


def create_agent_app(
    settings: BaseServiceSettings,
    agent_name: str,
    capabilities: list[AgentCapability],
    execute_fn: ExecuteFn,
    service_url: str,
    port: int,
) -> FastAPI:
    setup_logging(settings.service_name, settings.log_level, settings.log_format)
    setup_tracing(settings.service_name)

    app = FastAPI(title=f"Aether Agent: {agent_name}", version="0.1.0")
    app.add_middleware(CorrelationIdMiddleware)
    redis_client = redis.from_url(settings.redis_url, decode_responses=True)
    registry = AgentRegistry(redis_client)

    @app.on_event("startup")
    async def startup() -> None:
        await registry.register(
            AgentRegistration(
                name=agent_name,
                url=service_url,
                capabilities=capabilities,
            )
        )
        logger.info("agent_registered", agent=agent_name, url=service_url)

    @app.on_event("shutdown")
    async def shutdown() -> None:
        await registry.deregister(agent_name)

    @app.get("/health")
    async def health() -> HealthStatus:
        return HealthStatus(state=HealthState.HEALTHY, service=agent_name)

    @app.get("/ready")
    async def ready() -> HealthStatus:
        return HealthStatus(state=HealthState.HEALTHY, service=agent_name)

    @app.get("/metrics")
    async def metrics() -> Response:
        return Response(content=get_metrics(), media_type="text/plain")

    @app.post("/v1/execute", response_model=ExecuteAgentResponse)
    async def execute(request: ExecuteAgentRequest) -> ExecuteAgentResponse:
        result = await execute_fn(request)
        return ExecuteAgentResponse(result=result)

    instrument_fastapi(app)
    return app


def run_agent(app_path: str, host: str, port: int) -> None:
    import uvicorn

    uvicorn.run(app_path, host=host, port=port, reload=False)
