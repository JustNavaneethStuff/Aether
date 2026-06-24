from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class DomainEvent(BaseModel):
    event_type: str
    conversation_id: UUID | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    payload: dict[str, Any] = Field(default_factory=dict)


class TaskStartedEvent(DomainEvent):
    event_type: str = "task.started"


class TaskCompletedEvent(DomainEvent):
    event_type: str = "task.completed"


class AgentFailedEvent(DomainEvent):
    event_type: str = "agent.failed"


class LLMUsageEvent(DomainEvent):
    event_type: str = "llm.usage"


class WorkflowCompletedEvent(DomainEvent):
    event_type: str = "workflow.completed"
