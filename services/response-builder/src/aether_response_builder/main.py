import asyncio
import json
from collections.abc import AsyncIterator

from aether_common.config.settings import BaseServiceSettings
from aether_common.domain.api_models import OrchestrationResult
from aether_common.domain.enums import HealthState
from aether_common.observability.telemetry import (
    CorrelationIdMiddleware,
    get_metrics,
    instrument_fastapi,
    setup_logging,
    setup_tracing,
)
from fastapi import FastAPI
from fastapi.responses import Response, StreamingResponse
from pydantic_settings import SettingsConfigDict


class ResponseBuilderSettings(BaseServiceSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    service_name: str = "response-builder"
    host: str = "0.0.0.0"
    port: int = 8003


settings = ResponseBuilderSettings()


def build_response_text(result: OrchestrationResult) -> str:
    return result.final_response


async def stream_response(result: OrchestrationResult) -> AsyncIterator[str]:
    text = build_response_text(result)
    words = text.split()
    yield f"event: start\ndata: {json.dumps({'conversation_id': str(result.conversation_id)})}\n\n"
    for agent_result in result.agent_results:
        payload = {"agent": agent_result.agent_name, "success": agent_result.success}
        yield f"event: agent\ndata: {json.dumps(payload)}\n\n"
        await asyncio.sleep(0.01)
    for i, word in enumerate(words):
        payload = {"chunk": word + " ", "index": i}
        yield f"event: token\ndata: {json.dumps(payload)}\n\n"
        await asyncio.sleep(0.02)
    yield f"event: done\ndata: {json.dumps({'content': text})}\n\n"


def create_app() -> FastAPI:
    setup_logging(settings.service_name, settings.log_level, settings.log_format)
    setup_tracing(settings.service_name)

    app = FastAPI(title="Aether Response Builder", version="0.1.0")
    app.add_middleware(CorrelationIdMiddleware)

    @app.get("/health")
    async def health() -> dict:
        return {"status": HealthState.HEALTHY.value, "service": settings.service_name}

    @app.get("/metrics")
    async def metrics() -> Response:
        return Response(content=get_metrics(), media_type="text/plain")

    @app.post("/v1/build")
    async def build(result: OrchestrationResult) -> dict:
        return {"content": build_response_text(result)}

    @app.post("/v1/stream")
    async def stream(result: OrchestrationResult) -> StreamingResponse:
        return StreamingResponse(stream_response(result), media_type="text/event-stream")

    instrument_fastapi(app)
    return app


app = create_app()


def main() -> None:
    import uvicorn

    uvicorn.run(
        "aether_response_builder.main:app", host=settings.host, port=settings.port, reload=False
    )
