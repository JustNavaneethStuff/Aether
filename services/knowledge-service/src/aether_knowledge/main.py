import structlog
from aether_common.config.settings import BaseServiceSettings
from aether_common.contracts.knowledge_acquisition import CrawlRequest
from aether_common.contracts.tools import KnowledgeDocument, KnowledgeQuery
from aether_common.domain.enums import HealthState
from aether_common.infrastructure.redis_clients import EventBus
from aether_common.integrations.factory import build_knowledge_acquisition
from aether_common.observability.telemetry import (
    CorrelationIdMiddleware,
    get_metrics,
    instrument_fastapi,
    setup_logging,
    setup_tracing,
)
from aether_knowledge.infrastructure.repository import KnowledgeRepository, create_session_factory, init_db
from fastapi import FastAPI
from fastapi.responses import Response
from pydantic_settings import SettingsConfigDict
import redis.asyncio as redis

logger = structlog.get_logger()


class KnowledgeSettings(BaseServiceSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    service_name: str = "knowledge-service"
    postgres_url: str = "postgresql+asyncpg://aether:aether@localhost:5432/aether"
    host: str = "0.0.0.0"
    port: int = 8004


settings = KnowledgeSettings()


def create_app() -> FastAPI:
    setup_logging(settings.service_name, settings.log_level, settings.log_format)
    setup_tracing(settings.service_name)

    app = FastAPI(title="Aether Knowledge Service", version="0.3.0")
    app.add_middleware(CorrelationIdMiddleware)

    session_factory = create_session_factory(settings.postgres_url)
    repo = KnowledgeRepository(session_factory)
    redis_client = redis.from_url(settings.redis_url, decode_responses=True)
    event_bus = EventBus(redis_client)

    async def search_fn(query: KnowledgeQuery):
        return await repo.search(query)

    knowledge = build_knowledge_acquisition(settings, search_fn=search_fn, event_bus=event_bus)

    @app.on_event("startup")
    async def startup() -> None:
        await init_db(settings.postgres_url)
        logger.info("knowledge_service_started", backend=settings.knowledge_backend)

    @app.get("/health")
    async def health() -> dict:
        return {"status": HealthState.HEALTHY.value, "service": settings.service_name}

    @app.get("/ready")
    async def ready() -> dict:
        return {"status": HealthState.HEALTHY.value, "service": settings.service_name}

    @app.get("/metrics")
    async def metrics() -> Response:
        return Response(content=get_metrics(), media_type="text/plain")

    @app.post("/v1/documents")
    async def ingest(document: KnowledgeDocument) -> dict:
        doc_id = await repo.ingest(document)
        await event_bus.publish("knowledge.updated", {"document_id": str(doc_id), "action": "ingested"})
        return {"id": str(doc_id), "status": "ingested"}

    @app.post("/v1/search")
    async def search(query: KnowledgeQuery) -> list[dict]:
        chunks = await knowledge.search(query)
        return [c.model_dump(mode="json") for c in chunks]

    @app.post("/v1/rag")
    async def rag(query: KnowledgeQuery) -> dict:
        chunks = await knowledge.search(query)
        context = "\n\n".join(f"[{c.score:.2f}] {c.content}" for c in chunks)
        return {"query": query.query, "context": context, "chunks": [c.model_dump(mode="json") for c in chunks]}

    @app.post("/v1/acquire")
    async def acquire(request: CrawlRequest) -> dict:
        handle = await knowledge.trigger_crawl(request)
        return handle.model_dump(mode="json")

    @app.get("/v1/datasets/{dataset_id}")
    async def get_dataset(dataset_id: str, q: str = "", top_k: int = 20) -> list[dict]:
        query = KnowledgeQuery(query=q, top_k=top_k) if q else None
        chunks = await knowledge.get_dataset(dataset_id, query)
        return [c.model_dump(mode="json") for c in chunks]

    instrument_fastapi(app)
    return app


app = create_app()


def main() -> None:
    import uvicorn

    uvicorn.run("aether_knowledge.main:app", host=settings.host, port=settings.port, reload=False)
