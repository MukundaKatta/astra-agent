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
                "Install with: pip install astra-agent[openai]"
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
            if not chunk.choices:
                continue
            choice = chunk.choices[0]
            delta = choice.delta
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
                            "name": "",
                            "arguments": "",
                        }
                    # Update name if present (only comes in first chunk)
                    if tc.function and tc.function.name:
                        collected_tool_calls[idx]["name"] = tc.function.name
                    # Append argument fragments
                    if tc.function and tc.function.arguments:
                        collected_tool_calls[idx]["arguments"] += tc.function.arguments
                    # Preserve tool call id if provided in later chunks
                    if tc.id:
                        collected_tool_calls[idx]["id"] = tc.id

            if choice.finish_reason:
                yield {
                    "type": "finish",
                    "reason": choice.finish_reason,
                    "content": collected_content,
                    "tool_calls": list(collected_tool_calls.values()),
                }


def _convert_messages(
    system_prompt: str | list[dict],
    messages: list[dict[str, Any]],
) -> list[dict]:
    """Convert Anthropic message format to OpenAI format."""
    oai_msgs: list[dict[str, Any]] = []

    # System prompt
    if isinstance(system_prompt, str) and system_prompt.strip():
        oai_msgs.append({"role": "system", "content": system_prompt})
    elif isinstance(system_prompt, list):
        text = " ".join(
            b.get("text", "") for b in system_prompt if b.get("type") == "text"
        )
        if text.strip():
            oai_msgs.append({"role": "system", "content": text})

    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")

        if isinstance(content, str):
            oai_msgs.append({"role": role, "content": content})
        elif isinstance(content, list):
            # Handle content blocks
            text_parts: list[str] = []
            tool_calls: list[dict] = []
            tool_results: list[dict] = []

            for block in content:
                if not isinstance(block, dict):
                    continue
                block_type = block.get("type", "")
                if block_type == "text":
                    text_parts.append(block.get("text", ""))
                elif block_type == "tool_use":
                    try:
                        args_json = json.dumps(block.get("input", {}))
                    except (TypeError, ValueError):
                        args_json = "{}"
                    tool_calls.append({
                        "id": block.get("id", ""),
                        "type": "function",
                        "function": {
                            "name": block.get("name", ""),
                            "arguments": args_json,
                        },
                    })
                elif block_type == "tool_result":
                    tool_results.append(block)
                # Skip thinking blocks silently

            if role == "assistant":
                msg_dict: dict[str, Any] = {"role": "assistant"}
                # OpenAI requires content OR tool_calls (or both)
                if text_parts:
                    msg_dict["content"] = "\n".join(text_parts)
                else:
                    msg_dict["content"] = None  # OpenAI accepts null content with tool_calls
                if tool_calls:
                    msg_dict["tool_calls"] = tool_calls
                oai_msgs.append(msg_dict)
            elif tool_results:
                # Tool results become separate "tool" messages
                for tr in tool_results:
                    result_content = tr.get("content", "")
                    if not isinstance(result_content, str):
                        result_content = json.dumps(result_content, default=str)
                    oai_msgs.append({
                        "role": "tool",
                        "tool_call_id": tr.get("tool_use_id", ""),
                        "content": result_content,
                    })
                # Also include any text parts from the same message
                if text_parts:
                    oai_msgs.append({
                        "role": role,
                        "content": "\n".join(text_parts),
                    })
            else:
                text = "\n".join(text_parts) if text_parts else ""
                if text:
                    oai_msgs.append({"role": role, "content": text})
        else:
            # Fallback for unexpected content types
            oai_msgs.append({"role": role, "content": str(content)})

    return oai_msgs


def _convert_tools(anthropic_tools: list[dict]) -> list[dict]:
    """Convert Anthropic tool schemas to OpenAI function calling format."""
    oai_tools = []
    for tool in anthropic_tools:
        oai_tools.append({
            "type": "function",
            "function": {
                "name": tool.get("name", ""),
                "description": tool.get("description", ""),
                "parameters": tool.get("input_schema", {}),
            },
        })
    return oai_tools
