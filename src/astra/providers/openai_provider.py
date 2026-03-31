"""OpenAI-compatible provider — supports OpenAI, Azure, and local models (Ollama, LM Studio)."""

from __future__ import annotations

import json
import os
from typing import Any, AsyncGenerator

from astra.providers.base import LLMProvider


class OpenAIProvider(LLMProvider):
    """
    Provider for OpenAI-compatible APIs.

    Supports:
    - OpenAI (gpt-4o, gpt-4-turbo, etc.)
    - Azure OpenAI
    - Ollama (http://localhost:11434/v1)
    - LM Studio (http://localhost:1234/v1)
    - Any OpenAI-compatible API
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
    ) -> None:
        try:
            from openai import AsyncOpenAI
        except ImportError:
            raise ImportError(
                "openai package required for OpenAI provider. "
                "Install with: pip install openai"
            )

        self._api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self._base_url = base_url or os.environ.get("OPENAI_BASE_URL")
        self.client = AsyncOpenAI(api_key=self._api_key, base_url=self._base_url)

    def name(self) -> str:
        if self._base_url and "localhost" in self._base_url:
            return "local"
        return "openai"

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
        # Convert Anthropic-style messages to OpenAI format
        oai_messages = _convert_messages(system_prompt, messages)

        params: dict[str, Any] = {
            "model": model,
            "messages": oai_messages,
            "max_tokens": max_tokens,
            "stream": True,
        }

        if tools:
            params["tools"] = _convert_tools(tools)

        stream = await self.client.chat.completions.create(**params)

        collected_content = ""
        collected_tool_calls: dict[int, dict] = {}

        async for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if not delta:
                continue

            if delta.content:
                collected_content += delta.content
                yield {"type": "text_delta", "text": delta.content}

            if delta.tool_calls:
                for tc in delta.tool_calls:
                    idx = tc.index
                    if idx not in collected_tool_calls:
                        collected_tool_calls[idx] = {
                            "id": tc.id or "",
                            "name": tc.function.name or "" if tc.function else "",
                            "arguments": "",
                        }
                    if tc.function and tc.function.arguments:
                        collected_tool_calls[idx]["arguments"] += tc.function.arguments

            if chunk.choices[0].finish_reason:
                yield {
                    "type": "finish",
                    "reason": chunk.choices[0].finish_reason,
                    "content": collected_content,
                    "tool_calls": list(collected_tool_calls.values()),
                }


def _convert_messages(
    system_prompt: str | list[dict],
    messages: list[dict[str, Any]],
) -> list[dict]:
    """Convert Anthropic message format to OpenAI format."""
    oai_msgs = []

    # System prompt
    if isinstance(system_prompt, str):
        oai_msgs.append({"role": "system", "content": system_prompt})
    elif isinstance(system_prompt, list):
        text = " ".join(b.get("text", "") for b in system_prompt if b.get("type") == "text")
        oai_msgs.append({"role": "system", "content": text})

    for msg in messages:
        role = msg["role"]
        content = msg["content"]

        if isinstance(content, str):
            oai_msgs.append({"role": role, "content": content})
        elif isinstance(content, list):
            # Handle content blocks
            text_parts = []
            tool_calls = []
            tool_results = []

            for block in content:
                if isinstance(block, dict):
                    if block.get("type") == "text":
                        text_parts.append(block["text"])
                    elif block.get("type") == "tool_use":
                        tool_calls.append({
                            "id": block["id"],
                            "type": "function",
                            "function": {
                                "name": block["name"],
                                "arguments": json.dumps(block["input"]),
                            },
                        })
                    elif block.get("type") == "tool_result":
                        tool_results.append(block)
                    # Skip thinking blocks

            if role == "assistant":
                msg_dict: dict[str, Any] = {"role": "assistant"}
                if text_parts:
                    msg_dict["content"] = "\n".join(text_parts)
                if tool_calls:
                    msg_dict["tool_calls"] = tool_calls
                oai_msgs.append(msg_dict)
            elif role == "user" and tool_results:
                for tr in tool_results:
                    oai_msgs.append({
                        "role": "tool",
                        "tool_call_id": tr.get("tool_use_id", ""),
                        "content": tr.get("content", ""),
                    })
            else:
                oai_msgs.append({"role": role, "content": "\n".join(text_parts) or str(content)})

    return oai_msgs


def _convert_tools(anthropic_tools: list[dict]) -> list[dict]:
    """Convert Anthropic tool schemas to OpenAI function calling format."""
    oai_tools = []
    for tool in anthropic_tools:
        oai_tools.append({
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool.get("description", ""),
                "parameters": tool.get("input_schema", {}),
            },
        })
    return oai_tools
