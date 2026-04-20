from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class PermissionMode(str, Enum):
    DEFAULT = "default"  # Ask user for write operations
    AUTO = "auto"  # Auto-approve everything
    BYPASS = "bypass"  # Skip all permission checks


@dataclass(frozen=True)
class MemoryLifecyclePolicy:
    """Retention and pruning policy for long-running sessions."""

    short_term_message_limit: int = 40
    persist_user_messages: bool = True
    persist_assistant_messages: bool = False
    keep_recent_memories: int = 50
    summarize_pruned_messages: bool = True


@dataclass(frozen=True)
class AstraConfig:
    model: str = "claude-sonnet-4-20250514"
    max_turns: int = 30
    max_tokens: int = 16384
    permission_mode: PermissionMode = PermissionMode.DEFAULT
    cwd: Path = field(default_factory=Path.cwd)
    memory_dir: Path | None = None
    session_dir: Path | None = None
    mcp_config_paths: tuple[str, ...] = ()
    verbose: bool = False
    thinking: bool = True
    memory_policy: MemoryLifecyclePolicy = field(default_factory=MemoryLifecyclePolicy)
