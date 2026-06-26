import time
from uuid import UUID, uuid4

import httpx
import structlog
from aether_common.domain.agent import AgentResult, AgentTask, ExecuteAgentRequest
from aether_common.domain.approval import ApprovalDecision, ApprovalRequest, ApprovalStatus
from aether_common.domain.conversation import SharedContext
from aether_common.domain.enums import MessageRole, TaskGraphStatus, TaskStatus
from aether_common.domain.task_graph import TaskGraph, topological_sort
from aether_common.domain.workflow import AgentMessage
from aether_common.infrastructure.agent_bus import AgentCommunicationBus, CheckpointStore
from aether_common.infrastructure.redis_clients import AgentRegistry, EventBus
from aether_common.observability.telemetry import (
    AGENT_EXECUTIONS,
    APPROVAL_REQUESTS,
    LLM_COST_USD,
    LLM_TOKENS,
    WORKFLOW_PAUSE_DURATION,
)

logger = structlog.get_logger()


class MemoryClient:
    def __init__(self, base_url: str) -> None:
        self._base_url = base_url.rstrip("/")

    async def get_context(self, conversation_id: UUID) -> SharedContext:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self._base_url}/v1/conversations/{conversation_id}/context")
            response.raise_for_status()
            return SharedContext.model_validate(response.json())

    async def update_context(self, conversation_id: UUID, context: SharedContext) -> None:
        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"{self._base_url}/v1/conversations/{conversation_id}/context",
                json=context.model_dump(mode="json"),
            )
            response.raise_for_status()

    async def add_message(self, conversation_id: UUID, role: MessageRole, content: str) -> None:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self._base_url}/v1/conversations/{conversation_id}/messages",
                json={"role": role.value, "content": content},
            )
            response.raise_for_status()

    async def save_task_graph(self, conversation_id: UUID, task_graph: TaskGraph) -> None:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self._base_url}/v1/conversations/{conversation_id}/task-graphs",
                json=task_graph.model_dump(mode="json"),
            )
            response.raise_for_status()

    async def record_execution(self, conversation_id: UUID, agent_name: str, latency_ms: int, usage: dict) -> None:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self._base_url}/v1/conversations/{conversation_id}/executions",
                json={"agent_name": agent_name, "latency_ms": latency_ms, "usage": usage},
            )
            response.raise_for_status()

    async def create_approval(self, request: ApprovalRequest) -> ApprovalRequest:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self._base_url}/v1/approvals",
                json=request.model_dump(mode="json"),
            )
            response.raise_for_status()
            return ApprovalRequest.model_validate(response.json())

    async def decide_approval(self, decision: ApprovalDecision) -> ApprovalRequest:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self._base_url}/v1/approvals/{decision.approval_id}/decide",
                json=decision.model_dump(mode="json"),
            )
            response.raise_for_status()
            return ApprovalRequest.model_validate(response.json())

    async def list_pending_approvals(self) -> list[ApprovalRequest]:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self._base_url}/v1/approvals/pending")
            response.raise_for_status()
            return [ApprovalRequest.model_validate(a) for a in response.json()]

    async def record_usage(
        self,
        conversation_id: UUID,
        agent_name: str,
        provider: str,
        model: str,
        usage: dict,
        latency_ms: int,
    ) -> None:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{self._base_url}/v1/usage",
                json={
                    "conversation_id": str(conversation_id),
                    "agent_name": agent_name,
                    "provider": provider,
                    "model": model,
                    "prompt_tokens": usage.get("prompt_tokens", 0),
                    "completion_tokens": usage.get("completion_tokens", 0),
                    "latency_ms": latency_ms,
                },
            )


class AgentClient:
    def __init__(self, registry: AgentRegistry) -> None:
        self._registry = registry

    async def execute(self, agent_name: str, task: AgentTask, context: SharedContext) -> AgentResult:
        registration = await self._registry.get(agent_name)
        if not registration:
            raise ValueError(f"Agent '{agent_name}' not registered")

        start = time.perf_counter()
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{registration.url.rstrip('/')}/v1/execute",
                json=ExecuteAgentRequest(task=task, context=context).model_dump(mode="json"),
            )
            response.raise_for_status()
            result = AgentResult.model_validate(response.json()["result"])

        duration = time.perf_counter() - start
        AGENT_EXECUTIONS.labels(agent_name=agent_name).observe(duration)
        return result


class OrchestrationService:
    def __init__(
        self,
        memory_client: MemoryClient,
        agent_client: AgentClient,
        event_bus: EventBus,
        checkpoint_store: CheckpointStore,
        agent_bus: AgentCommunicationBus,
        approvals_enabled: bool = False,
    ) -> None:
        self._memory = memory_client
        self._agents = agent_client
        self._events = event_bus
        self._checkpoints = checkpoint_store
        self._agent_bus = agent_bus
        self._approvals_enabled = approvals_enabled

    async def run(
        self, conversation_id: UUID, message: str
    ) -> tuple[TaskGraph, list[AgentResult], str, bool, UUID | None]:
        await self._memory.add_message(conversation_id, MessageRole.USER, message)
        context = await self._memory.get_context(conversation_id)

        planner_task = AgentTask(
            task_id=uuid4(),
            description=message,
            input={"description": message},
        )
        planner_result = await self._agents.execute("planner", planner_task, context)
        await self._events.publish(
            "task.completed",
            {"conversation_id": str(conversation_id), "agent": "planner"},
        )

        task_graph_data = planner_result.output.get("task_graph", {})
        task_graph = TaskGraph.model_validate(task_graph_data)
        task_graph.status = TaskGraphStatus.RUNNING
        await self._memory.save_task_graph(conversation_id, task_graph)

        context.artifacts.update(planner_result.artifacts)
        results: list[AgentResult] = [planner_result]

        paused, approval_id = await self._execute_nodes(conversation_id, task_graph, context, results, message)
        if paused:
            return task_graph, results, "", True, approval_id

        task_graph.status = TaskGraphStatus.COMPLETED
        await self._memory.save_task_graph(conversation_id, task_graph)
        await self._memory.update_context(conversation_id, context)
        await self._checkpoints.delete(str(conversation_id))

        final_response = self._extract_final_response(results)
        await self._memory.add_message(conversation_id, MessageRole.ASSISTANT, final_response)
        await self._events.publish(
            "workflow.completed",
            {"conversation_id": str(conversation_id)},
        )
        return task_graph, results, final_response, False, None

    async def resume(self, conversation_id: UUID) -> tuple[TaskGraph, list[AgentResult], str, bool, UUID | None]:
        checkpoint = await self._checkpoints.get(str(conversation_id))
        if not checkpoint:
            raise ValueError("No checkpoint found for conversation")

        task_graph = TaskGraph.model_validate(checkpoint["task_graph"])
        context = SharedContext.model_validate(checkpoint["context"])
        results: list[AgentResult] = [AgentResult.model_validate(r) for r in checkpoint.get("results", [])]
        message = checkpoint.get("message", "")

        completed_ids = set(checkpoint.get("completed_nodes", []))
        for node in task_graph.nodes:
            if str(node.id) in completed_ids:
                node.status = TaskStatus.COMPLETED

        paused, approval_id = await self._execute_nodes(
            conversation_id, task_graph, context, results, message, skip_completed=True
        )
        if paused:
            return task_graph, results, "", True, approval_id

        task_graph.status = TaskGraphStatus.COMPLETED
        await self._memory.save_task_graph(conversation_id, task_graph)
        await self._memory.update_context(conversation_id, context)
        await self._checkpoints.delete(str(conversation_id))

        final_response = self._extract_final_response(results)
        await self._memory.add_message(conversation_id, MessageRole.ASSISTANT, final_response)
        await self._events.publish(
            "workflow.completed",
            {"conversation_id": str(conversation_id), "resumed": True},
        )
        return task_graph, results, final_response, False, None

    async def approve(self, approval_id: UUID, decided_by: str) -> ApprovalRequest:
        from datetime import UTC, datetime

        decision = ApprovalDecision(
            approval_id=approval_id,
            decision=ApprovalStatus.APPROVED,
            decided_by=decided_by,
        )
        approval = await self._memory.decide_approval(decision)
        APPROVAL_REQUESTS.labels(decision="approved").inc()
        if approval.requested_at:
            pause_seconds = (datetime.now(UTC) - approval.requested_at.replace(tzinfo=UTC)).total_seconds()
            WORKFLOW_PAUSE_DURATION.observe(max(pause_seconds, 0))

        checkpoint = await self._checkpoints.get(str(approval.conversation_id))
        if checkpoint:
            task_graph = TaskGraph.model_validate(checkpoint["task_graph"])
            for node in task_graph.nodes:
                if node.id == approval.task_node_id:
                    node.status = TaskStatus.PENDING
                    node.input["approval_granted"] = True
                    break
            checkpoint["task_graph"] = task_graph.model_dump(mode="json")
            await self._checkpoints.save(str(approval.conversation_id), checkpoint)
            await self._memory.save_task_graph(approval.conversation_id, task_graph)

        await self._events.publish(
            "approval.decided",
            {"approval_id": str(approval_id), "decision": "approved"},
        )
        await self.resume(approval.conversation_id)
        return approval

    async def reject(self, approval_id: UUID, decided_by: str, comment: str = "") -> ApprovalRequest:
        decision = ApprovalDecision(
            approval_id=approval_id,
            decision=ApprovalStatus.REJECTED,
            decided_by=decided_by,
            comment=comment,
        )
        approval = await self._memory.decide_approval(decision)
        APPROVAL_REQUESTS.labels(decision="rejected").inc()

        checkpoint = await self._checkpoints.get(str(approval.conversation_id))
        if checkpoint:
            task_graph = TaskGraph.model_validate(checkpoint["task_graph"])
            task_graph.status = TaskGraphStatus.FAILED
            for node in task_graph.nodes:
                if node.id == approval.task_node_id:
                    node.status = TaskStatus.FAILED
                    node.error = comment or "Rejected by approver"
            await self._memory.save_task_graph(approval.conversation_id, task_graph)
            await self._checkpoints.delete(str(approval.conversation_id))

        await self._events.publish(
            "approval.decided",
            {"approval_id": str(approval_id), "decision": "rejected"},
        )
        return approval

    async def _execute_nodes(
        self,
        conversation_id: UUID,
        task_graph: TaskGraph,
        context: SharedContext,
        results: list[AgentResult],
        message: str,
        skip_completed: bool = False,
    ) -> tuple[bool, UUID | None]:
        completed_nodes: list[str] = []
        if skip_completed:
            completed_nodes = [str(n.id) for n in task_graph.nodes if n.status == TaskStatus.COMPLETED]

        for node in topological_sort(task_graph.nodes):
            if skip_completed and node.status == TaskStatus.COMPLETED:
                continue

            requires_approval = (
                self._approvals_enabled
                and node.input.get("requires_approval", False)
                and not node.input.get("approval_granted", False)
                and node.status != TaskStatus.COMPLETED
            )
            if requires_approval and node.status != TaskStatus.AWAITING_APPROVAL:
                node.status = TaskStatus.AWAITING_APPROVAL
                approval = await self._memory.create_approval(
                    ApprovalRequest(
                        conversation_id=conversation_id,
                        task_node_id=node.id,
                        agent_name=node.agent_name,
                        reason=node.input.get("approval_reason", "High-risk task"),
                        payload={"description": node.input.get("description", message)},
                    )
                )
                APPROVAL_REQUESTS.labels(decision="pending").inc()
                await self._events.publish(
                    "approval.requested",
                    {
                        "conversation_id": str(conversation_id),
                        "approval_id": str(approval.id),
                        "agent": node.agent_name,
                    },
                )
                await self._save_checkpoint(conversation_id, task_graph, context, results, completed_nodes, message)
                return True, approval.id

            if node.status == TaskStatus.AWAITING_APPROVAL:
                await self._save_checkpoint(conversation_id, task_graph, context, results, completed_nodes, message)
                return True, None

            node.status = TaskStatus.RUNNING
            await self._events.publish(
                "task.started",
                {"conversation_id": str(conversation_id), "agent": node.agent_name},
            )

            await self._agent_bus.publish(
                AgentMessage(
                    conversation_id=conversation_id,
                    from_agent="orchestrator",
                    to_agent=node.agent_name,
                    message_type="task.dispatch",
                    payload={"task_id": str(node.id), "description": node.input},
                )
            )

            task = AgentTask(
                task_id=node.id,
                description=node.input.get("description", message),
                input=node.input,
            )
            try:
                result = await self._agents.execute(node.agent_name, task, context)
                node.status = TaskStatus.COMPLETED if result.success else TaskStatus.FAILED
                node.output = result.output
                context.artifacts.update(result.artifacts)
                results.append(result)
                completed_nodes.append(str(node.id))
                await self._memory.record_execution(conversation_id, node.agent_name, result.latency_ms, result.usage)
                if result.usage:
                    provider = result.usage.get("provider", "unknown")
                    model = result.usage.get("model", "unknown")
                    prompt_tokens = result.usage.get("prompt_tokens", 0)
                    completion_tokens = result.usage.get("completion_tokens", 0)
                    await self._memory.record_usage(
                        conversation_id,
                        node.agent_name,
                        provider,
                        model,
                        result.usage,
                        result.latency_ms,
                    )
                    LLM_TOKENS.labels(provider=provider, model=model, type="prompt").inc(prompt_tokens)
                    LLM_TOKENS.labels(provider=provider, model=model, type="completion").inc(completion_tokens)
                    from aether_common.infrastructure.pricing import estimate_cost_usd

                    cost, _ = estimate_cost_usd(provider, model, prompt_tokens, completion_tokens)
                    if cost:
                        LLM_COST_USD.labels(provider=provider, model=model).inc(cost)
                await self._events.publish(
                    "task.completed",
                    {"conversation_id": str(conversation_id), "agent": node.agent_name},
                )
            except Exception as exc:
                node.status = TaskStatus.FAILED
                node.error = str(exc)
                await self._events.publish(
                    "agent.failed",
                    {
                        "conversation_id": str(conversation_id),
                        "agent": node.agent_name,
                        "error": str(exc),
                    },
                )
                logger.error("agent_execution_failed", agent=node.agent_name, error=str(exc))

            await self._save_checkpoint(conversation_id, task_graph, context, results, completed_nodes, message)

        return False, None

    async def _save_checkpoint(
        self,
        conversation_id: UUID,
        task_graph: TaskGraph,
        context: SharedContext,
        results: list[AgentResult],
        completed_nodes: list[str],
        message: str,
    ) -> None:
        await self._memory.save_task_graph(conversation_id, task_graph)
        await self._checkpoints.save(
            str(conversation_id),
            {
                "task_graph": task_graph.model_dump(mode="json"),
                "context": context.model_dump(mode="json"),
                "results": [r.model_dump(mode="json") for r in results],
                "completed_nodes": completed_nodes,
                "message": message,
                "status": "running",
            },
        )

    def _extract_final_response(self, results: list[AgentResult]) -> str:
        for result in reversed(results):
            if result.agent_name == "summarizer" and result.output.get("content"):
                return str(result.output["content"])
        for result in reversed(results):
            if result.output.get("content"):
                return str(result.output["content"])
        return "Workflow completed with no summarizer output."
