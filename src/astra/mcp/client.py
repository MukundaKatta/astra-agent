"""MCP client manager — connects to MCP servers and discovers tools."""

from __future__ import annotations

import sys
from typing import Any

from astra.mcp.config import MCPServerConfig, load_mcp_configs


class MCPConnection:
    """A single MCP server connection."""

    def __init__(self, name: str, session: Any) -> None:
        self.name = name
        self.session = session
        self.tools: list[dict[str, Any]] = []

    async def discover_tools(self) -> list[dict[str, Any]]:
        """List tools from the MCP server."""
        result = await self.session.list_tools()
        self.tools = [
            {
                "name": f"mcp__{self.name}__{tool.name}",
                "description": tool.description or "",
                "input_schema": tool.inputSchema,
                "mcp_server": self.name,
                "mcp_tool_name": tool.name,
            }
            for tool in result.tools
        ]
        return self.tools

    async def call_tool(self, tool_name: str, arguments: dict) -> str:
        """Call a tool on this MCP server."""
        result = await self.session.call_tool(tool_name, arguments=arguments)
        texts = [c.text for c in result.content if hasattr(c, "text")]
        return "\n".join(texts) if texts else str(result.content)


class MCPManager:
    """Manages all MCP server connections."""

    def __init__(self) -> None:
        self.connections: dict[str, MCPConnection] = {}
        self._contexts: list[Any] = []

    async def connect_from_config(self, config_paths: tuple[str, ...]) -> None:
        """Load configs and connect to all MCP servers."""
        configs = load_mcp_configs(config_paths)
        for name, config in configs.items():
            try:
                conn = await self._connect_one(name, config)
                await conn.discover_tools()
                self.connections[name] = conn
            except Exception as e:
                print(
                    f"Warning: Failed to connect MCP server '{name}': {e}",
                    file=sys.stderr,
                )

    async def _connect_one(
        self, name: str, config: MCPServerConfig
    ) -> MCPConnection:
        """Connect to a single MCP server."""
        try:
            from mcp import ClientSession
        except ImportError:
            raise ImportError(
                "MCP package not installed. Install with: pip install mcp"
            )

        if config.transport == "stdio":
            from mcp.client.stdio import stdio_client

            ctx = stdio_client(config.command, config.args, env=config.env or None)
            streams = await ctx.__aenter__()
            self._contexts.append(ctx)
            read_stream, write_stream = streams
            session = ClientSession(read_stream, write_stream)
            await session.initialize()
            return MCPConnection(name, session)

        elif config.transport in ("sse", "http"):
            from mcp.client.sse import sse_client

            ctx = sse_client(config.url, headers=config.headers or None)
            streams = await ctx.__aenter__()
            self._contexts.append(ctx)
            read_stream, write_stream = streams
            session = ClientSession(read_stream, write_stream)
            await session.initialize()
            return MCPConnection(name, session)

        else:
            raise ValueError(f"Unknown MCP transport: {config.transport}")

    def get_all_tools(self) -> list[dict[str, Any]]:
        """Get all discovered tools across all connections."""
        all_tools = []
        for conn in self.connections.values():
            all_tools.extend(conn.tools)
        return all_tools

    def find_connection_for_tool(
        self, prefixed_name: str
    ) -> tuple[MCPConnection, str] | None:
        """Given mcp__server__tool, find the connection and original name."""
        for conn in self.connections.values():
            prefix = f"mcp__{conn.name}__"
            if prefixed_name.startswith(prefix):
                original_name = prefixed_name[len(prefix) :]
                return (conn, original_name)
        return None

    async def disconnect_all(self) -> None:
        for ctx in reversed(self._contexts):
            try:
                await ctx.__aexit__(None, None, None)
            except Exception:
                pass
        self._contexts.clear()
        self.connections.clear()
