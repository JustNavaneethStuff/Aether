# CloudForge Deployment Contract

Aether services are designed for deployment by **CloudForge** (Terraform + ECS Fargate on AWS). Aether does not contain Infrastructure-as-Code for production; CloudForge owns provisioning, CI/CD, and operations.

## Ownership boundary

| Concern | Owner |
|---------|-------|
| Application code, Docker images, health endpoints | Aether |
| Terraform modules, VPC, ECS, RDS, ElastiCache, ALB | CloudForge |
| Container registry push, ECS task rollout | CloudForge CI/CD |
| Runtime secrets (DB URLs, API keys) | AWS Secrets Manager via CloudForge |

This avoids circular dependencies: CloudForge deploys Aether; Aether never imports CloudForge.

## Container images

All services build from [`docker/Dockerfile.service`](../../docker/Dockerfile.service) with build args:

| Build arg | Example |
|-----------|---------|
| `SERVICE_MODULE` | `aether_orchestrator.main:app` |
| `SERVICE_PORT` | `8001` |

Image tagging convention for CloudForge: `aether/<service-name>:<git-sha>` (e.g. `aether/orchestrator:abc1234`).

## Service inventory

| Service | Port | Module | Health | Ready | Metrics |
|---------|------|--------|--------|-------|---------|
| api-gateway | 8000 | `aether_gateway.main:app` | `/health` | — | `/metrics` |
| orchestrator | 8001 | `aether_orchestrator.main:app` | `/health` | `/ready` | `/metrics` |
| memory-service | 8002 | `aether_memory.main:app` | `/health` | `/ready` | `/metrics` |
| response-builder | 8003 | `aether_response_builder.main:app` | `/health` | — | `/metrics` |
| knowledge-service | 8004 | `aether_knowledge.main:app` | `/health` | `/ready` | `/metrics` |
| evaluation-service | 8005 | `aether_evaluation.main:app` | `/health` | — | `/metrics` |
| prompt-registry | 8006 | `aether_prompt_registry.main:app` | `/health` | — | `/metrics` |
| agent-planner | 8010 | `aether_agent_planner.main:app` | `/health` | `/ready` | `/metrics` |
| agent-research | 8011 | `aether_agent_research.main:app` | `/health` | `/ready` | `/metrics` |
| agent-critic | 8012 | `aether_agent_critic.main:app` | `/health` | `/ready` | `/metrics` |
| agent-summarizer | 8013 | `aether_agent_summarizer.main:app` | `/health` | `/ready` | `/metrics` |
| agent-code | 8014 | `aether_agent_code.main:app` | `/health` | `/ready` | `/metrics` |
| agent-data-analysis | 8015 | `aether_agent_data_analysis.main:app` | `/health` | `/ready` | `/metrics` |
| agent-fact-checker | 8016 | `aether_agent_fact_checker.main:app` | `/health` | `/ready` | `/metrics` |
| agent-memory-manager | 8017 | `aether_agent_memory_manager.main:app` | `/health` | `/ready` | `/metrics` |
| agent-tool-executor | 8018 | `aether_agent_tool_executor.main:app` | `/health` | `/ready` | `/metrics` |

## Probe recommendations (ECS)

```hcl
# Liveness — process is up
health_check {
  path                = "/health"
  healthy_threshold   = 2
  unhealthy_threshold = 3
  timeout             = 5
  interval            = 30
}

# Readiness — dependencies available (where /ready exists)
# Use /ready for orchestrator, memory-service, knowledge-service, agents
```

Services without `/ready` should use `/health` for both probes until readiness checks are added.

## 12-factor configuration

All configuration is via environment variables (see [`.env.example`](../../.env.example)). CloudForge should inject:

- `POSTGRES_URL`, `REDIS_URL` — from Secrets Manager / parameter store
- `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `JWT_SECRET` — secrets
- `*_SERVICE_URL` — internal service discovery (ECS service connect or Cloud Map)
- `OTEL_EXPORTER_OTLP_ENDPOINT` — observability collector
- Ecosystem adapters (optional): `TASK_QUEUE_BACKEND`, `KNOWLEDGE_BACKEND`, `ATLAS_QUEUE_*`, `ARGUS_*`

## Observability

- **Metrics**: Prometheus scrape `GET /metrics` on each service port
- **Traces**: OpenTelemetry OTLP export via `OTEL_EXPORTER_OTLP_ENDPOINT`
- **Logs**: Structured JSON to stdout (`LOG_FORMAT=json`)

## Networking

- **Public**: only `api-gateway` behind ALB
- **Private**: all other services in private subnets; inter-service HTTP only
- **Data**: RDS PostgreSQL, ElastiCache Redis in private subnets

## Scaling

| Tier | Scale strategy |
|------|----------------|
| api-gateway, orchestrator | ECS service auto-scaling on CPU/request count |
| agents | Horizontal scale per agent type (independent ECS services) |
| memory, knowledge, evaluation | Scale on connection pool / latency metrics |

## Ecosystem services (external to Aether images)

When enabled via env vars, Aether calls sibling platforms over HTTP — deploy separately:

| Service | Default URL env | Purpose |
|---------|-----------------|---------|
| Atlas Queue | `ATLAS_QUEUE_URL` | Background workflow jobs |
| Argus API | `ARGUS_API_URL` | Search / datasets |
| Argus Scheduler | `ARGUS_SCHEDULER_URL` | Crawl job submission |

Defaults (`local` backends) require no sibling services.
