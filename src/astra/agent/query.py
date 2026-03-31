"""Core agent loop — async generator that orchestrates Claude API calls and tool execution.

This is the heart of Astra Agent, modeled on Claude Code's query() async generator.
It streams responses, detects tool_use blocks, executes tools, feeds results back,
and loops until end_turn or max_turns.
"""

from __future__ import annotations

from typing import Any, AsyncGenerator

import anthropic

from astra.permissions.checker import PermissionChecker, PermissionDecision
from astra.tools import ToolRegistry
from astra.types import StreamEvent, Usage


async def query(
    *,
    client: anthropic.AsyncAnthropic,
    model: str,
    system_prompt: str | list[dict],
    messages: list[dict[str, Any]],
    tools: ToolRegistry,
    permission_checker: PermissionChecker,
    cwd: str,
    max_tokens: int = 16384,
    max_turns: int = 30,
    thinking: bool = True,
    on_permission_request: Any | None = None,
) -> AsyncGenerator[StreamEvent, None]:
    """
    Core agent loop. Async generator that:
    1. Sends messages to Claude API with tool definitions
    2. Streams the response, yielding text/thinking events
    3. When tool_use blocks appear, executes them
    4. Feeds tool_results back and continues the loop
    5. Stops on end_turn, max_turns, or abort

    The caller (QueryEngine) owns the messages list.
    This generator mutates it in-place (appends assistant + tool_result messages).
    """
    turn = 0
    tool_schemas = tools.to_anthropic_schemas()

    while turn < max_turns:
        turn += 1
        yield {"type": "turn_start", "turn": turn}

        # Build API params
        api_params: dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "system": system_prompt,
            "messages": messages,
            "stream": True,
        }
        if tool_schemas:
            api_params["tools"] = tool_schemas
        if thinking:
            api_params["thinking"] = {"type": "enabled", "budget_tokens": 10000}

        # Stream the API response
        current_usage = Usage()

        try:
            async with client.messages.stream(**api_params) as stream:
                async for event in stream:
                    if event.type == "content_block_start":
                        block = event.content_block
                        if block.type == "text":
                            yield {"type": "text_start"}
                        elif block.type == "thinking":
                            yield {"type": "thinking_start"}
                        elif block.type == "tool_use":
                            yield {
                                "type": "tool_use_start",
                                "name": block.name,
                                "id": block.id,
                            }
                    elif event.type == "content_block_delta":
                        delta = event.delta
                        if hasattr(delta, "text"):
                            yield {"type": "text_delta", "text": delta.text}
                        elif hasattr(delta, "thinking"):
                            yield {"type": "thinking_delta", "text": delta.thinking}
                        elif hasattr(delta, "partial_json"):
                            yield {
                                "type": "tool_input_delta",
                                "json": delta.partial_json,
                            }
                    elif event.type == "content_block_stop":
                        yield {"type": "block_stop"}
                    elif event.type == "message_start":
                        if hasattr(event.message, "usage") and event.message.usage:
                            u = event.message.usage
                            current_usage = Usage(
                                input_tokens=getattr(u, "input_tokens", 0),
                                output_tokens=0,
                                cache_creation_input_tokens=getattr(
                                    u, "cache_creation_input_tokens", 0
                                ),
                                cache_read_input_tokens=getattr(
                                    u, "cache_read_input_tokens", 0
                                ),
                            )
                    elif event.type == "message_delta":
                        if hasattr(event, "usage") and event.usage:
                            current_usage = Usage(
                                input_tokens=current_usage.input_tokens,
                                output_tokens=getattr(
                                    event.usage, "output_tokens", 0
                                ),
                                cache_creation_input_tokens=current_usage.cache_creation_input_tokens,
                                cache_read_input_tokens=current_usage.cache_read_input_tokens,
                            )

                # Get final message
                final_message = await stream.get_final_message()

        except anthropic.APIError as e:
            yield {"type": "error", "error": str(e)}
            return

        yield {"type": "usage", "usage": current_usage}

        # Build assistant message content blocks
        assistant_content = []
        for block in final_message.content:
            if block.type == "thinking":
                assistant_content.append(
                    {
                        "type": "thinking",
                        "thinking": block.thinking,
                        "signature": block.signature,
                    }
                )
            elif block.type == "text":
                assistant_content.append({"type": "text", "text": block.text})
            elif block.type == "tool_use":
                assistant_content.append(
                    {
                        "type": "tool_use",
                        "id": block.id,
                        "name": block.name,
                        "input": block.input,
                    }
                )

        messages.append({"role": "assistant", "content": assistant_content})

        # Check stop reason
        if final_message.stop_reason == "end_turn":
            yield {"type": "turn_complete", "stop_reason": "end_turn"}
            return

        if final_message.stop_reason != "tool_use":
            yield {
                "type": "turn_complete",
                "stop_reason": final_message.stop_reason or "unknown",
            }
            return

        # Process tool calls
        tool_use_blocks = [b for b in final_message.content if b.type == "tool_use"]
        tool_results: list[dict[str, Any]] = []

        for tool_use in tool_use_blocks:
            tool = tools.get(tool_use.name)
            if tool is None:
                result_output = f"Unknown tool: {tool_use.name}"
                is_error = True
            else:
                # Check permissions
                decision = tool.check_permissions(tool_use.input, permission_checker)

                if decision == PermissionDecision.DENY:
                    result_output = "Permission denied"
                    is_error = True
                elif decision == PermissionDecision.ASK:
                    # Ask user for permission if callback provided
                    allowed = False
                    if on_permission_request:
                        allowed = await on_permission_request(
                            tool_use.name, tool_use.input
                        )
                    if not allowed:
                        yield {
                            "type": "permission_denied",
                            "tool": tool_use.name,
                            "id": tool_use.id,
                        }
                        result_output = "Permission denied by user"
                        is_error = True
                    else:
                        yield {
                            "type": "tool_executing",
                            "name": tool_use.name,
                            "id": tool_use.id,
                            "input": tool_use.input,
                        }
                        result = await tool.call(tool_input=tool_use.input, cwd=cwd)
                        result_output = result.output
                        is_error = result.is_error
                else:
                    # ALLOW
                    yield {
                        "type": "tool_executing",
                        "name": tool_use.name,
                        "id": tool_use.id,
                        "input": tool_use.input,
                    }
                    result = await tool.call(tool_input=tool_use.input, cwd=cwd)
                    result_output = result.output
                    is_error = result.is_error

            yield {
                "type": "tool_result",
                "id": tool_use.id,
                "name": tool_use.name,
                "output": result_output,
                "is_error": is_error,
            }

            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": tool_use.id,
                    "content": result_output,
                    **({"is_error": True} if is_error else {}),
                }
            )

        # Append tool results as user message
        messages.append({"role": "user", "content": tool_results})

    yield {"type": "turn_complete", "stop_reason": "max_turns"}
