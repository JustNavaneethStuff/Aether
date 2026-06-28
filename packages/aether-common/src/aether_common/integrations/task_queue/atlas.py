import httpx
import structlog

from aether_common.contracts.task_queue import JobHandle, JobRequest, JobState, JobStatus, TaskQueuePort

logger = structlog.get_logger()

_ATLAS_STATE_MAP: dict[str, JobState] = {
    "queued": JobState.QUEUED,
    "scheduled": JobState.QUEUED,
    "running": JobState.RUNNING,
    "completed": JobState.COMPLETED,
    "failed": JobState.FAILED,
    "dead_letter": JobState.FAILED,
    "cancelled": JobState.CANCELLED,
}


class AtlasQueueAdapter:
    """HTTP adapter for Atlas Queue. Not selected by default."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        execute_url: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._execute_url = execute_url
        self._timeout = timeout

    def _headers(self) -> dict[str, str]:
        return {"X-API-Key": self._api_key, "Content-Type": "application/json"}

    async def submit(self, request: JobRequest) -> JobHandle:
        body: dict = {
            "name": request.name,
            "payload": dict(request.payload),
            "priority": request.priority,
            "max_retries": request.max_retries,
            "timeout_seconds": request.timeout_seconds,
        }
        if request.schedule_at:
            body["scheduled_at"] = request.schedule_at.isoformat()

        if request.callback_url or self._execute_url:
            execute_url = request.callback_url or self._execute_url
            body["executor_type"] = "webhook"
            body["payload"] = {
                "url": execute_url,
                "method": "POST",
                "body": request.payload,
            }
        else:
            body["executor_type"] = "python"

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                f"{self._base_url}/v1/tasks",
                json=body,
                headers=self._headers(),
            )
            response.raise_for_status()
            data = response.json()

        state = _ATLAS_STATE_MAP.get(data.get("status", "queued"), JobState.QUEUED)
        return JobHandle(job_id=data["id"], state=state)

    async def get_status(self, job_id: str) -> JobStatus:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.get(
                f"{self._base_url}/v1/tasks/{job_id}",
                headers=self._headers(),
            )
            response.raise_for_status()
            data = response.json()

        state = _ATLAS_STATE_MAP.get(data.get("status", "failed"), JobState.FAILED)
        return JobStatus(
            job_id=job_id,
            state=state,
            name=data.get("name", ""),
            result=data.get("result"),
            error=data.get("error"),
        )

    async def cancel(self, job_id: str) -> JobStatus:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                f"{self._base_url}/v1/tasks/{job_id}/cancel",
                headers=self._headers(),
            )
            response.raise_for_status()
            data = response.json()

        state = _ATLAS_STATE_MAP.get(data.get("status", "cancelled"), JobState.CANCELLED)
        return JobStatus(job_id=job_id, state=state, name=data.get("name", ""), error=data.get("error"))


def as_task_queue_port(adapter: AtlasQueueAdapter) -> TaskQueuePort:
    return adapter
