from __future__ import annotations

from enum import Enum
from typing import Any

from astra.config import PermissionMode


class PermissionDecision(str, Enum):
    ALLOW = "allow"
    ASK = "ask"
    DENY = "deny"


ALWAYS_ALLOW = frozenset({"file_read", "glob", "grep"})
ALWAYS_ASK_DEFAULT = frozenset({"bash", "file_write", "file_edit"})


class PermissionChecker:
    def __init__(self, mode: PermissionMode) -> None:
        self.mode = mode

    def check(self, tool_name: str, tool_input: dict[str, Any]) -> PermissionDecision:
        if self.mode == PermissionMode.BYPASS:
            return PermissionDecision.ALLOW
        if tool_name in ALWAYS_ALLOW:
            return PermissionDecision.ALLOW
        # MCP tools: treat like write tools
        if tool_name.startswith("mcp__"):
            if self.mode == PermissionMode.AUTO:
                return PermissionDecision.ALLOW
            return PermissionDecision.ASK
        if self.mode == PermissionMode.AUTO:
            return PermissionDecision.ALLOW
        if tool_name in ALWAYS_ASK_DEFAULT:
            return PermissionDecision.ASK
        return PermissionDecision.ALLOW
