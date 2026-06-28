# ADR-015: Atlas Queue Integration via TaskQueuePort

## Status
Accepted

## Context
Long-running agent workflows should execute asynchronously with retries, scheduling, and distributed workers. Atlas Queue provides these capabilities as an independent task platform.

## Decision
Define `TaskQueuePort` with `JobRequest`/`JobHandle` models (Aether vocabulary). Implement:
- `LocalTaskQueue` (default): inline execution via registered executor
- `AtlasQueueAdapter`: `POST /v1/tasks`, `GET /v1/tasks/{id}`, webhook executor for workflow dispatch

Orchestrator exposes:
- `POST /v1/orchestrate/async` — submit workflow job
- `POST /v1/internal/workflows/execute` — webhook target for Atlas workers
- `POST /v1/internal/jobs/{job_id}/callback` — external completion notifications

Enable with `TASK_QUEUE_BACKEND=atlas` and `ATLAS_QUEUE_URL` / `ATLAS_QUEUE_API_KEY`.

## Consequences
- **Positive**: Retries, scheduling, and worker scaling delegated to Atlas; Aether orchestrator stays focused on agent coordination.
- **Negative**: Webhook tasks require network reachability between Atlas workers and orchestrator.
- **Tradeoff**: Use Atlas webhook executor for dispatch; publish `job.submitted` / `job.completed` on Aether's EventBus for internal consumers.
