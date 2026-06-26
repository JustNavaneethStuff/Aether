# ADR-011: Prompt Versioning

## Status
Accepted

## Context
Agents need reproducible prompts with version history for experimentation and debugging.

## Decision
Create `prompt-registry` service with versioned templates, active version management, and variable rendering.

## Consequences
- Agents can fall back to local prompts if registry is unavailable
- Prompt versions are auditable and swappable without redeploying agents
