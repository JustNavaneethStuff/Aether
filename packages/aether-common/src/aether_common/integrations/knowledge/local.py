from collections.abc import Awaitable, Callable
from uuid import uuid4

import structlog

from aether_common.contracts.knowledge_acquisition import CrawlHandle, CrawlRequest, KnowledgeAcquisitionPort
from aether_common.contracts.tools import KnowledgeChunk, KnowledgeQuery
from aether_common.infrastructure.redis_clients import EventBus

logger = structlog.get_logger()

SearchFn = Callable[[KnowledgeQuery], Awaitable[list[KnowledgeChunk]]]


class LocalKnowledgeAcquisition:
    """Default knowledge acquisition: in-process search with no-op crawl trigger."""

    def __init__(
        self,
        search_fn: SearchFn | None = None,
        event_bus: EventBus | None = None,
    ) -> None:
        self._search_fn = search_fn
        self._event_bus = event_bus
        self._crawls: dict[str, CrawlHandle] = {}

    async def trigger_crawl(self, request: CrawlRequest) -> CrawlHandle:
        crawl_id = str(uuid4())
        handle = CrawlHandle(crawl_id=crawl_id, status="accepted", source="local")
        self._crawls[crawl_id] = handle

        if self._event_bus:
            await self._event_bus.publish(
                "knowledge.acquisition.requested",
                {
                    "crawl_id": crawl_id,
                    "seed_urls": request.seed_urls,
                    "conversation_id": str(request.conversation_id) if request.conversation_id else None,
                },
            )
        logger.info("local_crawl_requested", crawl_id=crawl_id, seeds=len(request.seed_urls))
        return handle

    async def search(self, query: KnowledgeQuery) -> list[KnowledgeChunk]:
        if self._search_fn is None:
            return []
        return await self._search_fn(query)

    async def get_dataset(self, dataset_id: str, query: KnowledgeQuery | None = None) -> list[KnowledgeChunk]:
        search_query = query or KnowledgeQuery(query="", top_k=50)
        chunks = await self.search(search_query)
        return [c for c in chunks if c.metadata.get("dataset_id") == dataset_id or dataset_id in c.content]


def as_knowledge_port(acquisition: LocalKnowledgeAcquisition) -> KnowledgeAcquisitionPort:
    return acquisition
