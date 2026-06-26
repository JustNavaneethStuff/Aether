from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class PromptTemplate(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    agent_name: str
    prompt_name: str
    version: str
    content: str
    provider: str | None = None
    model: str | None = None
    is_active: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class PromptVersion(BaseModel):
    id: UUID
    version: str
    is_active: bool
    created_at: datetime


class PromptRenderRequest(BaseModel):
    agent_name: str
    prompt_name: str
    variables: dict[str, Any] = Field(default_factory=dict)
    version: str | None = None


class PromptRenderResult(BaseModel):
    content: str
    prompt_id: UUID
    version: str
    agent_name: str
    prompt_name: str
