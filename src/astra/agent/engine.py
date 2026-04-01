"""QueryEngine — stateful session wrapper around the agent loop."""

from __future__ import annotations

from pathlib import Path
from typing import Any, AsyncGenerator, Callable, Coroutine
from uuid import uuid4

import anthropic

from astra.agent.context import build_system_prompt
from astra.agent.query import StreamEvent, query
from astra.config import AstraConfig
from astra.mcp.bridge import register_mcp_tools
from astra.mcp.client import MCPManager
from astra.permissions.checker import PermissionChecker
from astra.session.storage import SessionStorage
from astra.session.usage import UsageTracker
from astra.tools import ToolRegistry, build_default_registry
from astra.types import Usage


class QueryEngine:
    """
    Stateful wrapper around the query loop. One per conversation.
    Manages messages, usage, session persistence, and MCP connections.
    """

    def __init__(
        self,
        config: AstraConfig,
        client: anthropic.AsyncAnthropic | None = None,
        session_id: str | None = None,
    ) -> None:
        self.config = config
        self.session_id = session_id or uuid4().hex[:12]
        self.client = client or anthropic.AsyncAnthropic()
        self.messages: list[dict[str, Any]] = []
        self.usage = UsageTracker()
        self.tools = build_default_registry()
        self.permission_checker = PermissionChecker(config.permission_mode)
        self.mcp_manager = MCPManager()
        self._session_storage = SessionStorage(config.session_dir)
        self._system_prompt: str | None = None
        self._initialized = False
        self.on_permission_request: (
            Callable[[str, dict], Coroutine[Any, Any, bool]] | None
        ) = None

    async def initialize(self) -> None:
        """Connect MCP servers, build system prompt."""
        # Connect MCP servers
        try:
            await self.mcp_manager.connect_from_config(self.config.mcp_config_paths)
            register_mcp_tools(self.mcp_manager, self.tools)
        except Exception:
            pass  # MCP is optional — continue without it

        # Build system prompt
        self._system_prompt = await build_system_prompt(
            cwd=str(self.config.cwd),
            tools=self.tools,
            memory_dir=self.config.memory_dir,
        )
        self._initialized = True

    async def submit_message(
        self, prompt: str
    ) -> AsyncGenerator[StreamEvent, None]:
        """Submit a user message and stream back events."""
        if not self._initialized:
            raise RuntimeError(
                "Engine not initialized. Call await engine.initialize() first."
            )
        self.messages.append({"role": "user", "content": prompt})

        async for event in query(
            client=self.client,
            model=self.config.model,
            system_prompt=self._system_prompt or "",
            messages=self.messages,
            tools=self.tools,
            permission_checker=self.permission_checker,
            cwd=str(self.config.cwd),
            max_tokens=self.config.max_tokens,
            max_turns=self.config.max_turns,
            thinking=self.config.thinking,
            on_permission_request=self.on_permission_request,
        ):
            if event["type"] == "usage":
                self.usage.add(event["usage"])
            yield event

    async def save_session(self) -> str:
        """Persist conversation to disk."""
        return self._session_storage.save(
            session_id=self.session_id,
            messages=self.messages,
            usage=self.usage.total,
        )

    @classmethod
    async def resume(cls, session_id: str, config: AstraConfig) -> QueryEngine:
        """Resume a saved session."""
        storage = SessionStorage(config.session_dir)
        data = storage.load(session_id)
        engine = cls(config=config, session_id=session_id)
        engine.messages = data.get("messages", [])
        # Handle old session files that may lack cache fields
        usage_data = data.get("usage", {})
        engine.usage = UsageTracker(total=Usage(
            input_tokens=usage_data.get("input_tokens", 0),
            output_tokens=usage_data.get("output_tokens", 0),
            cache_creation_input_tokens=usage_data.get("cache_creation_input_tokens", 0),
            cache_read_input_tokens=usage_data.get("cache_read_input_tokens", 0),
        ))
        await engine.initialize()
        return engine

    async def shutdown(self) -> None:
        """Clean up MCP connections."""
        await self.mcp_manager.disconnect_all()
