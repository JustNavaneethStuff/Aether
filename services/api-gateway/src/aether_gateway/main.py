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
from aether_common.infrastructure.auth import JWTAuthProvider
from aether_common.infrastructure.rate_limiter import RateLimiter
from aether_common.infrastructure.redis_clients import AgentRegistry
from aether_common.observability.telemetry import (
    CorrelationIdMiddleware,
    get_metrics,
    instrument_fastapi,
    setup_logging,
    setup_tracing,
)
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import Response, StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from pydantic_settings import SettingsConfigDict
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

security = HTTPBearer(auto_error=False)


class GatewaySettings(BaseServiceSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    service_name: str = "api-gateway"
    orchestrator_url: str = "http://localhost:8001"
    memory_service_url: str = "http://localhost:8002"
    response_builder_url: str = "http://localhost:8003"
    knowledge_service_url: str = "http://localhost:8004"
    evaluation_service_url: str = "http://localhost:8005"
    prompt_registry_url: str = "http://localhost:8006"
    host: str = "0.0.0.0"
    port: int = 8000
    auth_enabled: bool = False
    jwt_secret: str = "aether-dev-secret-change-in-production"
    rate_limit_requests: int = 60
    rate_limit_window_seconds: int = 60


class TokenRequest(BaseModel):
    user_id: str
    roles: list[str] = ["user"]


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, rate_limiter: RateLimiter) -> None:
        super().__init__(app)
        self._limiter = rate_limiter

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.url.path in ("/health", "/metrics", "/v1/auth/token"):
            return await call_next(request)
        client_id = request.headers.get("X-API-Key") or request.client.host or "anonymous"
        allowed, remaining = await self._limiter.is_allowed(client_id)
        if not allowed:
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        response = await call_next(request)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response


settings = GatewaySettings()


def create_app() -> FastAPI:
    setup_logging(settings.service_name, settings.log_level, settings.log_format)
    setup_tracing(settings.service_name)

    app = FastAPI(title="Aether API Gateway", version="0.3.0")
    app.add_middleware(CorrelationIdMiddleware)

    redis_client = redis.from_url(settings.redis_url, decode_responses=True)
    registry = AgentRegistry(redis_client)
    auth_provider = JWTAuthProvider(settings.jwt_secret)
    rate_limiter = RateLimiter(redis_client, settings.rate_limit_requests, settings.rate_limit_window_seconds)
    app.add_middleware(RateLimitMiddleware, rate_limiter=rate_limiter)

    async def get_current_user(
        credentials: HTTPAuthorizationCredentials | None = Depends(security),  # noqa: B008
    ) -> str | None:
        if not settings.auth_enabled:
            return None
        if not credentials:
            raise HTTPException(status_code=401, detail="Authentication required")
        user = await auth_provider.authenticate(credentials.credentials)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid token")
        return user.user_id

    @app.get("/health")
    async def health() -> dict:
        services = {
            "orchestrator": settings.orchestrator_url,
            "memory": settings.memory_service_url,
            "response_builder": settings.response_builder_url,
            "knowledge": settings.knowledge_service_url,
            "evaluation": settings.evaluation_service_url,
            "prompt_registry": settings.prompt_registry_url,
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

    @app.post("/v1/auth/token")
    async def create_token(request: TokenRequest) -> dict:
        token = await auth_provider.create_token(request.user_id, request.roles)
        return {"access_token": token, "token_type": "bearer"}

    @app.post("/v1/conversations", response_model=CreateConversationResponse)
    async def create_conversation(
        request: CreateConversationRequest,
        _user: str | None = Depends(get_current_user),
    ) -> CreateConversationResponse:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.memory_service_url}/v1/conversations",
                json=request.model_dump(mode="json"),
            )
            response.raise_for_status()
            return CreateConversationResponse.model_validate(response.json())

    @app.get("/v1/conversations/{conversation_id}")
    async def get_conversation(
        conversation_id: UUID,
        _user: str | None = Depends(get_current_user),
    ) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{settings.memory_service_url}/v1/conversations/{conversation_id}")
            if response.status_code == 404:
                raise HTTPException(status_code=404, detail="Conversation not found")
            response.raise_for_status()
            return response.json()

    @app.get("/v1/conversations/{conversation_id}/messages")
    async def list_messages(
        conversation_id: UUID,
        _user: str | None = Depends(get_current_user),
    ) -> list[dict]:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{settings.memory_service_url}/v1/conversations/{conversation_id}/messages")
            response.raise_for_status()
            return response.json()

    @app.post("/v1/conversations/{conversation_id}/messages")
    async def send_message(
        conversation_id: UUID,
        request: SendMessageRequest,
        _user: str | None = Depends(get_current_user),
    ) -> StreamingResponse:
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

    @app.post("/v1/conversations/{conversation_id}/resume")
    async def resume_workflow(
        conversation_id: UUID,
        _user: str | None = Depends(get_current_user),
    ) -> dict:
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                f"{settings.orchestrator_url}/v1/orchestrate/resume",
                json={"conversation_id": str(conversation_id)},
            )
            response.raise_for_status()
            return response.json()

    @app.post("/v1/knowledge/documents")
    async def ingest_document(
        body: dict,
        _user: str | None = Depends(get_current_user),
    ) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.knowledge_service_url}/v1/documents",
                json=body,
            )
            response.raise_for_status()
            return response.json()

    @app.post("/v1/knowledge/search")
    async def search_knowledge(
        body: dict,
        _user: str | None = Depends(get_current_user),
    ) -> list[dict]:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.knowledge_service_url}/v1/search",
                json=body,
            )
            response.raise_for_status()
            return response.json()

    @app.get("/v1/agents")
    async def list_agents(_user: str | None = Depends(get_current_user)) -> list[dict]:
        agents = await registry.list_all()
        return [a.model_dump(mode="json") for a in agents]

    @app.get("/v1/tools")
    async def list_tools(_user: str | None = Depends(get_current_user)) -> list[dict]:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{settings.orchestrator_url}/v1/tools")
            response.raise_for_status()
            return response.json()

    @app.get("/v1/approvals/pending")
    async def list_pending_approvals(_user: str | None = Depends(get_current_user)) -> list[dict]:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{settings.orchestrator_url}/v1/approvals/pending")
            response.raise_for_status()
            return response.json()

    @app.post("/v1/approvals/{approval_id}/approve")
    async def approve_workflow(approval_id: UUID, body: dict, _user: str | None = Depends(get_current_user)) -> dict:
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                f"{settings.orchestrator_url}/v1/approvals/{approval_id}/approve",
                json=body,
            )
            response.raise_for_status()
            return response.json()

    @app.post("/v1/approvals/{approval_id}/reject")
    async def reject_workflow(approval_id: UUID, body: dict, _user: str | None = Depends(get_current_user)) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.orchestrator_url}/v1/approvals/{approval_id}/reject",
                json=body,
            )
            response.raise_for_status()
            return response.json()

    @app.post("/v1/evaluations/run")
    async def run_evaluation(body: dict, _user: str | None = Depends(get_current_user)) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{settings.evaluation_service_url}/v1/evaluations/run", json=body)
            response.raise_for_status()
            return response.json()

    @app.get("/v1/evaluations/{conversation_id}")
    async def get_evaluations(conversation_id: UUID, _user: str | None = Depends(get_current_user)) -> list[dict]:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{settings.evaluation_service_url}/v1/evaluations/{conversation_id}")
            response.raise_for_status()
            return response.json()

    @app.get("/v1/evaluations/summary")
    async def evaluation_summary(_user: str | None = Depends(get_current_user)) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{settings.evaluation_service_url}/v1/evaluations/summary")
            response.raise_for_status()
            return response.json()

    @app.post("/v1/prompts")
    async def create_prompt(body: dict, _user: str | None = Depends(get_current_user)) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{settings.prompt_registry_url}/v1/prompts", json=body)
            response.raise_for_status()
            return response.json()

    @app.get("/v1/prompts/{agent_name}")
    async def list_prompts(agent_name: str, _user: str | None = Depends(get_current_user)) -> list[dict]:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{settings.prompt_registry_url}/v1/prompts/{agent_name}")
            response.raise_for_status()
            return response.json()

    @app.post("/v1/prompts/render")
    async def render_prompt(body: dict, _user: str | None = Depends(get_current_user)) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{settings.prompt_registry_url}/v1/prompts/render", json=body)
            response.raise_for_status()
            return response.json()

    @app.get("/v1/usage/cost-summary")
    async def cost_summary(conversation_id: UUID | None = None, _user: str | None = Depends(get_current_user)) -> dict:
        async with httpx.AsyncClient() as client:
            params = {"conversation_id": str(conversation_id)} if conversation_id else {}
            response = await client.get(f"{settings.memory_service_url}/v1/usage/cost-summary", params=params)
            response.raise_for_status()
            return response.json()

    @app.get("/v1/experiments")
    async def list_experiments(_user: str | None = Depends(get_current_user)) -> list[dict]:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{settings.memory_service_url}/v1/experiments")
            response.raise_for_status()
            return response.json()

    instrument_fastapi(app)
    return app


app = create_app()


def main() -> None:
    import uvicorn

    uvicorn.run("aether_gateway.main:app", host=settings.host, port=settings.port, reload=False)
