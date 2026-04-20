from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any


class MemoryType(str, Enum):
    USER = "user"
    FEEDBACK = "feedback"
    PROJECT = "project"
    REFERENCE = "reference"


@dataclass(frozen=True)
class Memory:
    """A single memory entry with frontmatter metadata."""

    title: str
    memory_type: MemoryType
    content: str
    created: datetime
    tags: tuple[str, ...] = ()
    file_path: str = ""
    metadata: dict[str, Any] | None = None
