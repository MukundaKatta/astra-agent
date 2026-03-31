from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class StopReason(str, Enum):
    END_TURN = "end_turn"
    MAX_TOKENS = "max_tokens"
    TOOL_USE = "tool_use"
    MAX_TURNS = "max_turns"
    ABORT = "abort"


@dataclass(frozen=True)
class ToolResult:
    """Result returned by every tool call."""

    output: str
    is_error: bool = False

    def truncated(self, max_chars: int = 100_000) -> ToolResult:
        if len(self.output) <= max_chars:
            return self
        return ToolResult(
            output=self.output[:max_chars] + "\n... (output truncated)",
            is_error=self.is_error,
        )


@dataclass(frozen=True)
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0

    def __add__(self, other: Usage) -> Usage:
        return Usage(
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
            cache_creation_input_tokens=self.cache_creation_input_tokens
            + other.cache_creation_input_tokens,
            cache_read_input_tokens=self.cache_read_input_tokens
            + other.cache_read_input_tokens,
        )


# Stream events yielded by the query loop
StreamEvent = dict[str, Any]
