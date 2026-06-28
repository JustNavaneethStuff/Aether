import httpx
import structlog

from aether_common.contracts.knowledge_acquisition import CrawlHandle, CrawlRequest, KnowledgeAcquisitionPort
from aether_common.contracts.tools import KnowledgeChunk, KnowledgeQuery

logger = structlog.get_logger()


class HttpKnowledgeAcquisition:
    """Calls knowledge-service HTTP API (used by tool-executor and remote clients)."""

    def __init__(self, base_url: str, timeout: float = 30.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    async def trigger_crawl(self, request: CrawlRequest) -> CrawlHandle:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                f"{self._base_url}/v1/acquire",
                json=request.model_dump(mode="json"),
            )
            response.raise_for_status()
            data = response.json()
        return CrawlHandle.model_validate(data)

    async def search(self, query: KnowledgeQuery) -> list[KnowledgeChunk]:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                f"{self._base_url}/v1/search",
                json=query.model_dump(mode="json"),
            )
            response.raise_for_status()
            return [KnowledgeChunk.model_validate(c) for c in response.json()]

    async def get_dataset(self, dataset_id: str, query: KnowledgeQuery | None = None) -> list[KnowledgeChunk]:
        params: dict[str, str | int] = {"dataset_id": dataset_id}
        if query:
            params["q"] = query.query
            params["top_k"] = query.top_k
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.get(f"{self._base_url}/v1/datasets/{dataset_id}", params=params)
            response.raise_for_status()
            return [KnowledgeChunk.model_validate(c) for c in response.json()]


def as_knowledge_port(acquisition: HttpKnowledgeAcquisition) -> KnowledgeAcquisitionPort:
    return acquisition
