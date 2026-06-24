# ADR-003: Provider-Agnostic LLM Abstraction

## Status
Accepted

## Context
Different agents may use different LLM providers; Phase 3 requires cost and latency comparison.

## Decision
Define LLMProvider protocol in aether-common with OpenAI and Anthropic adapters plus MockLLM fallback.

## Consequences
- Agents depend on abstraction, not vendor SDKs directly
- Development works without API keys via mock provider
