"""Rich-based terminal UI for the agent."""

from __future__ import annotations

import json

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
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
                f"Session: {session_id}",
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
            style = "red" if is_error else "green"
            title = f"{'Error' if is_error else 'Result'}: {event.get('name', '')}"

            # Truncate for display
            if len(output) > 3000:
                output = output[:3000] + "\n... (truncated for display)"

            console.print(
                Panel(
                    output,
                    title=title,
                    style=style,
                    width=min(100, console.width),
                )
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
        summary = _summarize_tool_input(tool_name, tool_input)
        console.print(
            f"\n[yellow]Permission needed:[/yellow] {tool_name}"
        )
        if summary:
            console.print(f"  [dim]{summary}[/dim]")

        response = console.input("[yellow]Allow? (y/n): [/yellow]").strip().lower()
        return response in ("y", "yes")


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
    else:
        # MCP or unknown: show compact JSON
        try:
            return json.dumps(tool_input, default=str)[:100]
        except Exception:
            return ""
