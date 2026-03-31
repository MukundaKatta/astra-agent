"""Context compaction — summarize old messages to save token budget."""

from __future__ import annotations

from typing import Any


def compact_messages(
    messages: list[dict[str, Any]],
    keep_recent: int = 4,
) -> list[dict[str, Any]]:
    """
    Compact a conversation by replacing older messages with a summary.

    Keeps the most recent `keep_recent` message pairs intact.
    Older messages are collapsed into a single summary message.
    """
    if len(messages) <= keep_recent * 2:
        return messages  # Already small enough

    # Split into old and recent
    cutoff = len(messages) - (keep_recent * 2)
    old_messages = messages[:cutoff]
    recent_messages = messages[cutoff:]

    # Build summary of old messages
    summary_parts = []
    for msg in old_messages:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")

        if isinstance(content, str):
            text = content
        elif isinstance(content, list):
            # Extract text from content blocks
            texts = []
            for block in content:
                if isinstance(block, dict):
                    if block.get("type") == "text":
                        texts.append(block["text"])
                    elif block.get("type") == "tool_use":
                        texts.append(f"[Tool: {block.get('name', '?')}]")
                    elif block.get("type") == "tool_result":
                        result = block.get("content", "")
                        if isinstance(result, str):
                            texts.append(f"[Result: {result[:100]}]")
                    elif block.get("type") == "thinking":
                        pass  # Skip thinking blocks in summary
            text = " | ".join(texts)
        else:
            text = str(content)

        if text.strip():
            # Truncate individual messages for the summary
            if len(text) > 200:
                text = text[:200] + "..."
            summary_parts.append(f"[{role}] {text}")

    summary_text = (
        "**Conversation Summary (compacted):**\n"
        + "\n".join(summary_parts[-20:])  # Keep at most 20 entries
    )

    # Return summary + recent messages
    return [
        {"role": "user", "content": summary_text},
        {"role": "assistant", "content": "Understood. I have the context from our earlier conversation."},
        *recent_messages,
    ]


def estimate_tokens(messages: list[dict[str, Any]]) -> int:
    """Rough token estimate for a message list (~4 chars per token)."""
    total_chars = 0
    for msg in messages:
        content = msg.get("content", "")
        if isinstance(content, str):
            total_chars += len(content)
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict):
                    for v in block.values():
                        if isinstance(v, str):
                            total_chars += len(v)
    return total_chars // 4
