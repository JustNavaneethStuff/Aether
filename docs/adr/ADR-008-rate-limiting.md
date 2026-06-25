# ADR-008: Redis Sliding-Window Rate Limiting

## Status
Accepted

## Context
API gateway needs protection against abuse without adding a separate rate-limiting service.

## Decision
Implement sliding-window rate limiting in api-gateway using Redis sorted sets.

## Consequences
- Per-client limits via IP or X-API-Key header
- Returns 429 with X-RateLimit-Remaining header
