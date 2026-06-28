from importlib import metadata
from typing import Any

from aether_common.contracts.tools import ToolDefinition, ToolResult


class PluginRegistry:
    """Discover and load agent/tool plugins via Python entry points."""

    ENTRY_POINT_GROUP = "aether.plugins"

    def __init__(self) -> None:
        self._plugins: dict[str, Any] = {}

    def discover(self) -> dict[str, Any]:
        try:
            eps = metadata.entry_points(group=self.ENTRY_POINT_GROUP)
        except TypeError:
            eps = metadata.entry_points().get(self.ENTRY_POINT_GROUP, [])

        for ep in eps:
            self._plugins[ep.name] = ep.load()
        return self._plugins

    def get(self, name: str) -> Any | None:
        return self._plugins.get(name)

    def list_plugins(self) -> list[str]:
        return list(self._plugins.keys())


class BuiltinTools:
    """Built-in tools available to the tool-executor agent."""

    @staticmethod
    def calculator(arguments: dict[str, Any], _context: dict[str, Any]) -> ToolResult:
        expression = arguments.get("expression", "0")
        try:
            # Safe eval for basic math only
            allowed = set("0123456789+-*/(). ")
            if not all(c in allowed for c in expression):
                raise ValueError("Invalid characters in expression")
            result = eval(expression, {"__builtins__": {}}, {})  # noqa: S307
            return ToolResult(
                call_id=arguments.get("call_id", ""),
                tool_name="calculator",
                success=True,
                output=result,
            )
        except Exception as exc:
            return ToolResult(
                call_id=arguments.get("call_id", ""),
                tool_name="calculator",
                success=False,
                error=str(exc),
            )

    @staticmethod
    def get_definitions() -> list[ToolDefinition]:
        return [
            ToolDefinition(
                name="calculator",
                description="Evaluate a mathematical expression",
                parameters={"expression": "string"},
            ),
            ToolDefinition(
                name="knowledge_search",
                description="Search the knowledge base for relevant documents",
                parameters={"query": "string", "top_k": "integer"},
            ),
            ToolDefinition(
                name="web_crawl",
                description="Trigger a web crawl to acquire external knowledge",
                parameters={
                    "seed_urls": "array",
                    "max_depth": "integer",
                    "allowed_domains": "array",
                    "incremental": "boolean",
                },
            ),
        ]
