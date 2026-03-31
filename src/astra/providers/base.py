"""Base LLM provider interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator


class LLMProvider(ABC):
    """Abstract interface for LLM providers."""

    @abstractmethod
    async def stream_message(
        self,
        *,
        model: str,
        system_prompt: str | list[dict],
        messages: list[dict[str, Any]],
        tools: list[dict] | None = None,
        max_tokens: int = 16384,
        thinking: bool = False,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Stream a message response. Yields raw provider events."""
        ...

    @abstractmethod
    def name(self) -> str:
        """Provider name."""
        ...
