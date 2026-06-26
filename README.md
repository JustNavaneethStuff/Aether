# Aether

Enterprise-grade AI orchestration platform that coordinates multiple specialized agents to solve complex tasks.

## Architecture

```
Client → API Gateway → Orchestrator → Specialized Agents → Memory Layer → PostgreSQL / Redis
                              ↓
                      Response Builder (SSE streaming)
```

Aether is **not a chatbot**. It is a microservices-based orchestration engine with replaceable agents, conversation persistence, task decomposition, and full observability.

## Tech Stack

- Python 3.13, FastAPI, SQLAlchemy, Pydantic
- PostgreSQL, Redis
- OpenTelemetry, Prometheus, Grafana
- Docker Compose, GitHub Actions, uv, Ruff, mypy, pytest

## Quick Start

### Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/)
- Docker & Docker Compose

### Local Development

```bash
cp .env.example .env
# Optional: set OPENAI_API_KEY or ANTHROPIC_API_KEY (falls back to mock LLM)

make install
make test
make up
```

### API Usage

```bash
# Create conversation
curl -X POST http://localhost:8000/v1/conversations -H "Content-Type: application/json" -d "{}"

# Send message (SSE stream)
curl -N -X POST http://localhost:8000/v1/conversations/{id}/messages \
  -H "Content-Type: application/json" \
  -d '{"content": "Analyze the tradeoffs between microservices and modular monoliths"}'

# List registered agents
curl http://localhost:8000/v1/agents
```

## Phase 2 Features

- **Tool calling** — `agent-tool-executor` with calculator and knowledge_search tools
- **Vector search / RAG** — `knowledge-service` with hybrid embedding + TF-IDF search
- **Checkpointing** — workflow state saved after each agent; resume via `POST /v1/conversations/{id}/resume`
- **Rate limiting** — Redis sliding-window in api-gateway (60 req/min default)
- **Authentication** — optional JWT auth (`AUTH_ENABLED=true`)
- **Agent communication** — Redis pub/sub agent bus per conversation
- **Plugin system** — entry-point based PluginRegistry for extensible tools

### Phase 2 API Additions

```
POST   /v1/auth/token
POST   /v1/knowledge/documents
POST   /v1/knowledge/search
POST   /v1/conversations/{id}/resume
GET    /v1/tools
POST   /v1/orchestrate/resume          (orchestrator)
GET    /v1/workflows/{id}/checkpoint     (orchestrator)
```

## Phase 3 Features

- **Evaluation engine** — rule-based workflow scoring via `evaluation-service`
- **Prompt versioning** — versioned templates with render API via `prompt-registry`
- **Experiment tracking** — experiment definitions and conversation variant assignments
- **Cost tracking** — LLM usage records with local pricing estimates
- **Human approval workflows** — pause/resume on `requires_approval` task nodes
- **Agent performance dashboards** — Grafana Phase 3 dashboard for latency, cost, evaluations, approvals

### Phase 3 API Additions

```
POST   /v1/evaluations/run
GET    /v1/evaluations/{conversation_id}
GET    /v1/evaluations/summary
POST   /v1/prompts
GET    /v1/prompts/{agent_name}
POST   /v1/prompts/render
GET    /v1/usage/cost-summary
GET    /v1/experiments
GET    /v1/approvals/pending
POST   /v1/approvals/{id}/approve
POST   /v1/approvals/{id}/reject
```

## Services

| Service | Port | Description |
|---------|------|-------------|
| api-gateway | 8000 | Public REST API + SSE |
| orchestrator | 8001 | Task graph execution |
| memory-service | 8002 | Conversation persistence |
| response-builder | 8003 | Response aggregation + streaming |
| knowledge-service | 8004 | Vector search + RAG |
| evaluation-service | 8005 | Workflow evaluation + scoring |
| prompt-registry | 8006 | Prompt versioning + rendering |
| agent-planner | 8010 | Task decomposition |
| agent-research | 8011 | Research agent |
| agent-critic | 8012 | Critique agent |
| agent-summarizer | 8013 | Summarization agent |

## Project Structure

```
packages/aether-common/     Shared domain models, contracts, LLM adapters
services/api-gateway/       Edge API
services/orchestrator/      Workflow coordination
services/memory-service/    Persistence layer
services/response-builder/  Streaming response builder
services/agents/            Replaceable specialized agents
docker/                     Docker Compose + Dockerfile
monitoring/                 Prometheus, Grafana, OTEL configs
docs/                       Architecture docs and ADRs
tests/                      Integration and performance tests
```

## Observability

```bash
make up-obs   # Starts Prometheus (9090) and Grafana (3000)
```

## Development

```bash
make lint
make format
make typecheck
make test
```

## License

MIT
