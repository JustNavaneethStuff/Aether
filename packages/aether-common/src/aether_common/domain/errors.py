from uuid import UUID


class WorkflowPausedError(Exception):
    """Raised when a workflow pauses for human approval."""

    def __init__(self, conversation_id: UUID, approval_id: UUID, message: str = "") -> None:
        self.conversation_id = conversation_id
        self.approval_id = approval_id
        super().__init__(message or f"Workflow paused for approval: {approval_id}")
