from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class AgentMessage(BaseModel):
    """Inter-agent communication message published on the agent bus."""

    conversation_id: UUID
    from_agent: str
    to_agent: str | None = None  # None = broadcast
    message_type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class WorkflowCheckpoint(BaseModel):
    conversation_id: UUID
    task_graph_id: UUID
    task_graph: dict[str, Any]
    context: dict[str, Any]
    completed_nodes: list[str] = Field(default_factory=list)
    status: str = "running"
