"""System prompt builder — assembles static + dynamic context for the agent."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from astra.tools import ToolRegistry


IDENTITY_PROMPT = """\
You are Astra, an AI coding agent built with the Anthropic Claude API. You help users \
with software development tasks by reading files, writing code, running commands, and \
managing projects.

Guidelines:
- Be direct and concise in your responses
- Use tools to explore the codebase before making changes
- Make targeted edits rather than rewriting entire files
- Run tests after making changes when appropriate
- Explain what you're doing and why when it's not obvious

You have access to tools for file operations (read, write, edit), search (grep, glob), \
and command execution (bash). Use them freely to accomplish tasks."""


async def build_system_prompt(
    *,
    cwd: str,
    tools: ToolRegistry,
    memory_dir: Path | None = None,
) -> str:
    """Assemble system prompt from static + dynamic sections."""
    sections: list[str] = [IDENTITY_PROMPT]

    # Tool list
    tool_names = [t.name for t in tools.all_tools()]
    sections.append(f"Available tools: {', '.join(tool_names)}")

    # Working directory
    sections.append(f"Current working directory: {cwd}")

    # Git info
    git_info = await _get_git_info(cwd)
    if git_info:
        sections.append(f"Git status:\n{git_info}")

    # Memory
    if memory_dir:
        mem_prompt = await _load_memory_prompt(memory_dir)
        if mem_prompt:
            sections.append(mem_prompt)

    # CLAUDE.md / ASTRA.md
    project_instructions = _load_project_instructions(cwd)
    if project_instructions:
        sections.append(f"Project instructions:\n{project_instructions}")

    return "\n\n".join(sections)


async def _get_git_info(cwd: str) -> str | None:
    """Get basic git info for context."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "git", "rev-parse", "--is-inside-work-tree",
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5)
        if proc.returncode != 0:
            return None

        # Get branch and status
        results = []
        for cmd in [
            ["git", "branch", "--show-current"],
            ["git", "status", "--short"],
        ]:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=cwd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5)
            if proc.returncode == 0:
                results.append(stdout.decode().strip())

        if results:
            parts = []
            if results[0]:
                parts.append(f"Branch: {results[0]}")
            if len(results) > 1 and results[1]:
                status = results[1]
                # Truncate long status
                lines = status.split("\n")
                if len(lines) > 20:
                    status = "\n".join(lines[:20]) + f"\n... ({len(lines) - 20} more)"
                parts.append(f"Status:\n{status}")
            return "\n".join(parts)
    except Exception:
        pass
    return None


async def _load_memory_prompt(memory_dir: Path) -> str | None:
    """Load memory index for prompt injection."""
    index = memory_dir / "MEMORY.md"
    if not index.exists():
        return None
    content = index.read_text(encoding="utf-8").strip()
    if not content:
        return None
    lines = content.split("\n")
    if len(lines) > 200:
        content = "\n".join(lines[:200]) + "\n... (truncated)"
    return f"Your Memory:\n{content}"


def _load_project_instructions(cwd: str) -> str | None:
    """Load ASTRA.md or CLAUDE.md from the project root."""
    for name in ["ASTRA.md", "CLAUDE.md"]:
        path = Path(cwd) / name
        if path.exists():
            content = path.read_text(encoding="utf-8").strip()
            if content:
                # Truncate if very long
                if len(content) > 10000:
                    content = content[:10000] + "\n... (truncated)"
                return content
    return None
