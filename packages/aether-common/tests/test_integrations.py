import pytest
from aether_common.config.settings import BaseServiceSettings
from aether_common.contracts.knowledge_acquisition import CrawlRequest
from aether_common.contracts.task_queue import JobRequest, JobState
from aether_common.contracts.tools import KnowledgeChunk, KnowledgeQuery
from aether_common.integrations.factory import build_knowledge_acquisition, build_task_queue
from aether_common.integrations.knowledge.local import LocalKnowledgeAcquisition
from aether_common.integrations.task_queue.atlas import AtlasQueueAdapter
from aether_common.integrations.task_queue.local import LocalTaskQueue


@pytest.mark.asyncio
async def test_local_task_queue_executes_inline() -> None:
    executed: list[str] = []

    async def executor(request: JobRequest):
        from aether_common.contracts.task_queue import JobResult

        executed.append(request.name)
        return JobResult(job_id="", success=True, output={"done": True})

    queue = LocalTaskQueue(executor=executor)
    handle = await queue.submit(JobRequest(name="test_job", payload={"key": "value"}))
    status = await queue.get_status(handle.job_id)

    assert executed == ["test_job"]
    assert status.state == JobState.COMPLETED
    assert status.result == {"done": True}


@pytest.mark.asyncio
async def test_local_task_queue_without_executor_completes_immediately() -> None:
    queue = LocalTaskQueue()
    handle = await queue.submit(JobRequest(name="noop"))
    status = await queue.get_status(handle.job_id)
    assert status.state == JobState.COMPLETED


@pytest.mark.asyncio
async def test_local_knowledge_acquisition_search() -> None:
    async def search_fn(query: KnowledgeQuery) -> list[KnowledgeChunk]:
        return [KnowledgeChunk(content=f"result for {query.query}", score=0.9)]

    knowledge = LocalKnowledgeAcquisition(search_fn=search_fn)
    chunks = await knowledge.search(KnowledgeQuery(query="hello", top_k=3))
    assert len(chunks) == 1
    assert "hello" in chunks[0].content


@pytest.mark.asyncio
async def test_local_knowledge_trigger_crawl() -> None:
    knowledge = LocalKnowledgeAcquisition()
    handle = await knowledge.trigger_crawl(CrawlRequest(seed_urls=["https://example.com"]))
    assert handle.crawl_id
    assert handle.source == "local"
    assert handle.status == "accepted"


def test_factory_defaults_to_local_backends() -> None:
    settings = BaseServiceSettings()
    queue = build_task_queue(settings)
    knowledge = build_knowledge_acquisition(settings)
    assert isinstance(queue, LocalTaskQueue)
    from aether_common.integrations.knowledge.http import HttpKnowledgeAcquisition

    # Default knowledge_service_url routes remote clients through HTTP adapter
    assert isinstance(knowledge, HttpKnowledgeAcquisition)


def test_factory_local_with_search_fn() -> None:
    settings = BaseServiceSettings()

    async def search_fn(_query: KnowledgeQuery) -> list[KnowledgeChunk]:
        return []

    knowledge = build_knowledge_acquisition(settings, search_fn=search_fn)
    assert isinstance(knowledge, LocalKnowledgeAcquisition)


def test_factory_selects_atlas_when_configured() -> None:
    settings = BaseServiceSettings(
        task_queue_backend="atlas",
        atlas_queue_url="http://atlas:8000",
        atlas_queue_api_key="test-key",
    )
    queue = build_task_queue(settings)
    assert isinstance(queue, AtlasQueueAdapter)


def test_factory_selects_argus_when_configured() -> None:
    settings = BaseServiceSettings(
        knowledge_backend="argus",
        argus_api_url="http://argus-api:8000",
        argus_scheduler_url="http://argus-scheduler:8001",
    )
    knowledge = build_knowledge_acquisition(settings)
    from aether_common.integrations.knowledge.argus import ArgusKnowledgeAcquisition

    assert isinstance(knowledge, ArgusKnowledgeAcquisition)
