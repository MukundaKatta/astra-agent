from __future__ import annotations

from astra.tools.base import Tool


class ToolRegistry:
    """Registry of all available tools."""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def all_tools(self) -> list[Tool]:
        return list(self._tools.values())

    def to_anthropic_schemas(self) -> list[dict]:
        return [t.to_anthropic_schema() for t in self._tools.values()]


def build_default_registry() -> ToolRegistry:
    """Create registry with all built-in tools."""
    from astra.tools.bash import BashTool
    from astra.tools.file_edit import FileEditTool
    from astra.tools.file_read import FileReadTool
    from astra.tools.file_write import FileWriteTool
    from astra.tools.glob import GlobTool
    from astra.tools.grep import GrepTool

    registry = ToolRegistry()
    for tool_cls in [BashTool, FileReadTool, FileWriteTool, FileEditTool, GrepTool, GlobTool]:
        registry.register(tool_cls())
    return registry
