from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from aether_common.domain.agent import AgentResult
from aether_common.domain.approval import ApprovalRequest, ApprovalStatus
from aether_common.domain.conversation import SharedContext
from aether_common.domain.enums import TaskGraphStatus, TaskStatus
from aether_common.domain.task_graph import TaskGraph, TaskNode
from aether_orchestrator.application.orchestration import OrchestrationService


@pytest.fixture
def conversation_id():
    return uuid4()


@pytest.fixture
def risky_node_id():
    return uuid4()


@pytest.fixture
def task_graph(conversation_id, risky_node_id):
    return TaskGraph(
        conversation_id=conversation_id,
        status=TaskGraphStatus.RUNNING,
        nodes=[
            TaskNode(
                id=risky_node_id,
                agent_name="tool-executor",
                input={"description": "delete production data", "requires_approval": True},
            )
        ],
    )


@pytest.fixture
def orchestration(task_graph, conversation_id, risky_node_id):
    memory = AsyncMock()
    memory.get_context.return_value = SharedContext(conversation_id=conversation_id)
    memory.create_approval.return_value = ApprovalRequest(
        conversation_id=conversation_id,
        task_node_id=risky_node_id,
        agent_name="tool-executor",
        status=ApprovalStatus.PENDING,
    )

    agents = AsyncMock()
    agents.execute.return_value = AgentResult(
        task_id=risky_node_id,
        agent_name="tool-executor",
        success=True,
        output={"content": "done"},
        latency_ms=10,
        usage={"provider": "mock", "model": "mock", "prompt_tokens": 1, "completion_tokens": 1},
    )

    events = AsyncMock()
    checkpoints = AsyncMock()
    agent_bus = AsyncMock()

    service = OrchestrationService(
        memory,
        agents,
        events,
        checkpoints,
        agent_bus,
        approvals_enabled=True,
    )
    return service, memory, agents, events, checkpoints, task_graph, risky_node_id


@pytest.mark.asyncio
async def test_workflow_pauses_for_approval(orchestration, conversation_id):
    service, memory, agents, events, checkpoints, task_graph, _ = orchestration
    checkpoints.get.return_value = None

    paused, approval_id = await service._execute_nodes(
        conversation_id,
        task_graph,
        SharedContext(conversation_id=conversation_id),
        [],
        "delete production data",
    )

    assert paused is True
    assert approval_id is not None
    assert task_graph.nodes[0].status == TaskStatus.AWAITING_APPROVAL
    memory.create_approval.assert_awaited_once()
    assert any(call.args[0] == "approval.requested" for call in events.publish.await_args_list)
    agents.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_approve_resumes_and_executes_node(orchestration, conversation_id):
    service, memory, agents, events, checkpoints, task_graph, risky_node_id = orchestration
    approval_id = uuid4()
    approval = ApprovalRequest(
        id=approval_id,
        conversation_id=conversation_id,
        task_node_id=risky_node_id,
        agent_name="tool-executor",
        status=ApprovalStatus.APPROVED,
    )
    memory.decide_approval.return_value = approval
    checkpoints.get.return_value = {
        "task_graph": task_graph.model_dump(mode="json"),
        "context": SharedContext(conversation_id=conversation_id).model_dump(mode="json"),
        "results": [],
        "completed_nodes": [],
        "message": "delete production data",
        "status": "running",
    }

    result = await service.approve(approval_id, "reviewer")

    assert result.status == ApprovalStatus.APPROVED
    memory.decide_approval.assert_awaited_once()
    agents.execute.assert_awaited()
    events.publish.assert_any_await(
        "approval.decided",
        {"approval_id": str(approval_id), "decision": "approved"},
    )


@pytest.mark.asyncio
async def test_reject_marks_node_failed(orchestration, conversation_id):
    service, memory, _, events, checkpoints, task_graph, risky_node_id = orchestration
    approval_id = uuid4()
    approval = ApprovalRequest(
        id=approval_id,
        conversation_id=conversation_id,
        task_node_id=risky_node_id,
        agent_name="tool-executor",
        status=ApprovalStatus.REJECTED,
    )
    memory.decide_approval.return_value = approval
    checkpoints.get.return_value = {
        "task_graph": task_graph.model_dump(mode="json"),
        "context": SharedContext(conversation_id=conversation_id).model_dump(mode="json"),
        "results": [],
        "completed_nodes": [],
        "message": "delete production data",
        "status": "running",
    }

    result = await service.reject(approval_id, "reviewer", "too risky")

    assert result.status == ApprovalStatus.REJECTED
    saved_graph = memory.save_task_graph.await_args.args[1]
    assert saved_graph.nodes[0].status == TaskStatus.FAILED
    assert saved_graph.status == TaskGraphStatus.FAILED
    checkpoints.delete.assert_awaited_with(str(conversation_id))
    events.publish.assert_any_await(
        "approval.decided",
        {"approval_id": str(approval_id), "decision": "rejected"},
    )
