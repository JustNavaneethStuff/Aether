# ADR-009: Hybrid Vector + TF-IDF Search

## Status
Accepted

## Context
Phase 2 requires knowledge retrieval without mandating external vector databases or paid embedding APIs.

## Decision
knowledge-service combines hash-based embeddings with TF-IDF scoring, upgradeable to OpenAI embeddings in Phase 3.

## Consequences
- Works offline without API keys
- Hybrid scoring improves recall over either method alone
