# ADR-010: Evaluation Service

## Status
Accepted

## Context
Phase 3 requires automated quality assessment of multi-agent workflows without mandating an LLM judge.

## Decision
Create a dedicated `evaluation-service` that consumes Redis Stream events and applies deterministic rubric scoring.

## Consequences
- Reliable offline evaluation without API keys
- Optional LLM evaluator can be added later without changing producers
