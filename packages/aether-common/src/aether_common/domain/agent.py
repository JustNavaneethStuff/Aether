from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from aether_common.domain.conversation import SharedContext
from aether_common.domain.enums import AgentCapability, HealthState


class AgentTask(BaseModel):
    task_id: UUID
    description: str
    input: dict[str, Any] = Field(default_factory=dict)


class AgentResult(BaseModel):
    task_id: UUID
    agent_name: str
    success: bool
    output: dict[str, Any] = Field(default_factory=dict)
    artifacts: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    latency_ms: int = 0
    usage: dict[str, Any] = Field(default_factory=dict)


class AgentRegistration(BaseModel):
    name: str
    url: str
    capabilities: list[AgentCapability]
    version: str = "0.1.0"


class HealthStatus(BaseModel):
    state: HealthState
    service: str
    details: dict[str, str] = Field(default_factory=dict)


class ExecuteAgentRequest(BaseModel):
    task: AgentTask
    context: SharedContext


class ExecuteAgentResponse(BaseModel):
    result: AgentResult
