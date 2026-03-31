from __future__ import annotations

from pathlib import Path

from astra.memory.store import MEMORY_INDEX


async def load_memory_prompt(memory_dir: Path) -> str | None:
    """Load memory index for system prompt injection."""
    index_path = memory_dir / MEMORY_INDEX
    if not index_path.exists():
        return None
    content = index_path.read_text().strip()
    if not content:
        return None
    lines = content.split("\n")
    if len(lines) > 200:
        content = "\n".join(lines[:200]) + "\n... (truncated)"
    return f"Your Memory:\n{content}"
