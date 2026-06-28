from uuid import UUID

import redis.asyncio as redis
import structlog
from aether_common.config.settings import BaseServiceSettings
from aether_common.domain.api_models import (
    AsyncOrchestrationRequest,
    AsyncOrchestrationResponse,
    JobCallbackRequest,
    OrchestrationRequest,
    OrchestrationResult,
)
from aether_common.domain.enums import HealthState
from aether_common.infrastructure.agent_bus import AgentCommunicationBus, CheckpointStore
from aether_common.infrastructure.redis_clients import AgentRegistry, EventBus
from aether_common.integrations.factory import build_task_queue
from aether_common.integrations.task_queue.local import LocalTaskQueue
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
    approvals_enabled: bool = False
    atlas_callback_url: str = "http://localhost:8001/v1/internal/workflows/execute"


class ResumeRequest(BaseModel):
    conversation_id: UUID


class ApprovalActionRequest(BaseModel):
    decided_by: str = "system"
    comment: str = ""


class WorkflowExecuteRequest(BaseModel):
    conversation_id: UUID
    message: str


settings = OrchestratorSettings()


def create_app() -> FastAPI:
    setup_logging(settings.service_name, settings.log_level, settings.log_format)
    setup_tracing(settings.service_name)

    app = FastAPI(title="Aether Orchestrator", version="0.3.0")
    app.add_middleware(CorrelationIdMiddleware)

    redis_client = redis.from_url(settings.redis_url, decode_responses=True)
    registry = AgentRegistry(redis_client)
    event_bus = EventBus(redis_client)
    checkpoint_store = CheckpointStore(redis_client)
    agent_bus = AgentCommunicationBus(redis_client)
    memory_client = MemoryClient(settings.memory_service_url)
    agent_client = AgentClient(registry)
    task_queue = build_task_queue(settings)
    orchestration = OrchestrationService(
        memory_client,
        agent_client,
        event_bus,
        checkpoint_store,
        agent_bus,
        task_queue,
        approvals_enabled=settings.approvals_enabled,
    )
    if isinstance(task_queue, LocalTaskQueue):
        task_queue.set_executor(orchestration.build_job_result)

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
        task_graph, results, final_response, paused, approval_id = await orchestration.run(
            request.conversation_id, request.message
        )
        return OrchestrationResult(
            conversation_id=request.conversation_id,
            task_graph=task_graph,
            agent_results=results,
            final_response=final_response,
            paused=paused,
            approval_id=approval_id,
        )

    @app.post("/v1/orchestrate/async", response_model=AsyncOrchestrationResponse)
    async def orchestrate_async(request: AsyncOrchestrationRequest) -> AsyncOrchestrationResponse:
        callback = settings.atlas_callback_url if settings.task_queue_backend == "atlas" else None
        job_id, state, result = await orchestration.submit_async(
            request.conversation_id, request.message, callback_url=callback
        )
        return AsyncOrchestrationResponse(
            conversation_id=request.conversation_id,
            job_id=job_id,
            state=state,
            result=result,
        )

    @app.post("/v1/internal/workflows/execute", response_model=OrchestrationResult)
    async def execute_workflow_internal(request: WorkflowExecuteRequest) -> OrchestrationResult:
        return await orchestration.execute_workflow_payload(request.conversation_id, request.message)

    @app.post("/v1/internal/jobs/{job_id}/callback")
    async def job_completion_callback(job_id: str, body: JobCallbackRequest) -> dict:
        await orchestration.handle_job_callback(job_id, body.success, body.output, body.error)
        return {"job_id": job_id, "accepted": True}

    @app.post("/v1/orchestrate/resume", response_model=OrchestrationResult)
    async def resume_workflow(request: ResumeRequest) -> OrchestrationResult:
        try:
            task_graph, results, final_response, paused, approval_id = await orchestration.resume(
                request.conversation_id
            )
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return OrchestrationResult(
            conversation_id=request.conversation_id,
            task_graph=task_graph,
            agent_results=results,
            final_response=final_response,
            paused=paused,
            approval_id=approval_id,
        )

    @app.get("/v1/approvals/pending")
    async def list_pending_approvals() -> list[dict]:
        approvals = await memory_client.list_pending_approvals()
        return [a.model_dump(mode="json") for a in approvals]

    @app.post("/v1/approvals/{approval_id}/approve")
    async def approve_workflow(approval_id: UUID, body: ApprovalActionRequest) -> dict:
        approval = await orchestration.approve(approval_id, body.decided_by)
        return approval.model_dump(mode="json")

    @app.post("/v1/approvals/{approval_id}/reject")
    async def reject_workflow(approval_id: UUID, body: ApprovalActionRequest) -> dict:
        approval = await orchestration.reject(approval_id, body.decided_by, body.comment)
        return approval.model_dump(mode="json")

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

    uvicorn.run("aether_orchestrator.main:app", host=settings.host, port=settings.port, reload=False)
