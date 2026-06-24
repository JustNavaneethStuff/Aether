# ADR-005: memory-service as Migration Owner

## Status
Accepted

## Context
Multiple services need PostgreSQL access; uncoordinated migrations cause conflicts.

## Decision
memory-service owns all Alembic migrations and database schema for Phase 1.

## Consequences
- Single source of truth for persistence schema
- Other services access data via memory-service HTTP API
