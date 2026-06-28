# ADR-014: Anti-Corruption Adapter Layer for Ecosystem Services

## Status
Accepted

## Context
Aether is part of a larger engineering ecosystem (Atlas Queue, Argus, CloudForge). These projects must remain independently deployable, testable, and free of circular dependencies.

## Decision
Introduce Protocol-based ports in `aether-common/contracts/` and HTTP adapters in `aether-common/integrations/`. A config-driven factory (`build_task_queue`, `build_knowledge_acquisition`) selects implementations via environment variables. Defaults use local/no-op adapters so Aether runs without sibling services.

## Consequences
- **Positive**: No imports from sibling repositories; adapters swappable per environment; tests use in-memory fakes.
- **Negative**: Thin indirection layer and mapping code between Aether domain models and external APIs.
- **Tradeoff**: Prefer explicit HTTP command paths and Aether's own `EventBus` for completion fan-out over sharing a message broker across repos.
