from aether_common.agent_runtime.app import run_agent
from aether_common.agent_runtime.stub_agent import StubSettings, create_stub_agent
from aether_common.domain.enums import AgentCapability

settings = StubSettings(
    service_name="agent-fact-checker", service_url="http://localhost:8016", port=8016
)
app = create_stub_agent("fact-checker", AgentCapability.FACT_CHECK, settings)


def main() -> None:
    run_agent("aether_agent_fact_checker.main:app", settings.host, settings.port)
