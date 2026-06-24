from aether_common.agent_runtime.app import run_agent
from aether_common.agent_runtime.stub_agent import StubSettings, create_stub_agent
from aether_common.domain.enums import AgentCapability

settings = StubSettings(
    service_name="agent-memory-manager", service_url="http://localhost:8017", port=8017
)
app = create_stub_agent("memory-manager", AgentCapability.MEMORY, settings)


def main() -> None:
    run_agent("aether_agent_memory_manager.main:app", settings.host, settings.port)
