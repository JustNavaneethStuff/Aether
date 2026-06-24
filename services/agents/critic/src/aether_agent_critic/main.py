from aether_common.agent_runtime.app import run_agent
from aether_common.agent_runtime.llm_agent import AgentSettings, build_agent
from aether_common.domain.enums import AgentCapability

settings = AgentSettings(
    service_name="agent-critic",
    service_url="http://localhost:8012",
    port=8012,
)
app, _ = build_agent(
    agent_name="critic",
    capability=AgentCapability.CRITIQUE,
    system_prompt="You are a critic agent. Review prior agent outputs for gaps, risks, and improvements.",
    settings=settings,
)


def main() -> None:
    run_agent("aether_agent_critic.main:app", settings.host, settings.port)
