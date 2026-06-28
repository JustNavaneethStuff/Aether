# ADR-016: Argus Integration via KnowledgeAcquisitionPort

## Status
Accepted

## Context
Agents need external knowledge acquisition (web crawls) and structured datasets for RAG. Argus is a separate crawler/ETL platform with its own scheduler and search API.

## Decision
Define `KnowledgeAcquisitionPort` with `CrawlRequest`/`CrawlHandle` models. Implement:
- `LocalKnowledgeAcquisition` (default): in-process search via injected function; no-op crawl with `knowledge.acquisition.requested` event
- `HttpKnowledgeAcquisition`: calls knowledge-service `/v1/search` and `/v1/acquire` (tool-executor path)
- `ArgusKnowledgeAcquisition`: scheduler `POST /jobs`, API `GET /search`

Knowledge-service routes search/acquire through the port. Tool-executor adds `web_crawl` tool using the same port.

Enable with `KNOWLEDGE_BACKEND=argus` and `ARGUS_API_URL` / `ARGUS_SCHEDULER_URL`.

## Consequences
- **Positive**: Argus treated as external microservice; continuous crawl schedules managed by Argus; Aether consumes results via API.
- **Negative**: Argus-indexed content is not automatically ingested into knowledge-service Postgres without a future sync pipeline.
- **Tradeoff**: Command path (trigger crawl) via HTTP; `knowledge.updated` events for local ingestion; future Argus→Aether webhook ingestion as a separate adapter.
