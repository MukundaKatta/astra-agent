from __future__ import annotations

import json
from pathlib import Path

from astra.config import MemoryLifecyclePolicy, PermissionMode
from astra.memory.store import MemoryStore
from astra.memory.types import MemoryType
from astra.permissions.checker import PermissionChecker, PermissionDecision
from astra.session.storage import SessionStorage
from astra.session.usage import UsageTracker
from astra.tools import ToolRegistry, build_default_registry
from astra.types import Usage


def test_tool_registry_contains_default_tools() -> None:
    registry = build_default_registry()

    tool_names = {tool.name for tool in registry.all_tools()}
    assert {"bash", "file_read", "file_write", "file_edit", "grep", "glob"} <= tool_names


def test_permission_checker_modes() -> None:
    default_checker = PermissionChecker(PermissionMode.DEFAULT)
    auto_checker = PermissionChecker(PermissionMode.AUTO)
    bypass_checker = PermissionChecker(PermissionMode.BYPASS)

    assert default_checker.check("file_read", {}) == PermissionDecision.ALLOW
    assert default_checker.check("file_write", {}) == PermissionDecision.ASK
    assert auto_checker.check("mcp__server__tool", {}) == PermissionDecision.ALLOW
    assert bypass_checker.check("file_edit", {}) == PermissionDecision.ALLOW


def test_session_storage_save_load_and_prune(tmp_path: Path) -> None:
    storage = SessionStorage(tmp_path)
    usage = Usage(input_tokens=10, output_tokens=5)

    storage.save("one", [{"role": "user", "content": "hello"}], usage)
    storage.save("two", [{"role": "assistant", "content": "hi"}], usage)
    storage.save("three", [{"role": "user", "content": "again"}], usage)

    loaded = storage.load("two")
    assert loaded["session_id"] == "two"
    removed = storage.prune(keep_recent=2)
    assert len(removed) == 1
    assert not (tmp_path / "one.json").exists()


def test_usage_tracker_summary() -> None:
    tracker = UsageTracker()
    tracker.add(Usage(input_tokens=100, output_tokens=50))

    summary = tracker.summary()
    assert "Tokens:" in summary
    assert "Turns: 1" in summary
    assert tracker.estimated_cost_usd > 0


def test_memory_store_prunes_old_entries(tmp_path: Path) -> None:
    store = MemoryStore(
        tmp_path,
        policy=MemoryLifecyclePolicy(keep_recent_memories=2),
    )
    store.save("First memory", "one", MemoryType.USER)
    store.save("Second memory", "two", MemoryType.USER)
    store.save("Third memory", "three", MemoryType.USER)

    memories = store.list_all()
    assert len(memories) == 2
    titles = [memory.title for memory in memories]
    assert "Third memory" in titles
    assert "Second memory" in titles


def test_memory_store_builds_session_memory_plan(tmp_path: Path) -> None:
    store = MemoryStore(
        tmp_path,
        policy=MemoryLifecyclePolicy(
            short_term_message_limit=2,
            persist_user_messages=True,
            persist_assistant_messages=False,
            summarize_pruned_messages=True,
        ),
    )
    messages = [
        {"role": "user", "content": "one"},
        {"role": "assistant", "content": "two"},
        {"role": "user", "content": "three"},
        {"role": "assistant", "content": "four"},
    ]

    plan = store.build_session_memory_plan(messages)

    assert len(plan["recent_messages"]) == 2
    assert len(plan["persisted_messages"]) == 1
    assert plan["persisted_messages"][0]["content"] == "one"
    assert plan["summary"]["count"] == 2
