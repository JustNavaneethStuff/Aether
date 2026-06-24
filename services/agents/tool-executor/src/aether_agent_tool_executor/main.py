from aether_common.agent_runtime.app import run_agent
from aether_common.agent_runtime.stub_agent import StubSettings, create_stub_agent
from aether_common.domain.enums import AgentCapability

settings = StubSettings(
    service_name="agent-tool-executor", service_url="http://localhost:8018", port=8018
)
app = create_stub_agent("tool-executor", AgentCapability.TOOL_EXECUTION, settings)


def main() -> None:
    run_agent("aether_agent_tool_executor.main:app", settings.host, settings.port)
