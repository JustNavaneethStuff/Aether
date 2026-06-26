"""Local LLM pricing map for cost estimation (USD per 1M tokens)."""

PRICING_PER_MILLION: dict[str, dict[str, dict[str, float]]] = {
    "openai": {
        "gpt-4o": {"input": 2.50, "output": 10.00},
        "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    },
    "anthropic": {
        "claude-3-5-haiku-latest": {"input": 0.80, "output": 4.00},
        "claude-3-5-sonnet-latest": {"input": 3.00, "output": 15.00},
    },
    "mock": {
        "mock": {"input": 0.0, "output": 0.0},
    },
}


def estimate_cost_usd(
    provider: str,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
) -> tuple[float, bool]:
    provider_prices = PRICING_PER_MILLION.get(provider, {})
    model_prices = provider_prices.get(model)
    if not model_prices:
        return 0.0, True

    input_cost = (prompt_tokens / 1_000_000) * model_prices["input"]
    output_cost = (completion_tokens / 1_000_000) * model_prices["output"]
    return round(input_cost + output_cost, 6), False
