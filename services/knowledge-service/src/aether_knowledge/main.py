
import structlog
from aether_common.config.settings import BaseServiceSettings
from aether_common.contracts.tools import KnowledgeDocument, KnowledgeQuery
from aether_common.domain.enums import HealthState
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

    app = FastAPI(title="Aether Knowledge Service", version="0.2.0")
    app.add_middleware(CorrelationIdMiddleware)

    session_factory = create_session_factory(settings.postgres_url)
    repo = KnowledgeRepository(session_factory)

    @app.on_event("startup")
    async def startup() -> None:
        await init_db(settings.postgres_url)
        logger.info("knowledge_service_started")

    @app.get("/health")
    async def health() -> dict:
        return {"status": HealthState.HEALTHY.value, "service": settings.service_name}

    @app.get("/metrics")
    async def metrics() -> Response:
        return Response(content=get_metrics(), media_type="text/plain")

    @app.post("/v1/documents")
    async def ingest(document: KnowledgeDocument) -> dict:
        doc_id = await repo.ingest(document)
        return {"id": str(doc_id), "status": "ingested"}

    @app.post("/v1/search")
    async def search(query: KnowledgeQuery) -> list[dict]:
        chunks = await repo.search(query)
        return [c.model_dump(mode="json") for c in chunks]

    @app.post("/v1/rag")
    async def rag(query: KnowledgeQuery) -> dict:
        chunks = await repo.search(query)
        context = "\n\n".join(f"[{c.score:.2f}] {c.content}" for c in chunks)
        return {"query": query.query, "context": context, "chunks": [c.model_dump(mode="json") for c in chunks]}

    instrument_fastapi(app)
    return app


app = create_app()


def main() -> None:
    import uvicorn

    uvicorn.run("aether_knowledge.main:app", host=settings.host, port=settings.port, reload=False)
