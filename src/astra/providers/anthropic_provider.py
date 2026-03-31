"""Anthropic Claude provider — primary provider using the native SDK."""

from __future__ import annotations

from typing import Any, AsyncGenerator

import anthropic

from astra.providers.base import LLMProvider


class AnthropicProvider(LLMProvider):
    """Provider for Anthropic Claude models."""

    def __init__(self, client: anthropic.AsyncAnthropic | None = None) -> None:
        self.client = client or anthropic.AsyncAnthropic()

    def name(self) -> str:
        return "anthropic"

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
        api_params: dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "system": system_prompt,
            "messages": messages,
        }
        if tools:
            api_params["tools"] = tools
        if thinking:
            api_params["thinking"] = {"type": "enabled", "budget_tokens": 10000}

        async with self.client.messages.stream(**api_params) as stream:
            async for event in stream:
                yield {"raw_event": event}

            final_message = await stream.get_final_message()
            yield {"final_message": final_message}
