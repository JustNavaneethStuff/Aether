from typing import Any, Protocol
from uuid import UUID

from pydantic import BaseModel, Field

from aether_common.contracts.tools import KnowledgeChunk, KnowledgeQuery


class CrawlRequest(BaseModel):
    seed_urls: list[str] = Field(default_factory=list)
    max_depth: int = 1
    allowed_domains: list[str] = Field(default_factory=list)
    incremental: bool = False
    conversation_id: UUID | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class CrawlHandle(BaseModel):
    crawl_id: str
    status: str = "pending"
    source: str = "local"


class KnowledgeAcquisitionPort(Protocol):
    async def trigger_crawl(self, request: CrawlRequest) -> CrawlHandle: ...

    async def search(self, query: KnowledgeQuery) -> list[KnowledgeChunk]: ...

    async def get_dataset(self, dataset_id: str, query: KnowledgeQuery | None = None) -> list[KnowledgeChunk]: ...
