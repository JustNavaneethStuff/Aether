from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from aether_common.domain.enums import TaskGraphStatus, TaskStatus


class TaskNode(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    agent_name: str
    input: dict[str, Any] = Field(default_factory=dict)
    depends_on: list[UUID] = Field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    output: dict[str, Any] | None = None
    error: str | None = None


class TaskGraph(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    conversation_id: UUID
    nodes: list[TaskNode] = Field(default_factory=list)
    status: TaskGraphStatus = TaskGraphStatus.PENDING


def topological_sort(nodes: list[TaskNode]) -> list[TaskNode]:
    """Return nodes in dependency order using Kahn's algorithm."""
    in_degree = {node.id: 0 for node in nodes}
    for node in nodes:
        for dep_id in node.depends_on:
            if dep_id in in_degree:
                in_degree[node.id] += 1

    queue = [node for node in nodes if in_degree[node.id] == 0]
    sorted_nodes: list[TaskNode] = []

    while queue:
        current = queue.pop(0)
        sorted_nodes.append(current)
        for node in nodes:
            if current.id in node.depends_on:
                in_degree[node.id] -= 1
                if in_degree[node.id] == 0:
                    queue.append(node)

    if len(sorted_nodes) != len(nodes):
        raise ValueError("Task graph contains a cycle")

    return sorted_nodes
