# ADR-013: Cost Tracking

## Status
Accepted

## Context
Phase 3 requires token and cost visibility per conversation and agent without external billing integration.

## Decision
Record LLM usage in `memory-service` with local pricing map in `aether-common`. Unknown models flag `pricing_unknown=true`.

## Consequences
- Cost summaries available via API without cloud billing APIs
- Pricing table is configurable and extensible per provider/model
