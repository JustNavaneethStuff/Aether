from aether_common.agent_runtime.app import run_agent
from aether_common.agent_runtime.stub_agent import StubSettings, create_stub_agent
from aether_common.domain.enums import AgentCapability

settings = StubSettings(service_name="agent-code", service_url="http://localhost:8014", port=8014)
app = create_stub_agent("code", AgentCapability.CODE, settings)


def main() -> None:
    run_agent("aether_agent_code.main:app", settings.host, settings.port)
