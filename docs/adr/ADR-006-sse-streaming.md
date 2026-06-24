# ADR-006: SSE over WebSockets

## Status
Accepted

## Context
Phase 1 requires streaming responses to clients for multi-agent workflow progress.

## Decision
Use Server-Sent Events (SSE) for client streaming via response-builder service.

## Consequences
- Simpler than WebSockets for unidirectional server-to-client streaming
- Works through standard HTTP proxies and load balancers
