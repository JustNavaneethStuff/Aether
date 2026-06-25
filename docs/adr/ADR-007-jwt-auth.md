# ADR-007: JWT Authentication with Optional Enforcement

## Status
Accepted

## Context
Phase 2 requires authentication for enterprise deployments while keeping local development frictionless.

## Decision
Implement JWT-based auth via AuthProvider abstraction. Auth is disabled by default (`AUTH_ENABLED=false`).

## Consequences
- Production can enable auth without code changes
- `POST /v1/auth/token` issues tokens for development and testing
