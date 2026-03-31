from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, ClassVar

from astra.permissions.checker import PermissionChecker, PermissionDecision
from astra.types import ToolResult


class Tool(ABC):
    """Base class for all Astra tools."""

    name: ClassVar[str]
    description: ClassVar[str]
    input_schema: ClassVar[dict[str, Any]]
    is_read_only: ClassVar[bool] = False

    @abstractmethod
    async def call(self, *, tool_input: dict[str, Any], cwd: str) -> ToolResult:
        """Execute the tool and return a result."""
        ...

    def check_permissions(
        self, tool_input: dict[str, Any], checker: PermissionChecker
    ) -> PermissionDecision:
        if self.is_read_only:
            return PermissionDecision.ALLOW
        return checker.check(self.name, tool_input)

    def to_anthropic_schema(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
        }
