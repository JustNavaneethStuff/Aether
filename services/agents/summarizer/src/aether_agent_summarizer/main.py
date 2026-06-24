from aether_common.agent_runtime.app import run_agent
from aether_common.agent_runtime.llm_agent import AgentSettings, build_agent
from aether_common.domain.enums import AgentCapability

settings = AgentSettings(
    service_name="agent-summarizer",
    service_url="http://localhost:8013",
    port=8013,
)
app, _ = build_agent(
    agent_name="summarizer",
    capability=AgentCapability.SUMMARIZE,
    system_prompt="You are a summarizer agent. Produce a clear, concise final answer from all prior work.",
    settings=settings,
)


def main() -> None:
    run_agent("aether_agent_summarizer.main:app", settings.host, settings.port)
