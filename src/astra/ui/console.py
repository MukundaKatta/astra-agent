"""Rich-based terminal UI for the agent."""

from __future__ import annotations

import json

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text

from astra.types import StreamEvent

console = Console()


class AgentUI:
    """Rich-based terminal UI for the agent loop."""

    def __init__(self) -> None:
        self._text_buffer: list[str] = []
        self._thinking_buffer: list[str] = []
        self._in_thinking = False

    def print_welcome(self, session_id: str, model: str, tool_count: int) -> None:
        console.print(
            Panel(
                f"[bold blue]Astra Agent[/bold blue] v0.1.0\n"
                f"Model: [cyan]{model}[/cyan]\n"
                f"Tools: {tool_count}\n"
                f"Session: {session_id}\n"
                f"Type [green]/help[/green] for commands",
                title="[bold]Welcome[/bold]",
                border_style="blue",
            )
        )
        console.print("[dim]Type /exit to quit, /save to save session[/dim]\n")

    def print_usage(self, summary: str) -> None:
        console.print(f"[dim]{summary}[/dim]\n")

    def print_error(self, message: str) -> None:
        console.print(f"[bold red]Error:[/bold red] {message}")

    def handle_stream_event(self, event: StreamEvent) -> None:
        """Process a stream event and update the display."""
        event_type = event["type"]

        if event_type == "text_start":
            self._flush_thinking()
            self._text_buffer = []

        elif event_type == "text_delta":
            self._text_buffer.append(event["text"])
            # Stream text character by character
            console.print(event["text"], end="", highlight=False)

        elif event_type == "thinking_start":
            self._in_thinking = True
            self._thinking_buffer = []

        elif event_type == "thinking_delta":
            self._thinking_buffer.append(event["text"])

        elif event_type == "block_stop":
            if self._in_thinking:
                self._in_thinking = False
                # Show collapsed thinking indicator
                thinking_text = "".join(self._thinking_buffer).strip()
                if thinking_text:
                    # Show first line as indicator
                    first_line = thinking_text.split("\n")[0][:80]
                    console.print(
                        f"\n[dim italic]Thinking: {first_line}...[/dim italic]"
                    )
                self._thinking_buffer = []
            elif self._text_buffer:
                # End of text block - print newline
                console.print()

        elif event_type == "tool_use_start":
            self._flush_text()
            console.print(f"\n[yellow bold]Tool:[/yellow bold] {event['name']}")

        elif event_type == "tool_executing":
            tool_input = event.get("input", {})
            # Show compact tool input
            summary = _summarize_tool_input(event["name"], tool_input)
            if summary:
                console.print(f"  [dim]{summary}[/dim]")

        elif event_type == "tool_result":
            output = event["output"]
            is_error = event.get("is_error", False)
            tool_name = event.get("name", "")
            style = "red" if is_error else "green"
            title = f"{'Error' if is_error else 'Result'}: {tool_name}"

            # Detect diff output and render with syntax highlighting
            if not is_error and "\n---" in output and "\n+++" in output:
                # Split result text from diff
                parts = output.split("\n---", 1)
                result_text = parts[0].strip()
                diff_text = "---" + parts[1]

                if result_text:
                    console.print(
                        Panel(result_text, title=title, style=style,
                              width=min(100, console.width))
                    )
                # Render diff with syntax highlighting
                if len(diff_text) > 3000:
                    diff_text = diff_text[:3000] + "\n... (diff truncated)"
                console.print(Syntax(diff_text, "diff", theme="monokai",
                                     word_wrap=True))
            else:
                # Truncate for display
                if len(output) > 3000:
                    output = output[:3000] + "\n... (truncated for display)"
                console.print(
                    Panel(output, title=title, style=style,
                          width=min(100, console.width))
                )

        elif event_type == "permission_denied":
            console.print(
                f"[red]Permission denied for tool: {event.get('tool', 'unknown')}[/red]"
            )

        elif event_type == "turn_complete":
            self._flush_text()
            self._flush_thinking()

        elif event_type == "error":
            console.print(f"[bold red]API Error:[/bold red] {event.get('error', '')}")

    def _flush_text(self) -> None:
        # Text is streamed directly, just reset buffer
        self._text_buffer = []

    def _flush_thinking(self) -> None:
        self._thinking_buffer = []
        self._in_thinking = False

    def prompt_user(self) -> str:
        """Get input from user."""
        return console.input("[bold green]> [/bold green]")

    async def ask_permission(self, tool_name: str, tool_input: dict) -> bool:
        """Ask user for permission to run a tool."""
        console.print(
            f"\n[yellow]Permission needed:[/yellow] [bold]{tool_name}[/bold]"
        )

        # Show diff preview for file edits
        if tool_name == "file_edit":
            file_path = tool_input.get("file_path", "")
            old_str = tool_input.get("old_string", "")
            new_str = tool_input.get("new_string", "")
            console.print(f"  File: [cyan]{file_path}[/cyan]")
            if old_str and new_str:
                _show_inline_diff(old_str, new_str)
        elif tool_name == "file_write":
            file_path = tool_input.get("file_path", "")
            content = tool_input.get("content", "")
            console.print(f"  File: [cyan]{file_path}[/cyan]")
            console.print(f"  Size: {len(content)} chars")
        elif tool_name == "bash":
            cmd = tool_input.get("command", "")
            console.print(f"  Command: [bold]{cmd}[/bold]")
        else:
            summary = _summarize_tool_input(tool_name, tool_input)
            if summary:
                console.print(f"  [dim]{summary}[/dim]")

        response = console.input("[yellow]Allow? (y/n/always): [/yellow]").strip().lower()
        return response in ("y", "yes", "a", "always")


def _show_inline_diff(old: str, new: str) -> None:
    """Show a compact inline diff for file edit permission preview."""
    import difflib

    old_lines = old.splitlines(keepends=True)
    new_lines = new.splitlines(keepends=True)
    diff = "".join(difflib.unified_diff(old_lines, new_lines, n=2))
    if diff:
        if len(diff) > 1500:
            diff = diff[:1500] + "\n... (preview truncated)"
        console.print(Syntax(diff, "diff", theme="monokai", word_wrap=True))


def _summarize_tool_input(tool_name: str, tool_input: dict) -> str:
    """Create a compact summary of tool input for display."""
    if tool_name == "bash":
        return tool_input.get("command", "")[:100]
    elif tool_name == "file_read":
        return tool_input.get("file_path", "")
    elif tool_name in ("file_write", "file_edit"):
        return tool_input.get("file_path", "")
    elif tool_name == "grep":
        path = tool_input.get("path", ".")
        return f"/{tool_input.get('pattern', '')}/ in {path}"
    elif tool_name == "glob":
        return tool_input.get("pattern", "")
    elif tool_name in ("web_search",):
        return tool_input.get("query", "")[:100]
    elif tool_name in ("web_fetch",):
        return tool_input.get("url", "")[:100]
    else:
        # MCP or unknown: show compact JSON
        try:
            return json.dumps(tool_input, default=str)[:100]
        except Exception:
            return ""
