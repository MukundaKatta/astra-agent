"""Web fetch tool — download and extract text content from a URL."""

from __future__ import annotations

import asyncio
import re
from typing import Any, ClassVar

from astra.tools.base import Tool
from astra.types import ToolResult


class WebFetchTool(Tool):
    name: ClassVar[str] = "web_fetch"
    description: ClassVar[str] = (
        "Fetch a URL and return its text content. HTML pages are converted "
        "to readable text. Useful for reading documentation, API responses, "
        "or any web content."
    )
    input_schema: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "The URL to fetch",
            },
            "max_length": {
                "type": "integer",
                "description": "Maximum characters to return (default 50000)",
            },
        },
        "required": ["url"],
    }
    is_read_only: ClassVar[bool] = True

    async def call(self, *, tool_input: dict[str, Any], cwd: str) -> ToolResult:
        url = tool_input["url"]
        max_length = tool_input.get("max_length", 50000)

        if not url.startswith(("http://", "https://")):
            return ToolResult(output="URL must start with http:// or https://", is_error=True)

        try:
            proc = await asyncio.create_subprocess_exec(
                "curl", "-sL", "-A",
                "Mozilla/5.0 (compatible; AstraAgent/0.1)",
                "--max-time", "30",
                "--max-filesize", "5000000",  # 5MB max
                url,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=35)

            if proc.returncode != 0:
                err = stderr.decode("utf-8", errors="replace").strip()
                return ToolResult(output=f"Fetch failed: {err}", is_error=True)

            content = stdout.decode("utf-8", errors="replace")

            # If HTML, extract text
            if "<html" in content.lower()[:500] or "<head" in content.lower()[:500]:
                content = _html_to_text(content)

            # Truncate
            if len(content) > max_length:
                content = content[:max_length] + "\n\n... (content truncated)"

            if not content.strip():
                return ToolResult(output="(empty response)")

            return ToolResult(output=content)

        except asyncio.TimeoutError:
            return ToolResult(output="Fetch timed out after 30s", is_error=True)
        except Exception as e:
            return ToolResult(output=f"Fetch error: {e}", is_error=True)


def _html_to_text(html: str) -> str:
    """Simple HTML to text conversion."""
    # Remove script and style blocks
    text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<nav[^>]*>.*?</nav>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<footer[^>]*>.*?</footer>", "", text, flags=re.DOTALL | re.IGNORECASE)

    # Convert common elements to text
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</?p[^>]*>", "\n\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</?div[^>]*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<h[1-6][^>]*>(.*?)</h[1-6]>", r"\n\n## \1\n", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<li[^>]*>(.*?)</li>", r"\n- \1", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<a[^>]*href=\"([^\"]+)\"[^>]*>(.*?)</a>", r"\2 (\1)", text, flags=re.DOTALL | re.IGNORECASE)

    # Remove all remaining HTML tags
    text = re.sub(r"<[^>]+>", "", text)

    # Decode HTML entities
    text = text.replace("&amp;", "&")
    text = text.replace("&lt;", "<")
    text = text.replace("&gt;", ">")
    text = text.replace("&quot;", '"')
    text = text.replace("&#39;", "'")
    text = text.replace("&nbsp;", " ")

    # Clean up whitespace
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r" {2,}", " ", text)

    return text.strip()
