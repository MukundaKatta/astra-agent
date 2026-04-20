from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import frontmatter

from astra.config import MemoryLifecyclePolicy
from astra.memory.types import Memory, MemoryType

MEMORY_INDEX = "MEMORY.md"


class MemoryStore:
    def __init__(
        self,
        memory_dir: Path,
        policy: MemoryLifecyclePolicy | None = None,
    ) -> None:
        self.memory_dir = memory_dir
        self.policy = policy or MemoryLifecyclePolicy()
        self.memory_dir.mkdir(parents=True, exist_ok=True)

    def save(
        self,
        title: str,
        content: str,
        memory_type: MemoryType,
        tags: tuple[str, ...] = (),
        metadata: dict[str, Any] | None = None,
    ) -> Path:
        """Save a new memory file with frontmatter."""
        slug = "".join(c if c.isalnum() or c == "-" else "-" for c in title.lower())[:50]
        ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        filename = f"{ts}-{slug}.md"
        filepath = self.memory_dir / filename

        post = frontmatter.Post(content)
        post["title"] = title
        post["type"] = memory_type.value
        post["created"] = datetime.now(timezone.utc).isoformat()
        if tags:
            post["tags"] = list(tags)
        if metadata:
            post["metadata"] = metadata

        filepath.write_text(frontmatter.dumps(post))
        self.prune()
        self._update_index()
        return filepath

    def list_all(self) -> list[Memory]:
        """List all memories sorted by creation date (newest first)."""
        memories = []
        for f in sorted(self.memory_dir.glob("*.md"), reverse=True):
            if f.name == MEMORY_INDEX:
                continue
            try:
                memories.append(self._load_one(f))
            except Exception:
                pass
        return memories

    def search(self, query: str) -> list[Memory]:
        """Search memories by content/title match."""
        q = query.lower()
        return [
            m
            for m in self.list_all()
            if q in m.title.lower() or q in m.content.lower()
        ]

    def prune(self) -> list[str]:
        """Prune old memory files according to the configured retention policy."""
        memories = self.list_all()
        to_remove = memories[self.policy.keep_recent_memories :]
        removed_paths: list[str] = []
        for memory in to_remove:
            if memory.file_path:
                path = Path(memory.file_path)
                if path.exists():
                    path.unlink()
                    removed_paths.append(str(path))
        return removed_paths

    def build_session_memory_plan(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
        """Plan how session messages should be retained, persisted, or summarized."""
        recent_messages = messages[-self.policy.short_term_message_limit :]
        pruned_messages = messages[: -self.policy.short_term_message_limit]
        persisted = []
        for message in pruned_messages:
            role = message.get("role")
            if role == "user" and self.policy.persist_user_messages:
                persisted.append(message)
            elif role == "assistant" and self.policy.persist_assistant_messages:
                persisted.append(message)
        summary = None
        if self.policy.summarize_pruned_messages and pruned_messages:
            summary = {
                "count": len(pruned_messages),
                "roles": [message.get("role", "unknown") for message in pruned_messages],
            }
        return {
            "recent_messages": recent_messages,
            "persisted_messages": persisted,
            "summary": summary,
        }

    def _load_one(self, path: Path) -> Memory:
        post = frontmatter.load(str(path))
        return Memory(
            title=post.get("title", path.stem),
            memory_type=MemoryType(post.get("type", "reference")),
            content=post.content,
            created=datetime.fromisoformat(
                str(post.get("created", "2000-01-01T00:00:00+00:00"))
            ),
            tags=tuple(post.get("tags", [])),
            file_path=str(path),
            metadata=post.get("metadata"),
        )

    def _update_index(self) -> None:
        """Regenerate MEMORY.md index file."""
        memories = self.list_all()
        lines = ["# Memory Index", "", f"Total: {len(memories)} memories", ""]
        for m in memories:
            date_str = m.created.strftime("%Y-%m-%d")
            lines.append(f"- **{m.title}** ({m.memory_type.value}) — {date_str}")
        (self.memory_dir / MEMORY_INDEX).write_text("\n".join(lines) + "\n")
