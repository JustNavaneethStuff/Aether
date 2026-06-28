from collections.abc import Awaitable, Callable
from uuid import uuid4

from aether_common.contracts.task_queue import (
    JobHandle,
    JobRequest,
    JobResult,
    JobState,
    JobStatus,
    TaskQueuePort,
)

JobExecutor = Callable[[JobRequest], Awaitable[JobResult]]


class LocalTaskQueue:
    """Default task queue: executes jobs inline when an executor is registered."""

    def __init__(self, executor: JobExecutor | None = None) -> None:
        self._executor = executor
        self._jobs: dict[str, JobStatus] = {}

    def set_executor(self, executor: JobExecutor) -> None:
        self._executor = executor

    async def submit(self, request: JobRequest) -> JobHandle:
        job_id = str(uuid4())
        if self._executor is None:
            status = JobStatus(job_id=job_id, state=JobState.COMPLETED, name=request.name)
            self._jobs[job_id] = status
            return JobHandle(job_id=job_id, state=JobState.COMPLETED)

        self._jobs[job_id] = JobStatus(job_id=job_id, state=JobState.RUNNING, name=request.name)
        try:
            result = await self._executor(request)
            result.job_id = job_id
            state = JobState.COMPLETED if result.success else JobState.FAILED
            self._jobs[job_id] = JobStatus(
                job_id=job_id,
                state=state,
                name=request.name,
                result=result.output,
                error=result.error,
            )
        except Exception as exc:
            self._jobs[job_id] = JobStatus(
                job_id=job_id,
                state=JobState.FAILED,
                name=request.name,
                error=str(exc),
            )
        return JobHandle(job_id=job_id, state=self._jobs[job_id].state)

    async def get_status(self, job_id: str) -> JobStatus:
        if job_id not in self._jobs:
            return JobStatus(job_id=job_id, state=JobState.FAILED, error="Job not found")
        return self._jobs[job_id]

    async def cancel(self, job_id: str) -> JobStatus:
        if job_id in self._jobs and self._jobs[job_id].state in (JobState.PENDING, JobState.QUEUED, JobState.RUNNING):
            self._jobs[job_id] = JobStatus(
                job_id=job_id,
                state=JobState.CANCELLED,
                name=self._jobs[job_id].name,
            )
        return await self.get_status(job_id)


def as_task_queue_port(queue: LocalTaskQueue) -> TaskQueuePort:
    return queue
