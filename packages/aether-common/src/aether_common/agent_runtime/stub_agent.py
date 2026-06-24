import time

from aether_common.agent_runtime.app import create_agent_app
from aether_common.config.settings import BaseServiceSettings
from aether_common.domain.agent import AgentResult, ExecuteAgentRequest
from aether_common.domain.enums import AgentCapability
from pydantic_settings import SettingsConfigDict


class StubSettings(BaseServiceSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    service_name: str = "agent-stub"
    service_url: str = "http://localhost:8000"
    host: str = "0.0.0.0"
    port: int = 8000


def create_stub_agent(
    agent_name: str,
    capability: AgentCapability,
    settings: StubSettings,
):
    async def execute(request: ExecuteAgentRequest) -> AgentResult:
        start = time.perf_counter()
        description = request.task.input.get("description", request.task.description)
        content = (
            f"[{agent_name} stub] Acknowledged task: {description[:200]}. "
            f"Full implementation planned for Phase 2."
        )
        latency_ms = int((time.perf_counter() - start) * 1000)
        return AgentResult(
            task_id=request.task.task_id,
            agent_name=agent_name,
            success=True,
            output={"content": content, "stub": True},
            artifacts={agent_name: content},
            latency_ms=latency_ms,
        )

    return create_agent_app(
        settings=settings,
        agent_name=agent_name,
        capabilities=[capability],
        execute_fn=execute,
        service_url=settings.service_url,
        port=settings.port,
    )
