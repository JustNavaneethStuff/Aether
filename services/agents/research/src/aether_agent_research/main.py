from aether_common.agent_runtime.app import run_agent
from aether_common.agent_runtime.llm_agent import AgentSettings, build_agent
from aether_common.domain.enums import AgentCapability

settings = AgentSettings(
    service_name="agent-research",
    service_url="http://localhost:8011",
    port=8011,
)
app, _ = build_agent(
    agent_name="research",
    capability=AgentCapability.RESEARCH,
    system_prompt="You are a research agent. Gather and synthesize information to answer the task.",
    settings=settings,
)


def main() -> None:
    run_agent("aether_agent_research.main:app", settings.host, settings.port)
