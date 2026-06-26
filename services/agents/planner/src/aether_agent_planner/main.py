import json
import time
from uuid import UUID, uuid4

from aether_common.agent_runtime.app import create_agent_app, run_agent
from aether_common.config.settings import BaseServiceSettings
from aether_common.contracts.agent import CompletionMessage, CompletionRequest
from aether_common.domain.agent import AgentResult, ExecuteAgentRequest
from aether_common.domain.enums import AgentCapability, TaskStatus
from aether_common.domain.task_graph import TaskGraph, TaskNode
from aether_common.infrastructure.llm import create_llm_provider
from pydantic_settings import SettingsConfigDict


class PlannerSettings(BaseServiceSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    service_name: str = "agent-planner"
    service_url: str = "http://localhost:8010"
    host: str = "0.0.0.0"
    port: int = 8010


settings = PlannerSettings()
llm = create_llm_provider(settings)

PLANNER_PROMPT = """You are a task planning agent. Decompose the user's request into a directed task graph.
Return ONLY valid JSON with this structure:
{
  "nodes": [
    {"agent_name": "research", "description": "...", "depends_on": []},
    {"agent_name": "critic", "description": "...", "depends_on": ["research"]},
    {"agent_name": "summarizer", "description": "...", "depends_on": ["research", "critic"]}
  ]
}
Available agents: research, critic, summarizer, code, data-analysis, fact-checker.
Use depends_on with agent names (not UUIDs). Keep graphs acyclic."""


async def execute_planner(request: ExecuteAgentRequest) -> AgentResult:
    start = time.perf_counter()
    user_message = request.context.messages[-1].content if request.context.messages else request.task.description

    response = await llm.complete(
        CompletionRequest(
            messages=[
                CompletionMessage(role="system", content=PLANNER_PROMPT),
                CompletionMessage(role="user", content=user_message),
            ],
            temperature=0.2,
        )
    )

    try:
        plan = json.loads(response.content)
        nodes_data = plan.get("nodes", [])
    except json.JSONDecodeError:
        nodes_data = [
            {"agent_name": "research", "description": user_message, "depends_on": []},
            {"agent_name": "critic", "description": "Review findings", "depends_on": ["research"]},
            {
                "agent_name": "summarizer",
                "description": "Summarize results",
                "depends_on": ["research", "critic"],
            },
        ]

    name_to_id: dict[str, UUID] = {}
    nodes: list[TaskNode] = []
    for item in nodes_data:
        node_id = uuid4()
        name_to_id[item["agent_name"]] = node_id
        nodes.append(
            TaskNode(
                id=node_id,
                agent_name=item["agent_name"],
                input={"description": item.get("description", user_message)},
                depends_on=[],
                status=TaskStatus.PENDING,
            )
        )

    for item, node in zip(nodes_data, nodes, strict=True):
        node.depends_on = [name_to_id[dep] for dep in item.get("depends_on", []) if dep in name_to_id]

    task_graph = TaskGraph(
        conversation_id=request.context.conversation_id,
        nodes=nodes,
    )

    latency_ms = int((time.perf_counter() - start) * 1000)
    return AgentResult(
        task_id=request.task.task_id,
        agent_name="planner",
        success=True,
        output={"task_graph": task_graph.model_dump(mode="json")},
        artifacts={"task_graph": task_graph.model_dump(mode="json")},
        latency_ms=latency_ms,
        usage=response.usage,
    )


app = create_agent_app(
    settings=settings,
    agent_name="planner",
    capabilities=[AgentCapability.PLANNING],
    execute_fn=execute_planner,
    service_url=settings.service_url,
    port=settings.port,
)


def main() -> None:
    run_agent("aether_agent_planner.main:app", settings.host, settings.port)
