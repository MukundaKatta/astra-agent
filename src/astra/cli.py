"""Astra Agent CLI — Click-based command-line interface."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import click

from astra.config import AstraConfig, PermissionMode


@click.group(invoke_without_command=True)
@click.option("--model", "-m", default=None, help="Model to use (default: claude-sonnet-4-20250514)")
@click.option(
    "--permission-mode",
    "-p",
    type=click.Choice(["default", "auto", "bypass"]),
    default="default",
    help="Permission mode for tool execution",
)
@click.option("--cwd", type=click.Path(exists=True), default=None, help="Working directory")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
@click.option("--no-thinking", is_flag=True, help="Disable extended thinking")
@click.option("--prompt", help="Single prompt (non-interactive mode)")
@click.option("--resume", "-r", "session_id", default=None, help="Resume a session by ID")
@click.version_option(version="0.1.0", prog_name="astra")
@click.pass_context
def main(ctx, model, permission_mode, cwd, verbose, no_thinking, prompt, session_id):
    """Astra Agent - AI coding assistant powered by Claude."""
    config = AstraConfig(
        model=model or AstraConfig.model,
        permission_mode=PermissionMode(permission_mode),
        cwd=Path(cwd) if cwd else Path.cwd(),
        verbose=verbose,
        thinking=not no_thinking,
    )

    if ctx.invoked_subcommand is None:
        if prompt:
            asyncio.run(_run_single(config, prompt))
        elif session_id:
            asyncio.run(_run_interactive(config, session_id=session_id))
        else:
            asyncio.run(_run_interactive(config))


@main.command()
def sessions():
    """List saved sessions."""
    from astra.session.storage import SessionStorage

    storage = SessionStorage()
    saved = storage.list_sessions()
    if not saved:
        click.echo("No saved sessions found.")
        return
    for s in saved[:20]:
        click.echo(f"  {s['id']}  ({s['saved_at']})")


async def _run_interactive(
    config: AstraConfig, session_id: str | None = None
) -> None:
    """Main interactive REPL loop."""
    from astra.agent.engine import QueryEngine
    from astra.ui.console import AgentUI

    ui = AgentUI()

    try:
        if session_id:
            engine = await QueryEngine.resume(session_id, config)
        else:
            engine = QueryEngine(config)
            await engine.initialize()
    except Exception as e:
        ui.print_error(f"Failed to initialize: {e}")
        sys.exit(1)

    # Wire up permission callback
    engine.on_permission_request = ui.ask_permission

    ui.print_welcome(engine.session_id, config.model, len(engine.tools.all_tools()))

    try:
        while True:
            try:
                user_input = ui.prompt_user()
            except (EOFError, KeyboardInterrupt):
                print()
                break

            stripped = user_input.strip()
            if not stripped:
                continue

            # Handle slash commands
            if stripped in ("/exit", "/quit", "/q"):
                break
            if stripped == "/save":
                path = await engine.save_session()
                click.echo(f"Session saved: {path}")
                continue
            if stripped == "/usage":
                ui.print_usage(engine.usage.summary())
                continue
            if stripped == "/help":
                _print_help()
                continue

            # Submit to engine
            try:
                async for event in engine.submit_message(user_input):
                    ui.handle_stream_event(event)
                ui.print_usage(engine.usage.summary())
            except KeyboardInterrupt:
                click.echo("\n[interrupted]")
            except Exception as e:
                ui.print_error(str(e))

    finally:
        try:
            await engine.save_session()
        except Exception:
            pass
        await engine.shutdown()
        click.echo("Goodbye!")


async def _run_single(config: AstraConfig, prompt: str) -> None:
    """Non-interactive: single prompt, print result, exit."""
    from astra.agent.engine import QueryEngine
    from astra.ui.console import AgentUI

    engine = QueryEngine(config)
    await engine.initialize()
    ui = AgentUI()

    try:
        async for event in engine.submit_message(prompt):
            ui.handle_stream_event(event)
        ui.print_usage(engine.usage.summary())
    except Exception as e:
        ui.print_error(str(e))
        sys.exit(1)
    finally:
        await engine.shutdown()


def _print_help() -> None:
    click.echo(
        """
Commands:
  /exit, /quit, /q   Exit the agent
  /save              Save the current session
  /usage             Show token usage and cost
  /help              Show this help message
"""
    )


if __name__ == "__main__":
    main()
