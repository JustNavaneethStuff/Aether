from enum import StrEnum


class MessageRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class TaskStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    AWAITING_APPROVAL = "awaiting_approval"


class TaskGraphStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentCapability(StrEnum):
    PLANNING = "planning"
    RESEARCH = "research"
    CODE = "code"
    DATA_ANALYSIS = "data_analysis"
    CRITIQUE = "critique"
    FACT_CHECK = "fact_check"
    SUMMARIZE = "summarize"
    MEMORY = "memory"
    TOOL_EXECUTION = "tool_execution"


class HealthState(StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
