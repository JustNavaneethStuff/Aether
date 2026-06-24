# ADR-001: Microservices Architecture

## Status
Accepted

## Context
Aether orchestrates multiple AI agents with independent scaling, deployment, and replacement requirements.

## Decision
Use microservices from day one with HTTP sync communication and Redis for registry/events.

## Consequences
- Higher local dev complexity (mitigated via Docker Compose)
- Agents are independently replaceable without orchestrator changes
- Each service scales independently in production
