from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from aether_common.domain.agent import AgentResult
from aether_common.domain.task_graph import TaskGraph


class CreateConversationRequest(BaseModel):
    metadata: dict[str, Any] = Field(default_factory=dict)


class CreateConversationResponse(BaseModel):
    id: UUID
    metadata: dict[str, Any]


class SendMessageRequest(BaseModel):
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class MessageResponse(BaseModel):
    id: UUID
    role: str
    content: str
    metadata: dict[str, Any]
    created_at: str


class OrchestrationRequest(BaseModel):
    conversation_id: UUID
    message: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class OrchestrationResult(BaseModel):
    conversation_id: UUID
    task_graph: TaskGraph
    agent_results: list[AgentResult]
    final_response: str
    paused: bool = False
    approval_id: UUID | None = None


class AsyncOrchestrationRequest(BaseModel):
    conversation_id: UUID
    message: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class AsyncOrchestrationResponse(BaseModel):
    conversation_id: UUID
    job_id: str
    state: str
    result: OrchestrationResult | None = None


class JobCallbackRequest(BaseModel):
    success: bool = True
    output: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


class StreamEvent(BaseModel):
    event: str
    data: dict[str, Any]
