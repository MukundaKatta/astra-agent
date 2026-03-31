from __future__ import annotations

from pathlib import Path
from typing import Any, ClassVar

from astra.tools.base import Tool
from astra.types import ToolResult


class FileEditTool(Tool):
    name: ClassVar[str] = "file_edit"
    description: ClassVar[str] = (
        "Edit a file by replacing an exact string match with new content. "
        "The old_string must appear exactly once in the file. "
        "Use file_write for creating new files."
    )
    input_schema: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Absolute or relative path to the file to edit",
            },
            "old_string": {
                "type": "string",
                "description": "The exact string to find and replace",
            },
            "new_string": {
                "type": "string",
                "description": "The replacement string",
            },
        },
        "required": ["file_path", "old_string", "new_string"],
    }
    is_read_only: ClassVar[bool] = False

    async def call(self, *, tool_input: dict[str, Any], cwd: str) -> ToolResult:
        file_path = tool_input["file_path"]
        old_string = tool_input["old_string"]
        new_string = tool_input["new_string"]

        if old_string == new_string:
            return ToolResult(
                output="old_string and new_string are identical", is_error=True
            )

        path = Path(file_path)
        if not path.is_absolute():
            path = Path(cwd) / path

        if not path.exists():
            return ToolResult(output=f"File not found: {path}", is_error=True)

        try:
            content = path.read_text(encoding="utf-8")
        except Exception as e:
            return ToolResult(output=f"Error reading file: {e}", is_error=True)

        count = content.count(old_string)
        if count == 0:
            return ToolResult(
                output="old_string not found in file", is_error=True
            )
        if count > 1:
            return ToolResult(
                output=f"old_string found {count} times — must be unique. "
                "Provide more surrounding context to make it unique.",
                is_error=True,
            )

        new_content = content.replace(old_string, new_string, 1)
        try:
            path.write_text(new_content, encoding="utf-8")
            return ToolResult(output=f"Successfully edited {path}")
        except Exception as e:
            return ToolResult(output=f"Error writing file: {e}", is_error=True)
