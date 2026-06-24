# ADR-004: Agent Registry Pattern

## Status
Accepted

## Context
Agents must be independently deployable and replaceable without modifying the orchestrator.

## Decision
Agents self-register in Redis on startup with name, URL, and capabilities. Orchestrator resolves agents dynamically.

## Consequences
- Adding an agent requires a new service + compose entry only
- Orchestrator contains zero agent-specific routing logic
