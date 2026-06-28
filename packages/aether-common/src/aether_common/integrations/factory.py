from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING

from aether_common.contracts.knowledge_acquisition import KnowledgeAcquisitionPort
from aether_common.contracts.task_queue import JobRequest, JobResult, TaskQueuePort
from aether_common.contracts.tools import KnowledgeChunk, KnowledgeQuery
from aether_common.integrations.knowledge.argus import ArgusKnowledgeAcquisition
from aether_common.integrations.knowledge.http import HttpKnowledgeAcquisition
from aether_common.integrations.knowledge.local import LocalKnowledgeAcquisition
from aether_common.integrations.task_queue.atlas import AtlasQueueAdapter
from aether_common.integrations.task_queue.local import LocalTaskQueue
from aether_common.infrastructure.redis_clients import EventBus

if TYPE_CHECKING:
    from aether_common.config.settings import BaseServiceSettings

SearchFn = Callable[[KnowledgeQuery], Awaitable[list[KnowledgeChunk]]]
JobExecutor = Callable[[JobRequest], Awaitable[JobResult]]


def build_task_queue(
    settings: "BaseServiceSettings",
    executor: JobExecutor | None = None,
) -> TaskQueuePort:
    backend = settings.task_queue_backend.lower()
    if backend == "atlas":
        return AtlasQueueAdapter(
            base_url=settings.atlas_queue_url,
            api_key=settings.atlas_queue_api_key,
            execute_url=settings.atlas_callback_url or None,
        )
    queue = LocalTaskQueue(executor=executor)
    return queue


def build_knowledge_acquisition(
    settings: "BaseServiceSettings",
    search_fn: SearchFn | None = None,
    event_bus: EventBus | None = None,
) -> KnowledgeAcquisitionPort:
    backend = settings.knowledge_backend.lower()
    if backend == "argus":
        return ArgusKnowledgeAcquisition(
            api_url=settings.argus_api_url,
            scheduler_url=settings.argus_scheduler_url,
        )
    if search_fn is not None:
        return LocalKnowledgeAcquisition(search_fn=search_fn, event_bus=event_bus)
    if settings.knowledge_service_url:
        return HttpKnowledgeAcquisition(base_url=settings.knowledge_service_url)
    return LocalKnowledgeAcquisition(search_fn=search_fn, event_bus=event_bus)
