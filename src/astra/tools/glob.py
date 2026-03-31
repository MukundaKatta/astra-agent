from __future__ import annotations

from pathlib import Path
from typing import Any, ClassVar

from astra.tools.base import Tool
from astra.types import ToolResult

# Directories to skip when globbing
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", ".tox", ".mypy_cache"}


class GlobTool(Tool):
    name: ClassVar[str] = "glob"
    description: ClassVar[str] = (
        "Find files matching a glob pattern. Returns matching file paths "
        "sorted by modification time (newest first). "
        "Example patterns: '**/*.py', 'src/**/*.ts', '*.json'"
    )
    input_schema: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "pattern": {
                "type": "string",
                "description": "Glob pattern to match files (e.g. '**/*.py')",
            },
            "path": {
                "type": "string",
                "description": "Directory to search in (default: working directory)",
            },
        },
        "required": ["pattern"],
    }
    is_read_only: ClassVar[bool] = True

    async def call(self, *, tool_input: dict[str, Any], cwd: str) -> ToolResult:
        pattern = tool_input["pattern"]
        search_path = tool_input.get("path", cwd)

        base = Path(search_path)
        if not base.is_absolute():
            base = Path(cwd) / base

        if not base.exists():
            return ToolResult(output=f"Directory not found: {base}", is_error=True)

        try:
            matches = []
            for p in base.glob(pattern):
                # Skip hidden/junk directories
                if any(part in SKIP_DIRS for part in p.parts):
                    continue
                if p.is_file():
                    matches.append(p)

            if not matches:
                return ToolResult(output="No files matched the pattern")

            # Sort by mtime (newest first)
            matches.sort(key=lambda p: p.stat().st_mtime, reverse=True)

            # Limit results
            total = len(matches)
            matches = matches[:500]

            output = "\n".join(str(p) for p in matches)
            if total > 500:
                output += f"\n\n... ({total - 500} more files)"

            return ToolResult(output=output)

        except Exception as e:
            return ToolResult(output=f"Glob error: {e}", is_error=True)
