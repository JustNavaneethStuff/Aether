# Aether Demos

Reproducible walkthroughs for Aether's core flows. Each demo is a runnable script under [`scripts/demos/`](../../scripts/demos/).

## Prerequisites

```bash
cp .env.example .env
make up          # core services
make up-obs      # optional: Prometheus + Grafana for demo 4
```

## Run all demos

```bash
# Linux / macOS / Git Bash
bash scripts/demos/run-all.sh

# Windows PowerShell
.\scripts\demos\run-all.ps1

# Makefile shortcut
make demo
```

---

## 1. End-to-end orchestration

**What it shows:** A request flowing through the API Gateway, orchestrator, planner, and specialized agents with SSE streaming.

```bash
bash scripts/demos/01-orchestration.sh
```

**Steps performed:**
1. `GET /health` on the gateway
2. `POST /v1/conversations` — create a conversation
3. `GET /v1/agents` — list replaceable registered agents
4. `POST /v1/conversations/{id}/messages` — send a message and stream SSE events
5. `GET /v1/conversations/{id}/messages` — verify persisted messages

**Expected SSE events** (streamed from response-builder):

```
event: task.started
data: {"agent": "planner", ...}

event: task.completed
data: {"agent": "planner", ...}

event: message
data: {"content": "...", ...}
```

---

## 2. Async workflows (Atlas Queue integration)

**What it shows:** Submitting a workflow as a background job. With the default `TASK_QUEUE_BACKEND=local`, execution runs inline and returns immediately with `state: completed`.

```bash
bash scripts/demos/02-async-workflow.sh
```

**Steps performed:**
1. Create a conversation via the gateway
2. `POST /v1/orchestrate/async` on the orchestrator

**Example response:**

```json
{
  "conversation_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "job_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "state": "completed",
  "result": {
    "conversation_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "final_response": "...",
    "paused": false
  }
}
```

**With Atlas Queue** (`TASK_QUEUE_BACKEND=atlas`):

```bash
export TASK_QUEUE_BACKEND=atlas
export ATLAS_QUEUE_URL=http://localhost:9000
export ATLAS_QUEUE_API_KEY=dev-api-key
export ATLAS_CALLBACK_URL=http://orchestrator:8001/v1/internal/workflows/execute
```

Atlas workers dispatch the workflow via webhook; completion is reported on `POST /v1/internal/jobs/{job_id}/callback` and published as `job.completed` on the Redis event stream.

---

## 3. Knowledge acquisition (Argus integration)

**What it shows:** Ingesting documents, hybrid search, triggering a crawl, and retrieving datasets for RAG.

```bash
bash scripts/demos/03-knowledge-acquisition.sh
```

**Steps performed:**
1. `POST /v1/knowledge/documents` — ingest a document
2. `POST /v1/knowledge/search` — hybrid embedding + TF-IDF search
3. `POST /v1/acquire` — trigger crawl (local backend accepts and emits `knowledge.acquisition.requested`)
4. `GET /v1/datasets/{crawl_id}` — retrieve dataset chunks

**Example acquire response (local backend):**

```json
{
  "crawl_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "status": "accepted",
  "source": "local"
}
```

**With Argus** (`KNOWLEDGE_BACKEND=argus`):

```bash
export KNOWLEDGE_BACKEND=argus
export ARGUS_API_URL=http://localhost:8000
export ARGUS_SCHEDULER_URL=http://localhost:8001
```

Crawl jobs appear in Argus's scheduler; search results come from Argus's indexed pages.

The `web_crawl` tool on `agent-tool-executor` uses the same `KnowledgeAcquisitionPort` — agents can trigger crawls from within workflows.

---

## 4. Observability

**What it shows:** Health/readiness probes, Prometheus metrics, and Grafana dashboards for CloudForge-style deployments.

```bash
make up-obs
bash scripts/demos/04-observability.sh
```

**Endpoints verified:**
- `GET /health` and `GET /ready` on orchestrator
- `GET /metrics` — Prometheus exposition format

**Grafana** (http://localhost:3000, admin/admin):

| Panel | Metric |
|-------|--------|
| Agent execution latency | `aether_agent_execution_seconds` |
| LLM token usage | `aether_llm_tokens_total` |
| Cost trends | `aether_llm_cost_usd_total` |
| Approval throughput | `aether_approval_requests_total` |

Run a workflow (demo 1) while Grafana is open to see metrics update in real time.

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `Connection refused` on :8000 | Run `make up` and wait for health checks |
| Empty agent list | Agents register on startup; check `docker compose logs agent-planner` |
| Prometheus unreachable | Run `make up-obs` (observability profile) |
| Async job stays `queued` with Atlas | Ensure Atlas Queue is running and `ATLAS_QUEUE_API_KEY` is set |
