from __future__ import annotations

from pathlib import Path
from typing import Any, ClassVar

from astra.tools.base import Tool
from astra.types import ToolResult


class FileWriteTool(Tool):
    name: ClassVar[str] = "file_write"
    description: ClassVar[str] = (
        "Write content to a file, creating it if it doesn't exist. "
        "This overwrites the entire file. Use file_edit for partial modifications."
    )
    input_schema: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Absolute or relative path to the file to write",
            },
            "content": {
                "type": "string",
                "description": "The full content to write to the file",
            },
        },
        "required": ["file_path", "content"],
    }
    is_read_only: ClassVar[bool] = False

    async def call(self, *, tool_input: dict[str, Any], cwd: str) -> ToolResult:
        file_path = tool_input["file_path"]
        content = tool_input["content"]

        path = Path(file_path)
        if not path.is_absolute():
            path = Path(cwd) / path

        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            return ToolResult(
                output=f"Successfully wrote {len(content)} bytes to {path}"
            )
        except Exception as e:
            return ToolResult(output=f"Error writing file: {e}", is_error=True)
