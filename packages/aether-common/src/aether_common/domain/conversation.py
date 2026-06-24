from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from aether_common.domain.enums import MessageRole


class Message(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    role: MessageRole
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Conversation(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class SharedContext(BaseModel):
    conversation_id: UUID
    messages: list[Message] = Field(default_factory=list)
    artifacts: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
