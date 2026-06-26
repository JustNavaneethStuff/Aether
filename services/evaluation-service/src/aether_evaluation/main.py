import asyncio
from datetime import UTC, datetime
from uuid import UUID

import httpx
import redis.asyncio as redis
import structlog
from aether_common.config.settings import BaseServiceSettings
from aether_common.domain.enums import HealthState
from aether_common.domain.evaluation import EvaluationStatus
from aether_common.evaluation.scorer import score_workflow
from aether_common.infrastructure.redis_clients import EventBus
from aether_common.observability.telemetry import (
    CorrelationIdMiddleware,
    get_metrics,
    instrument_fastapi,
    setup_logging,
    setup_tracing,
)
from aether_evaluation.infrastructure.repository import (
    EvaluationRepository,
    create_session_factory,
    init_db,
)
from fastapi import FastAPI
from fastapi.responses import Response
from pydantic import BaseModel
from pydantic_settings import SettingsConfigDict

logger = structlog.get_logger()


class EvaluationSettings(BaseServiceSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    service_name: str = "evaluation-service"
    postgres_url: str = "postgresql+asyncpg://aether:aether@localhost:5432/aether"
    memory_service_url: str = "http://localhost:8002"
    orchestrator_url: str = "http://localhost:8001"
    host: str = "0.0.0.0"
    port: int = 8005
    event_consumer_enabled: bool = True


class RunEvaluationRequest(BaseModel):
    conversation_id: UUID
    workflow_data: dict | None = None


settings = EvaluationSettings()


def create_app() -> FastAPI:
    setup_logging(settings.service_name, settings.log_level, settings.log_format)
    setup_tracing(settings.service_name)

    app = FastAPI(title="Aether Evaluation Service", version="0.3.0")
    app.add_middleware(CorrelationIdMiddleware)

    session_factory = create_session_factory(settings.postgres_url)
    repo = EvaluationRepository(session_factory)
    redis_client = redis.from_url(settings.redis_url, decode_responses=True)
    event_bus = EventBus(redis_client)

    async def consume_events() -> None:
        last_id = "0"
        while True:
            try:
                events = await event_bus.read_latest(count=10, last_id=last_id)
                for event in events:
                    last_id = event["id"]
                    if event["event_type"] == "workflow.completed":
                        cid = event["payload"].get("conversation_id")
                        if cid:
                            await _run_evaluation(UUID(cid), None, repo)
            except Exception as exc:
                logger.error("event_consumer_error", error=str(exc))
            await asyncio.sleep(2)

    @app.on_event("startup")
    async def startup() -> None:
        await init_db(settings.postgres_url)
        if settings.event_consumer_enabled:
            asyncio.create_task(consume_events())
        logger.info("evaluation_service_started")

    async def _run_evaluation(
        conversation_id: UUID,
        workflow_data: dict | None,
        repository: EvaluationRepository,
    ):
        if not workflow_data:
            async with httpx.AsyncClient() as client:
                try:
                    resp = await client.get(
                        f"{settings.memory_service_url}/v1/conversations/{conversation_id}/messages"
                    )
                    messages = resp.json() if resp.status_code == 200 else []
                    workflow_data = {
                        "agent_results": [],
                        "final_response": messages[-1]["content"] if messages else "",
                    }
                except Exception:
                    workflow_data = {"agent_results": [], "final_response": ""}

        run = score_workflow(str(conversation_id), workflow_data)
        run.status = EvaluationStatus.COMPLETED
        run.completed_at = datetime.now(UTC)
        saved = await repository.save(run)

        try:
            from aether_common.observability.telemetry import EVALUATION_SCORE

            EVALUATION_SCORE.labels(passed=str(saved.passed)).observe(saved.overall_score)
        except Exception:
            pass

        return saved

    @app.get("/health")
    async def health() -> dict:
        return {"status": HealthState.HEALTHY.value, "service": settings.service_name}

    @app.get("/metrics")
    async def metrics() -> Response:
        return Response(content=get_metrics(), media_type="text/plain")

    @app.post("/v1/evaluations/run")
    async def run_evaluation(request: RunEvaluationRequest) -> dict:
        run = await _run_evaluation(request.conversation_id, request.workflow_data, repo)
        return run.model_dump(mode="json")

    @app.get("/v1/evaluations/{conversation_id}")
    async def get_evaluations(conversation_id: UUID) -> list[dict]:
        runs = await repo.get_by_conversation(conversation_id)
        return [r.model_dump(mode="json") for r in runs]

    @app.get("/v1/evaluations/summary")
    async def get_summary() -> dict:
        return await repo.get_summary()

    instrument_fastapi(app)
    return app


app = create_app()


def main() -> None:
    import uvicorn

    uvicorn.run("aether_evaluation.main:app", host=settings.host, port=settings.port, reload=False)
