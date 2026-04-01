"""Slash command system — structured commands for common operations."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Coroutine

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

console = Console()


@dataclass
class CommandResult:
    output: str
    should_send_to_model: bool = False  # If True, output becomes a prompt


# Registry of all commands
COMMANDS: dict[str, Callable] = {}


def command(name: str, help_text: str):
    """Decorator to register a slash command."""
    def decorator(func):
        func._help = help_text
        COMMANDS[name] = func
        return func
    return decorator


@command("help", "Show available commands")
async def cmd_help(args: str, engine: Any) -> CommandResult:
    table = Table(title="Commands", show_header=True, header_style="bold cyan")
    table.add_column("Command", style="green")
    table.add_column("Description")
    for name, func in sorted(COMMANDS.items()):
        table.add_row(f"/{name}", func._help)
    console.print(table)
    return CommandResult("")


@command("exit", "Exit the agent")
async def cmd_exit(args: str, engine: Any) -> CommandResult:
    raise SystemExit(0)


@command("quit", "Exit the agent")
async def cmd_quit(args: str, engine: Any) -> CommandResult:
    raise SystemExit(0)


@command("save", "Save the current session")
async def cmd_save(args: str, engine: Any) -> CommandResult:
    path = await engine.save_session()
    return CommandResult(f"Session saved: {path}")


@command("usage", "Show token usage and cost")
async def cmd_usage(args: str, engine: Any) -> CommandResult:
    return CommandResult(engine.usage.summary())


@command("tokens", "Show token usage breakdown")
async def cmd_tokens(args: str, engine: Any) -> CommandResult:
    u = engine.usage.total
    lines = [
        f"Input tokens:  {u.input_tokens:>10,}",
        f"Output tokens: {u.output_tokens:>10,}",
        f"Cache create:  {u.cache_creation_input_tokens:>10,}",
        f"Cache read:    {u.cache_read_input_tokens:>10,}",
        f"Messages:      {len(engine.messages):>10}",
        f"Est. cost:     ${engine.usage.estimated_cost_usd:>9.4f}",
    ]
    console.print(Panel("\n".join(lines), title="Token Usage"))
    return CommandResult("")


@command("clear", "Clear conversation history (start fresh)")
async def cmd_clear(args: str, engine: Any) -> CommandResult:
    from astra.session.usage import UsageTracker
    engine.messages.clear()
    engine.usage = UsageTracker()  # Reset usage tracker
    return CommandResult("Conversation cleared.")


@command("compact", "Compact conversation to save context window")
async def cmd_compact(args: str, engine: Any) -> CommandResult:
    from astra.agent.compaction import compact_messages
    before = len(engine.messages)
    engine.messages = compact_messages(engine.messages)
    after = len(engine.messages)
    return CommandResult(f"Compacted: {before} -> {after} messages")


@command("diff", "Show git diff of recent changes")
async def cmd_diff(args: str, engine: Any) -> CommandResult:
    cwd = str(engine.config.cwd)
    proc = await asyncio.create_subprocess_exec(
        "git", "diff", "--stat",
        *(args.split() if args else []),
        cwd=cwd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=10)
    if proc.returncode != 0:
        return CommandResult(f"Git error: {stderr.decode()}")

    stat = stdout.decode().strip()
    if not stat:
        return CommandResult("No changes.")

    # Also get the actual diff
    proc2 = await asyncio.create_subprocess_exec(
        "git", "diff", *(args.split() if args else []),
        cwd=cwd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout2, _ = await asyncio.wait_for(proc2.communicate(), timeout=10)
    diff_text = stdout2.decode().strip()

    console.print(Panel(stat, title="Git Diff Summary"))
    if diff_text:
        # Truncate long diffs
        if len(diff_text) > 5000:
            diff_text = diff_text[:5000] + "\n... (truncated)"
        console.print(Syntax(diff_text, "diff", theme="monokai"))
    return CommandResult("")


@command("undo", "Undo the last git commit (soft reset)")
async def cmd_undo(args: str, engine: Any) -> CommandResult:
    cwd = str(engine.config.cwd)
    # Check if there's a commit to undo
    proc = await asyncio.create_subprocess_exec(
        "git", "log", "--oneline", "-1",
        cwd=cwd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5)
    if proc.returncode != 0:
        return CommandResult("Not in a git repository.")

    last_commit = stdout.decode().strip()
    console.print(f"[yellow]Undoing:[/yellow] {last_commit}")

    response = console.input("[yellow]Are you sure? (y/n): [/yellow]").strip().lower()
    if response not in ("y", "yes"):
        return CommandResult("Undo cancelled.")

    proc = await asyncio.create_subprocess_exec(
        "git", "reset", "--soft", "HEAD~1",
        cwd=cwd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await asyncio.wait_for(proc.communicate(), timeout=5)
    if proc.returncode != 0:
        return CommandResult(f"Undo failed: {stderr.decode()}")
    return CommandResult(f"Undid commit: {last_commit}")


@command("commit", "Auto-commit changes with a conventional message")
async def cmd_commit(args: str, engine: Any) -> CommandResult:
    message = args.strip() if args.strip() else None
    if not message:
        # Ask model to generate commit message
        return CommandResult(
            "Look at the current git diff and generate a concise conventional commit "
            "message, then run `git add -A && git commit -m '<message>'`.",
            should_send_to_model=True,
        )
    cwd = str(engine.config.cwd)
    proc = await asyncio.create_subprocess_exec(
        "git", "add", "-A",
        cwd=cwd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    await asyncio.wait_for(proc.communicate(), timeout=10)
    proc = await asyncio.create_subprocess_exec(
        "git", "commit", "-m", message,
        cwd=cwd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=10)
    output = stdout.decode().strip() or stderr.decode().strip()
    return CommandResult(output)


@command("test", "Run tests and report results")
async def cmd_test(args: str, engine: Any) -> CommandResult:
    return CommandResult(
        f"Run the project's tests{' with: ' + args if args else ''} and report results. "
        "If tests fail, analyze the failures and suggest fixes.",
        should_send_to_model=True,
    )


@command("lint", "Run linter and fix issues")
async def cmd_lint(args: str, engine: Any) -> CommandResult:
    return CommandResult(
        f"Run the project's linter{' with: ' + args if args else ''} and fix any issues found. "
        "Auto-detect the linter from project config (e.g., ruff, black, eslint, pylint).",
        should_send_to_model=True,
    )


@command("fix", "Fix errors or issues")
async def cmd_fix(args: str, engine: Any) -> CommandResult:
    issue = args.strip() or "the last error"
    return CommandResult(
        f"Analyze and fix: {issue}. Read relevant files, identify the root cause, "
        "and apply a fix.",
        should_send_to_model=True,
    )


@command("plan", "Create a plan before implementing")
async def cmd_plan(args: str, engine: Any) -> CommandResult:
    task = args.strip() or "the current task"
    return CommandResult(
        f"Create a detailed implementation plan for: {task}. "
        "List the files to modify, the changes needed, and the order of operations. "
        "Do NOT make any changes yet — just plan.",
        should_send_to_model=True,
    )


@command("ask", "Ask a question without making changes")
async def cmd_ask(args: str, engine: Any) -> CommandResult:
    question = args.strip()
    if not question:
        return CommandResult("Usage: /ask <question>")
    return CommandResult(
        f"Answer this question about the codebase (do NOT make any changes): {question}",
        should_send_to_model=True,
    )


@command("model", "Show or switch the model")
async def cmd_model(args: str, engine: Any) -> CommandResult:
    if not args.strip():
        return CommandResult(f"Current model: {engine.config.model}")
    new_model = args.strip()
    # Update config (create new frozen config)
    from dataclasses import replace
    old_model = engine.config.model
    engine.config = replace(engine.config, model=new_model)
    # Rebuild system prompt to reflect updated config
    try:
        from astra.agent.context import build_system_prompt
        engine._system_prompt = await build_system_prompt(
            cwd=str(engine.config.cwd),
            tools=engine.tools,
            memory_dir=engine.config.memory_dir,
        )
    except Exception:
        pass  # Non-critical — prompt will be rebuilt on next init
    return CommandResult(f"Switched model: {old_model} -> {new_model}")


@command("map", "Show repository map (file structure + key symbols)")
async def cmd_map(args: str, engine: Any) -> CommandResult:
    from astra.agent.repomap import generate_repo_map
    cwd = str(engine.config.cwd)
    repo_map = await generate_repo_map(cwd, max_tokens=2000)
    console.print(Panel(repo_map, title="Repository Map"))
    return CommandResult("")


@command("files", "List files in context or working directory")
async def cmd_files(args: str, engine: Any) -> CommandResult:
    cwd = str(engine.config.cwd)
    proc = await asyncio.create_subprocess_exec(
        "find", cwd, "-maxdepth", "3", "-type", "f",
        "-not", "-path", "*/.git/*",
        "-not", "-path", "*/node_modules/*",
        "-not", "-path", "*/__pycache__/*",
        "-not", "-path", "*/.venv/*",
        cwd=cwd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=10)
    files = stdout.decode().strip()
    lines = files.split("\n")
    if len(lines) > 100:
        files = "\n".join(lines[:100]) + f"\n... ({len(lines) - 100} more)"
    console.print(Panel(files, title=f"Files ({len(lines)})"))
    return CommandResult("")


def parse_command(user_input: str) -> tuple[str, str] | None:
    """Parse a slash command. Returns (command_name, args) or None."""
    stripped = user_input.strip()
    if not stripped.startswith("/"):
        return None
    rest = stripped[1:].strip()
    if not rest:
        return None  # bare "/" is not a command
    parts = rest.split(None, 1)
    cmd_name = parts[0].lower()
    args = parts[1] if len(parts) > 1 else ""
    if cmd_name in COMMANDS:
        return (cmd_name, args)
    return None


async def execute_command(cmd_name: str, args: str, engine: Any) -> CommandResult:
    """Execute a slash command."""
    func = COMMANDS.get(cmd_name)
    if not func:
        return CommandResult(f"Unknown command: /{cmd_name}")
    return await func(args, engine)
