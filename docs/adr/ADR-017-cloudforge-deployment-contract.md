# ADR-017: CloudForge Deployment Contract

## Status
Accepted

## Context
All ecosystem services should deploy to AWS via Infrastructure-as-Code. CloudForge owns Terraform, ECS Fargate, and CI/CD pipelines.

## Decision
Aether does **not** embed production IaC. Instead, Aether publishes a deployment contract ([`docs/deployment/cloudforge-integration.md`](../deployment/cloudforge-integration.md)) specifying:
- Per-service Docker image build args and ports
- `/health`, `/ready` (where applicable), `/metrics` endpoints
- 12-factor environment variable configuration
- Networking and scaling guidance for CloudForge modules

CloudForge consumes Aether container images and provisions AWS infrastructure independently.

## Consequences
- **Positive**: Clear ownership boundary; no circular dependency; Aether remains runnable via Docker Compose locally.
- **Negative**: Production topology changes require coordination between Aether (image/contract) and CloudForge (Terraform).
- **Tradeoff**: Aether documents the contract; CloudForge implements it — neither project tightly couples to the other's codebase.
