from uuid import uuid4

import httpx
import structlog

from aether_common.contracts.knowledge_acquisition import CrawlHandle, CrawlRequest, KnowledgeAcquisitionPort
from aether_common.contracts.tools import KnowledgeChunk, KnowledgeQuery

logger = structlog.get_logger()


class ArgusKnowledgeAcquisition:
    """HTTP adapter for Argus crawler and search APIs. Not selected by default."""

    def __init__(
        self,
        api_url: str,
        scheduler_url: str,
        timeout: float = 60.0,
    ) -> None:
        self._api_url = api_url.rstrip("/")
        self._scheduler_url = scheduler_url.rstrip("/")
        self._timeout = timeout

    async def trigger_crawl(self, request: CrawlRequest) -> CrawlHandle:
        body = {
            "seed_urls": request.seed_urls,
            "max_depth": request.max_depth,
            "incremental": request.incremental,
        }
        if request.allowed_domains:
            body["allowed_domains"] = request.allowed_domains

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                f"{self._scheduler_url}/jobs",
                json=body,
            )
            response.raise_for_status()
            data = response.json()

        job_id = str(data.get("id") or data.get("job_id") or uuid4())
        return CrawlHandle(crawl_id=job_id, status=data.get("status", "queued"), source="argus")

    async def search(self, query: KnowledgeQuery) -> list[KnowledgeChunk]:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.get(
                f"{self._api_url}/search",
                params={"q": query.query, "limit": query.top_k},
            )
            response.raise_for_status()
            data = response.json()

        results = data if isinstance(data, list) else data.get("results", data.get("items", []))
        chunks: list[KnowledgeChunk] = []
        for item in results:
            if isinstance(item, dict):
                content = item.get("content") or item.get("title") or item.get("url", "")
                score = float(item.get("score", item.get("rank", 0.5)))
                chunks.append(KnowledgeChunk(content=str(content), score=score, metadata=item))
            else:
                chunks.append(KnowledgeChunk(content=str(item), score=0.5))
        return chunks[: query.top_k]

    async def get_dataset(self, dataset_id: str, query: KnowledgeQuery | None = None) -> list[KnowledgeChunk]:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.get(f"{self._api_url}/jobs/{dataset_id}")
            response.raise_for_status()
            job_data = response.json()

        search_query = query or KnowledgeQuery(query=dataset_id, top_k=20)
        chunks = await self.search(search_query)
        for chunk in chunks:
            chunk.metadata["job_id"] = dataset_id
            chunk.metadata["job"] = job_data
        return chunks


def as_knowledge_port(acquisition: ArgusKnowledgeAcquisition) -> KnowledgeAcquisitionPort:
    return acquisition
