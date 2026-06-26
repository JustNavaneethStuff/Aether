import time

from aether_common.agent_runtime.app import create_agent_app
from aether_common.config.settings import BaseServiceSettings
from aether_common.contracts.agent import CompletionMessage, CompletionRequest
from aether_common.domain.agent import AgentResult, ExecuteAgentRequest
from aether_common.domain.enums import AgentCapability
from aether_common.infrastructure.llm import create_llm_provider
from pydantic_settings import SettingsConfigDict


class AgentSettings(BaseServiceSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    service_name: str = "AGENT_NAME"
    service_url: str = "http://localhost:8000"
    host: str = "0.0.0.0"
    port: int = 8000


def build_agent(
    agent_name: str,
    capability: AgentCapability,
    system_prompt: str,
    settings: AgentSettings,
) -> tuple:
    llm = create_llm_provider(settings)

    async def execute(request: ExecuteAgentRequest) -> AgentResult:
        start = time.perf_counter()
        description = request.task.input.get("description", request.task.description)
        context_summary = "\n".join(f"{m.role}: {m.content}" for m in request.context.messages[-6:])
        artifacts_text = "\n".join(f"{k}: {str(v)[:500]}" for k, v in request.context.artifacts.items())

        response = await llm.complete(
            CompletionRequest(
                messages=[
                    CompletionMessage(role="system", content=system_prompt),
                    CompletionMessage(
                        role="user",
                        content=f"Task: {description}\n\nContext:\n{context_summary}\n\nArtifacts:\n{artifacts_text}",
                    ),
                ],
                temperature=0.5,
            )
        )
        latency_ms = int((time.perf_counter() - start) * 1000)
        return AgentResult(
            task_id=request.task.task_id,
            agent_name=agent_name,
            success=True,
            output={"content": response.content},
            artifacts={agent_name: response.content},
            latency_ms=latency_ms,
            usage=response.usage,
        )

    app = create_agent_app(
        settings=settings,
        agent_name=agent_name,
        capabilities=[capability],
        execute_fn=execute,
        service_url=settings.service_url,
        port=settings.port,
    )
    return app, settings
