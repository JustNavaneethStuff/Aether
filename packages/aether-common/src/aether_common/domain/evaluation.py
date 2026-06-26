from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class EvaluationStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class EvaluationMetric(BaseModel):
    name: str
    value: float
    weight: float = 1.0
    passed: bool = True
    details: dict[str, Any] = Field(default_factory=dict)


class EvaluationRubric(BaseModel):
    name: str = "default"
    max_latency_ms: int = 120000
    max_failed_agents: int = 0
    min_final_response_length: int = 10
    max_total_tokens: int = 100000


class EvaluationScore(BaseModel):
    metric: str
    score: float
    max_score: float = 1.0
    passed: bool = True


class EvaluationRun(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    conversation_id: UUID
    status: EvaluationStatus = EvaluationStatus.PENDING
    overall_score: float = 0.0
    passed: bool = False
    scores: list[EvaluationScore] = Field(default_factory=list)
    rubric: EvaluationRubric = Field(default_factory=EvaluationRubric)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
