from __future__ import annotations

import asyncio
import shutil
from pathlib import Path
from typing import Any, ClassVar

from astra.tools.base import Tool
from astra.types import ToolResult


class GrepTool(Tool):
    name: ClassVar[str] = "grep"
    description: ClassVar[str] = (
        "Search file contents using regex patterns. Uses ripgrep (rg) if available, "
        "otherwise falls back to grep. Returns matching lines with file paths."
    )
    input_schema: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "pattern": {
                "type": "string",
                "description": "Regular expression pattern to search for",
            },
            "path": {
                "type": "string",
                "description": "File or directory to search in (default: working directory)",
            },
            "include": {
                "type": "string",
                "description": "Glob pattern to filter files (e.g. '*.py', '*.ts')",
            },
            "case_insensitive": {
                "type": "boolean",
                "description": "Case insensitive search (default false)",
            },
        },
        "required": ["pattern"],
    }
    is_read_only: ClassVar[bool] = True

    async def call(self, *, tool_input: dict[str, Any], cwd: str) -> ToolResult:
        pattern = tool_input["pattern"]
        search_path = tool_input.get("path", cwd)
        include = tool_input.get("include")
        case_insensitive = tool_input.get("case_insensitive", False)

        path = Path(search_path)
        if not path.is_absolute():
            path = Path(cwd) / path

        # Prefer ripgrep, fall back to grep
        rg = shutil.which("rg")
        if rg:
            args = [rg, "--hidden", "--no-heading", "--line-number", "--max-columns", "500"]
            if case_insensitive:
                args.append("-i")
            if include:
                args.extend(["--glob", include])
            # Exclude common dirs
            for d in [".git", "node_modules", "__pycache__", ".venv"]:
                args.extend(["--glob", f"!{d}"])
            args.append(pattern)
            args.append(str(path))
        else:
            args = ["grep", "-rn"]
            if case_insensitive:
                args.append("-i")
            if include:
                args.extend(["--include", include])
            args.append(pattern)
            args.append(str(path))

        try:
            proc = await asyncio.create_subprocess_exec(
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)

            output = stdout.decode("utf-8", errors="replace").strip()
            if not output:
                return ToolResult(output="No matches found")

            # Truncate if too many results
            lines = output.split("\n")
            if len(lines) > 500:
                output = "\n".join(lines[:500])
                output += f"\n\n... ({len(lines) - 500} more matches)"

            return ToolResult(output=output)

        except asyncio.TimeoutError:
            return ToolResult(output="Search timed out after 30s", is_error=True)
        except Exception as e:
            return ToolResult(output=f"Search error: {e}", is_error=True)
