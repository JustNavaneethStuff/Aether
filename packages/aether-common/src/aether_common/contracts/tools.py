from typing import Any, Protocol
from uuid import UUID

from pydantic import BaseModel, Field


class ToolDefinition(BaseModel):
    name: str
    description: str
    parameters: dict[str, Any] = Field(default_factory=dict)


class ToolCall(BaseModel):
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    call_id: str = ""


class ToolResult(BaseModel):
    call_id: str
    tool_name: str
    success: bool
    output: Any = None
    error: str | None = None


class ToolProtocol(Protocol):
    definition: ToolDefinition

    async def execute(self, arguments: dict[str, Any], context: dict[str, Any]) -> ToolResult: ...


class KnowledgeDocument(BaseModel):
    id: UUID | None = None
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    embedding: list[float] | None = None


class KnowledgeQuery(BaseModel):
    query: str
    top_k: int = 5
    conversation_id: UUID | None = None


class KnowledgeChunk(BaseModel):
    content: str
    score: float
    metadata: dict[str, Any] = Field(default_factory=dict)


class KnowledgeRetriever(Protocol):
    async def ingest(self, document: KnowledgeDocument) -> UUID: ...
    async def search(self, query: KnowledgeQuery) -> list[KnowledgeChunk]: ...
