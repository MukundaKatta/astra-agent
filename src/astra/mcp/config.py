from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class MCPServerConfig:
    transport: str  # "stdio" | "sse" | "http"
    command: str = ""
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    url: str = ""
    headers: dict[str, str] = field(default_factory=dict)


def load_mcp_configs(config_paths: tuple[str, ...]) -> dict[str, MCPServerConfig]:
    """Load MCP server configs from .mcp.json files and ~/.astra/config.json."""
    servers: dict[str, MCPServerConfig] = {}

    default_paths = [
        Path.cwd() / ".mcp.json",
        Path.home() / ".astra" / "config.json",
    ]
    all_paths = [Path(p) for p in config_paths] + default_paths

    for path in all_paths:
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text())
            mcp_servers = data.get("mcpServers", data.get("mcp_servers", {}))
            for name, cfg in mcp_servers.items():
                if name not in servers:  # first wins
                    servers[name] = _parse_server_config(cfg)
        except Exception:
            pass

    return servers


def _parse_server_config(cfg: dict[str, Any]) -> MCPServerConfig:
    if "command" in cfg:
        return MCPServerConfig(
            transport="stdio",
            command=cfg["command"],
            args=cfg.get("args", []),
            env=cfg.get("env", {}),
        )
    elif "url" in cfg:
        transport = cfg.get("type", "sse")
        return MCPServerConfig(
            transport=transport,
            url=cfg["url"],
            headers=cfg.get("headers", {}),
        )
    raise ValueError(f"Cannot determine transport for MCP config: {cfg}")
