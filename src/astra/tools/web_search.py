"""Web search tool — search the web using DuckDuckGo (no API key needed)."""

from __future__ import annotations

import asyncio
import json
import urllib.parse
from typing import Any, ClassVar

from astra.tools.base import Tool
from astra.types import ToolResult


class WebSearchTool(Tool):
    name: ClassVar[str] = "web_search"
    description: ClassVar[str] = (
        "Search the web using DuckDuckGo. Returns titles, URLs, and snippets "
        "for the top results. Use this to find documentation, examples, or "
        "current information."
    )
    input_schema: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query",
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of results (default 5, max 10)",
            },
        },
        "required": ["query"],
    }
    is_read_only: ClassVar[bool] = True

    async def call(self, *, tool_input: dict[str, Any], cwd: str) -> ToolResult:
        query = tool_input["query"]
        max_results = min(tool_input.get("max_results", 5), 10)

        try:
            # Use DuckDuckGo HTML search (no API key required)
            encoded = urllib.parse.quote_plus(query)
            url = f"https://html.duckduckgo.com/html/?q={encoded}"

            proc = await asyncio.create_subprocess_exec(
                "curl", "-sL", "-A",
                "Mozilla/5.0 (compatible; AstraAgent/0.1)",
                url,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=15)
            html = stdout.decode("utf-8", errors="replace")

            results = _parse_ddg_html(html, max_results)
            if not results:
                return ToolResult(output=f"No results found for: {query}")

            lines = []
            for i, r in enumerate(results, 1):
                lines.append(f"{i}. {r['title']}")
                lines.append(f"   {r['url']}")
                if r["snippet"]:
                    lines.append(f"   {r['snippet']}")
                lines.append("")

            return ToolResult(output="\n".join(lines))

        except asyncio.TimeoutError:
            return ToolResult(output="Search timed out", is_error=True)
        except Exception as e:
            return ToolResult(output=f"Search error: {e}", is_error=True)


def _parse_ddg_html(html: str, max_results: int) -> list[dict]:
    """Parse DuckDuckGo HTML results (simple regex-based parser)."""
    import re

    results = []
    # Find result blocks
    blocks = re.findall(
        r'class="result__a"[^>]*href="([^"]*)"[^>]*>(.*?)</a>.*?'
        r'class="result__snippet"[^>]*>(.*?)</div>',
        html,
        re.DOTALL,
    )

    for url, title, snippet in blocks[:max_results]:
        # Clean up URL (DuckDuckGo wraps URLs)
        actual_url = url
        if "uddg=" in url:
            match = re.search(r"uddg=([^&]+)", url)
            if match:
                actual_url = urllib.parse.unquote(match.group(1))

        # Strip HTML tags
        title = re.sub(r"<[^>]+>", "", title).strip()
        snippet = re.sub(r"<[^>]+>", "", snippet).strip()

        if title and actual_url:
            results.append(
                {"title": title, "url": actual_url, "snippet": snippet}
            )

    return results
