from __future__ import annotations

import asyncio
import os
from typing import Any, ClassVar

from astra.tools.base import Tool
from astra.types import ToolResult


class BashTool(Tool):
    name: ClassVar[str] = "bash"
    description: ClassVar[str] = (
        "Execute a bash command in the working directory. "
        "Use for running scripts, installing packages, git operations, "
        "and any shell commands. Returns stdout and stderr."
    )
    input_schema: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "The bash command to execute",
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout in seconds (default 120, max 600)",
            },
        },
        "required": ["command"],
    }
    is_read_only: ClassVar[bool] = False

    async def call(self, *, tool_input: dict[str, Any], cwd: str) -> ToolResult:
        command = tool_input["command"]
        timeout = min(tool_input.get("timeout", 120), 600)

        proc = None
        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
                env={**os.environ, "TERM": "dumb"},
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=timeout
            )

            parts = []
            if stdout:
                parts.append(stdout.decode("utf-8", errors="replace"))
            if stderr:
                parts.append(f"STDERR:\n{stderr.decode('utf-8', errors='replace')}")

            output = "\n".join(parts) or "(no output)"
            return ToolResult(
                output=output, is_error=proc.returncode != 0
            ).truncated()

        except asyncio.TimeoutError:
            if proc:
                try:
                    proc.kill()
                except ProcessLookupError:
                    pass
            return ToolResult(
                output=f"Command timed out after {timeout}s", is_error=True
            )
        except Exception as e:
            return ToolResult(output=f"Error executing command: {e}", is_error=True)
