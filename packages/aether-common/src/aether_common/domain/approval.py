from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ApprovalStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class ApprovalRequest(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    conversation_id: UUID
    task_node_id: UUID
    agent_name: str
    status: ApprovalStatus = ApprovalStatus.PENDING
    reason: str = ""
    payload: dict[str, Any] = Field(default_factory=dict)
    requested_at: datetime = Field(default_factory=datetime.utcnow)
    decided_at: datetime | None = None
    decided_by: str | None = None


class ApprovalDecision(BaseModel):
    approval_id: UUID
    decision: ApprovalStatus
    decided_by: str
    comment: str = ""
