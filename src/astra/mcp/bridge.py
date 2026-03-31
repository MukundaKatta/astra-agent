"""MCP tool bridge — wraps MCP server tools as Astra Tool instances."""

from __future__ import annotations

from typing import Any, ClassVar

from astra.mcp.client import MCPConnection, MCPManager
from astra.tools import ToolRegistry
from astra.tools.base import Tool
from astra.types import ToolResult


class MCPBridgeTool(Tool):
    """A tool that proxies calls to an MCP server."""

    is_read_only: ClassVar[bool] = False

    def __init__(
        self,
        *,
        prefixed_name: str,
        tool_description: str,
        schema: dict,
        connection: MCPConnection,
        original_name: str,
    ):
        self._name = prefixed_name
        self._description = tool_description
        self._schema = schema
        self._connection = connection
        self._original_name = original_name

    @property  # type: ignore[override]
    def name(self) -> str:
        return self._name

    @property  # type: ignore[override]
    def description(self) -> str:
        return self._description

    @property  # type: ignore[override]
    def input_schema(self) -> dict[str, Any]:
        return self._schema

    async def call(self, *, tool_input: dict[str, Any], cwd: str) -> ToolResult:
        try:
            output = await self._connection.call_tool(
                self._original_name, tool_input
            )
            return ToolResult(output=output)
        except Exception as e:
            return ToolResult(output=f"MCP tool error: {e}", is_error=True)


def register_mcp_tools(mcp_manager: MCPManager, registry: ToolRegistry) -> None:
    """Register all MCP tools into the tool registry."""
    for conn in mcp_manager.connections.values():
        for tool_info in conn.tools:
            bridge = MCPBridgeTool(
                prefixed_name=tool_info["name"],
                tool_description=tool_info["description"],
                schema=tool_info["input_schema"],
                connection=conn,
                original_name=tool_info["mcp_tool_name"],
            )
            registry.register(bridge)
