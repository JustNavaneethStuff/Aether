# ADR-002: Redis Streams for Events

## Status
Accepted

## Context
Orchestration produces domain events (task started, completed, agent failed) consumed by future evaluation and monitoring services.

## Decision
Publish events to Redis Streams via a shared EventBus abstraction.

## Consequences
- Simple local setup with existing Redis dependency
- Upgrade path to Kafka/NATS without changing event producers
