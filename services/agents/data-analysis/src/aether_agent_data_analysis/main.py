from aether_common.agent_runtime.app import run_agent
from aether_common.agent_runtime.stub_agent import StubSettings, create_stub_agent
from aether_common.domain.enums import AgentCapability

settings = StubSettings(
    service_name="agent-data-analysis", service_url="http://localhost:8015", port=8015
)
app = create_stub_agent("data-analysis", AgentCapability.DATA_ANALYSIS, settings)


def main() -> None:
    run_agent("aether_agent_data_analysis.main:app", settings.host, settings.port)
