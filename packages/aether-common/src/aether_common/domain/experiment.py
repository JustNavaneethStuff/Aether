from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ExperimentStatus(StrEnum):
    DRAFT = "draft"
    RUNNING = "running"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class ExperimentVariant(BaseModel):
    name: str
    weight: float = 1.0
    config: dict[str, Any] = Field(default_factory=dict)


class Experiment(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str
    description: str = ""
    status: ExperimentStatus = ExperimentStatus.DRAFT
    variants: list[ExperimentVariant] = Field(default_factory=list)
    assignment_strategy: str = "hash"
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ExperimentAssignment(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    experiment_id: UUID
    conversation_id: UUID
    variant_name: str
    assigned_at: datetime = Field(default_factory=datetime.utcnow)


class CostSummary(BaseModel):
    conversation_id: UUID | None = None
    provider: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
    pricing_unknown: bool = False


class LatencySummary(BaseModel):
    conversation_id: UUID | None = None
    agent_name: str | None = None
    latency_ms: int = 0
    p50_ms: float | None = None
    p95_ms: float | None = None
