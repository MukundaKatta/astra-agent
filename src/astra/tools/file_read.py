from __future__ import annotations

from pathlib import Path
from typing import Any, ClassVar

from astra.tools.base import Tool
from astra.types import ToolResult


class FileReadTool(Tool):
    name: ClassVar[str] = "file_read"
    description: ClassVar[str] = (
        "Read the contents of a file. Returns the file content with line numbers. "
        "Use offset and limit to read specific portions of large files."
    )
    input_schema: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Absolute or relative path to the file to read",
            },
            "offset": {
                "type": "integer",
                "description": "Line number to start reading from (1-based, default 1)",
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of lines to read (default 2000)",
            },
        },
        "required": ["file_path"],
    }
    is_read_only: ClassVar[bool] = True

    async def call(self, *, tool_input: dict[str, Any], cwd: str) -> ToolResult:
        file_path = tool_input["file_path"]
        offset = max(1, tool_input.get("offset", 1))
        limit = tool_input.get("limit", 2000)

        path = Path(file_path)
        if not path.is_absolute():
            path = Path(cwd) / path

        if not path.exists():
            return ToolResult(output=f"File not found: {path}", is_error=True)

        if not path.is_file():
            return ToolResult(output=f"Not a file: {path}", is_error=True)

        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            return ToolResult(output=f"Error reading file: {e}", is_error=True)

        lines = content.splitlines()
        total_lines = len(lines)

        # Apply offset and limit
        selected = lines[offset - 1 : offset - 1 + limit]

        # Format with line numbers
        numbered = []
        for i, line in enumerate(selected, start=offset):
            numbered.append(f"{i}\t{line}")

        output = "\n".join(numbered)
        if offset + limit - 1 < total_lines:
            output += f"\n\n... ({total_lines - offset - limit + 1} more lines)"

        return ToolResult(output=output).truncated()
