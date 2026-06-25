from uuid import UUID

import redis.asyncio as redis
import structlog
from aether_common.domain.api_models import CreateConversationRequest, CreateConversationResponse
from aether_common.domain.conversation import SharedContext
from aether_common.domain.enums import HealthState, MessageRole
from aether_common.domain.task_graph import TaskGraph
from aether_common.infrastructure.cache import ContextCache
from aether_common.observability.telemetry import (
    CorrelationIdMiddleware,
    get_metrics,
    instrument_fastapi,
    setup_logging,
    setup_tracing,
)
from aether_memory.config import MemorySettings
from aether_memory.infrastructure.database.repositories import (
    ContextRepository,
    ConversationRepository,
    MessageRepository,
    create_session_factory,
    init_db,
)
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response

logger = structlog.get_logger()
settings = MemorySettings()


def create_app() -> FastAPI:
    setup_logging(settings.service_name, settings.log_level, settings.log_format)
    setup_tracing(settings.service_name)

    app = FastAPI(title="Aether Memory Service", version="0.2.0")
    app.add_middleware(CorrelationIdMiddleware)

    session_factory = create_session_factory(settings.postgres_url)
    conversation_repo = ConversationRepository(session_factory)
    message_repo = MessageRepository(session_factory)
    context_repo = ContextRepository(session_factory, message_repo)
    redis_client = redis.from_url(settings.redis_url, decode_responses=True)
    context_cache = ContextCache(redis_client)

    @app.on_event("startup")
    async def startup() -> None:
        await init_db(settings.postgres_url)
        logger.info("memory_service_started")

    @app.get("/health")
    async def health() -> dict:
        return {"status": HealthState.HEALTHY.value, "service": settings.service_name}

    @app.get("/ready")
    async def ready() -> dict:
        try:
            await redis_client.ping()
            return {"status": HealthState.HEALTHY.value, "service": settings.service_name}
        except Exception as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    @app.get("/metrics")
    async def metrics() -> Response:
        return Response(content=get_metrics(), media_type="text/plain")

    @app.post("/v1/conversations", response_model=CreateConversationResponse)
    async def create_conversation(request: CreateConversationRequest) -> CreateConversationResponse:
        conversation = await conversation_repo.create(request.metadata)
        return CreateConversationResponse(id=conversation.id, metadata=conversation.metadata)

    @app.get("/v1/conversations/{conversation_id}")
    async def get_conversation(conversation_id: UUID) -> dict:
        conversation = await conversation_repo.get(conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return conversation.model_dump(mode="json")

    @app.get("/v1/conversations/{conversation_id}/messages")
    async def list_messages(conversation_id: UUID) -> list[dict]:
        cached = await context_cache.get_messages(str(conversation_id))
        if cached is not None:
            return cached
        messages = await message_repo.list_by_conversation(conversation_id)
        serialized = [m.model_dump(mode="json") for m in messages]
        await context_cache.set_messages(str(conversation_id), serialized)
        return serialized

    @app.post("/v1/conversations/{conversation_id}/messages")
    async def add_message(conversation_id: UUID, body: dict) -> dict:
        conversation = await conversation_repo.get(conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        message = await message_repo.add(
            conversation_id,
            MessageRole(body["role"]),
            body["content"],
            body.get("metadata"),
        )
        await context_cache.delete(str(conversation_id))
        return message.model_dump(mode="json")

    @app.get("/v1/conversations/{conversation_id}/context", response_model=SharedContext)
    async def get_context(conversation_id: UUID) -> SharedContext:
        cached = await context_cache.get(str(conversation_id))
        if cached:
            return SharedContext.model_validate(cached)
        context = await context_repo.get_context(conversation_id)
        await context_cache.set(str(conversation_id), context.model_dump(mode="json"))
        return context

    @app.put("/v1/conversations/{conversation_id}/context")
    async def update_context(conversation_id: UUID, context: SharedContext) -> dict:
        await context_cache.set(str(conversation_id), context.model_dump(mode="json"))
        return {"status": "updated"}

    @app.post("/v1/conversations/{conversation_id}/task-graphs")
    async def save_task_graph(conversation_id: UUID, task_graph: TaskGraph) -> dict:
        await context_repo.save_task_graph(task_graph)
        return {"status": "saved", "id": str(task_graph.id)}

    @app.get("/v1/conversations/{conversation_id}/task-graphs/latest")
    async def get_latest_task_graph(conversation_id: UUID) -> TaskGraph:
        graph = await context_repo.get_latest_task_graph(conversation_id)
        if not graph:
            raise HTTPException(status_code=404, detail="No task graph found")
        return graph

    @app.post("/v1/conversations/{conversation_id}/executions")
    async def record_execution(conversation_id: UUID, body: dict) -> dict:
        await context_repo.record_execution(
            conversation_id,
            body["agent_name"],
            body.get("latency_ms", 0),
            body.get("usage", {}),
        )
        return {"status": "recorded"}

    instrument_fastapi(app)
    return app


app = create_app()


def main() -> None:
    import uvicorn

    uvicorn.run("aether_memory.main:app", host=settings.host, port=settings.port, reload=False)
