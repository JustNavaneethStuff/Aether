from datetime import datetime
from enum import StrEnum
from typing import Any, Protocol

from pydantic import BaseModel, Field


class JobState(StrEnum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobRequest(BaseModel):
    """Aether-side job submission model (anti-corruption boundary for external queues)."""

    name: str
    payload: dict[str, Any] = Field(default_factory=dict)
    priority: int = 2
    max_retries: int = 3
    schedule_at: datetime | None = None
    callback_url: str | None = None
    timeout_seconds: int = 300


class JobHandle(BaseModel):
    job_id: str
    state: JobState = JobState.QUEUED


class JobStatus(BaseModel):
    job_id: str
    state: JobState
    name: str = ""
    result: dict[str, Any] | None = None
    error: str | None = None


class JobResult(BaseModel):
    job_id: str
    success: bool
    output: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


class TaskQueuePort(Protocol):
    async def submit(self, request: JobRequest) -> JobHandle: ...

    async def get_status(self, job_id: str) -> JobStatus: ...

    async def cancel(self, job_id: str) -> JobStatus: ...
