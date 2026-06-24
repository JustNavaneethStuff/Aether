from collections.abc import AsyncIterator
from typing import Any, Protocol

from aether_common.domain.agent import AgentResult, AgentTask, HealthStatus
from aether_common.domain.conversation import SharedContext
from aether_common.domain.enums import AgentCapability
from pydantic import BaseModel


class AgentProtocol(Protocol):
    name: str
    capabilities: frozenset[AgentCapability]

    async def execute(self, task: AgentTask, context: SharedContext) -> AgentResult: ...
    async def health(self) -> HealthStatus: ...


class CompletionMessage(BaseModel):
    role: str
    content: str


class CompletionRequest(BaseModel):
    messages: list[CompletionMessage]
    model: str | None = None
    temperature: float = 0.7
    max_tokens: int = 4096
    metadata: dict[str, Any] = {}


class CompletionResponse(BaseModel):
    content: str
    model: str
    usage: dict[str, int] = {}
    latency_ms: int = 0


class StreamChunk(BaseModel):
    content: str
    done: bool = False


class LLMProvider(Protocol):
    async def complete(self, request: CompletionRequest) -> CompletionResponse: ...
    async def stream(self, request: CompletionRequest) -> AsyncIterator[StreamChunk]: ...
