"""Factory for creating standard agent service pyproject.toml content."""

AGENT_DEPS = """
dependencies = [
    "aether-common",
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.34.0",
    "openai>=1.59.0",
    "anthropic>=0.42.0",
    "redis>=5.2.0",
]
"""
