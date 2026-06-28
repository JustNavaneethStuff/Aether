import time
from uuid import uuid4

from aether_common.agent_runtime.app import create_agent_app, run_agent
from aether_common.config.settings import BaseServiceSettings
from aether_common.contracts.knowledge_acquisition import CrawlRequest
from aether_common.contracts.tools import KnowledgeQuery, ToolCall, ToolResult
from aether_common.domain.agent import AgentResult, ExecuteAgentRequest
from aether_common.domain.enums import AgentCapability
from aether_common.integrations.factory import build_knowledge_acquisition
from aether_common.plugins.registry import BuiltinTools
from pydantic_settings import SettingsConfigDict


class ToolExecutorSettings(BaseServiceSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    service_name: str = "agent-tool-executor"
    service_url: str = "http://localhost:8018"
    knowledge_service_url: str = "http://localhost:8004"
    host: str = "0.0.0.0"
    port: int = 8018


settings = ToolExecutorSettings()
knowledge = build_knowledge_acquisition(settings)


async def execute_tools(request: ExecuteAgentRequest) -> AgentResult:
    start = time.perf_counter()
    task_input = request.task.input
    tool_calls_raw = task_input.get("tool_calls", [])
    if not tool_calls_raw and "tool_name" in task_input:
        tool_calls_raw = [task_input]

    results = []
    for raw in tool_calls_raw:
        call = ToolCall.model_validate(raw) if isinstance(raw, dict) else raw
        call_id = call.call_id or str(uuid4())

        if call.tool_name == "calculator":
            result = BuiltinTools.calculator({**call.arguments, "call_id": call_id}, {})
            results.append(result.model_dump())
        elif call.tool_name == "knowledge_search":
            chunks = await knowledge.search(
                KnowledgeQuery(
                    query=call.arguments.get("query", ""),
                    top_k=call.arguments.get("top_k", 5),
                    conversation_id=request.context.conversation_id,
                )
            )
            results.append(
                ToolResult(
                    call_id=call_id,
                    tool_name="knowledge_search",
                    success=True,
                    output=[c.model_dump(mode="json") for c in chunks],
                ).model_dump()
            )
        elif call.tool_name == "web_crawl":
            handle = await knowledge.trigger_crawl(
                CrawlRequest(
                    seed_urls=call.arguments.get("seed_urls", []),
                    max_depth=call.arguments.get("max_depth", 1),
                    allowed_domains=call.arguments.get("allowed_domains", []),
                    incremental=call.arguments.get("incremental", False),
                    conversation_id=request.context.conversation_id,
                )
            )
            results.append(
                ToolResult(
                    call_id=call_id,
                    tool_name="web_crawl",
                    success=True,
                    output=handle.model_dump(mode="json"),
                ).model_dump()
            )
        else:
            results.append(
                ToolResult(
                    call_id=call_id,
                    tool_name=call.tool_name,
                    success=False,
                    error=f"Unknown tool: {call.tool_name}",
                ).model_dump()
            )

    latency_ms = int((time.perf_counter() - start) * 1000)
    return AgentResult(
        task_id=request.task.task_id,
        agent_name="tool-executor",
        success=True,
        output={"tool_results": results},
        artifacts={"tool_results": results},
        latency_ms=latency_ms,
    )


app = create_agent_app(
    settings=settings,
    agent_name="tool-executor",
    capabilities=[AgentCapability.TOOL_EXECUTION],
    execute_fn=execute_tools,
    service_url=settings.service_url,
    port=settings.port,
)


def main() -> None:
    run_agent("aether_agent_tool_executor.main:app", settings.host, settings.port)
