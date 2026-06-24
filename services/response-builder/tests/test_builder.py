from uuid import uuid4

from aether_common.domain.agent import AgentResult
from aether_common.domain.api_models import OrchestrationResult
from aether_common.domain.task_graph import TaskGraph
from aether_response_builder.main import build_response_text


def test_build_response_prefers_summarizer() -> None:
    cid = uuid4()
    task_graph = TaskGraph(conversation_id=cid, nodes=[])
    result = OrchestrationResult(
        conversation_id=cid,
        task_graph=task_graph,
        agent_results=[
            AgentResult(
                task_id=uuid4(),
                agent_name="research",
                success=True,
                output={"content": "research out"},
            ),
            AgentResult(
                task_id=uuid4(),
                agent_name="summarizer",
                success=True,
                output={"content": "final answer"},
            ),
        ],
        final_response="final answer",
    )
    assert build_response_text(result) == "final answer"
