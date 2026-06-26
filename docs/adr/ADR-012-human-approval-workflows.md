# ADR-012: Human Approval Workflows

## Status
Accepted

## Context
High-risk agent tasks require human oversight before execution in enterprise deployments.

## Decision
Support `requires_approval` on task nodes. Orchestrator pauses workflow, creates approval request, and resumes after approval.

## Consequences
- Workflows can pause at `AWAITING_APPROVAL` status
- Approval APIs exposed via orchestrator and api-gateway
- Disabled by default via `APPROVALS_ENABLED=false`
