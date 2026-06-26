from uuid import UUID

import structlog
from aether_common.config.settings import BaseServiceSettings
from aether_common.domain.enums import HealthState
from aether_common.domain.prompt import PromptRenderRequest, PromptTemplate
from aether_common.observability.telemetry import (
    CorrelationIdMiddleware,
    get_metrics,
    instrument_fastapi,
    setup_logging,
    setup_tracing,
)
from aether_prompt_registry.infrastructure.repository import (
    PromptRepository,
    create_session_factory,
    init_db,
)
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from pydantic_settings import SettingsConfigDict

logger = structlog.get_logger()


class PromptRegistrySettings(BaseServiceSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    service_name: str = "prompt-registry"
    postgres_url: str = "postgresql+asyncpg://aether:aether@localhost:5432/aether"
    host: str = "0.0.0.0"
    port: int = 8006


settings = PromptRegistrySettings()


def create_app() -> FastAPI:
    setup_logging(settings.service_name, settings.log_level, settings.log_format)
    setup_tracing(settings.service_name)

    app = FastAPI(title="Aether Prompt Registry", version="0.3.0")
    app.add_middleware(CorrelationIdMiddleware)

    session_factory = create_session_factory(settings.postgres_url)
    repo = PromptRepository(session_factory)

    @app.on_event("startup")
    async def startup() -> None:
        await init_db(settings.postgres_url)
        logger.info("prompt_registry_started")

    @app.get("/health")
    async def health() -> dict:
        return {"status": HealthState.HEALTHY.value, "service": settings.service_name}

    @app.get("/metrics")
    async def metrics() -> Response:
        return Response(content=get_metrics(), media_type="text/plain")

    @app.post("/v1/prompts")
    async def create_prompt(template: PromptTemplate) -> dict:
        saved = await repo.create(template)
        return saved.model_dump(mode="json")

    @app.get("/v1/prompts/{agent_name}")
    async def list_prompts(agent_name: str) -> list[dict]:
        prompts = await repo.list_by_agent(agent_name)
        return [p.model_dump(mode="json") for p in prompts]

    @app.post("/v1/prompts/render")
    async def render_prompt(request: PromptRenderRequest) -> dict:
        try:
            result = await repo.render(request)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return result.model_dump(mode="json")

    @app.post("/v1/prompts/{prompt_id}/activate")
    async def activate_prompt(prompt_id: UUID) -> dict:
        activated = await repo.activate(prompt_id)
        if not activated:
            raise HTTPException(status_code=404, detail="Prompt not found")
        return activated.model_dump(mode="json")

    instrument_fastapi(app)
    return app


app = create_app()


def main() -> None:
    import uvicorn

    uvicorn.run("aether_prompt_registry.main:app", host=settings.host, port=settings.port, reload=False)
