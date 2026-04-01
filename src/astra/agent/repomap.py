"""Repository map — AST-based codebase indexing with symbol extraction."""

from __future__ import annotations

import ast
import asyncio
from pathlib import Path
from typing import Any


async def generate_repo_map(cwd: str, max_tokens: int = 2000) -> str:
    """Generate a concise map of the repository: file tree + key symbols."""
    root = Path(cwd)

    # Collect files (exclude common non-source dirs)
    skip_dirs = {
        ".git", "node_modules", "__pycache__", ".venv", "venv",
        ".tox", ".mypy_cache", ".pytest_cache", ".eggs", "dist",
        "build", ".next", "target", "vendor", ".claude",
    }
    skip_extensions = {
        ".pyc", ".pyo", ".so", ".o", ".a", ".dylib",
        ".jpg", ".jpeg", ".png", ".gif", ".ico", ".svg",
        ".woff", ".woff2", ".ttf", ".eot",
        ".zip", ".tar", ".gz", ".bz2",
        ".lock", ".map",
    }

    source_files: list[Path] = []
    for p in sorted(root.rglob("*")):
        if any(part in skip_dirs for part in p.parts):
            continue
        if p.is_file() and p.suffix not in skip_extensions:
            source_files.append(p)

    if not source_files:
        return "(empty repository)"

    # Build file tree
    lines = ["# Repository Map", ""]

    # File tree section
    lines.append("## Files")
    for f in source_files[:200]:  # Cap at 200 files
        rel = f.relative_to(root)
        indent = "  " * (len(rel.parts) - 1)
        lines.append(f"{indent}{rel.name}")

    # Python symbol extraction
    py_files = [f for f in source_files if f.suffix == ".py"]
    if py_files:
        lines.append("")
        lines.append("## Key Symbols")
        for py_file in py_files[:50]:  # Cap at 50 Python files
            symbols = _extract_python_symbols(py_file)
            if symbols:
                rel = py_file.relative_to(root)
                lines.append(f"\n### {rel}")
                for sym in symbols:
                    lines.append(f"  {sym}")

    # JS/TS symbol extraction
    ts_files = [f for f in source_files if f.suffix in (".ts", ".tsx", ".js", ".jsx")]
    if ts_files:
        for ts_file in ts_files[:50]:
            symbols = _extract_js_symbols(ts_file)
            if symbols:
                rel = ts_file.relative_to(root)
                lines.append(f"\n### {rel}")
                for sym in symbols:
                    lines.append(f"  {sym}")

    result = "\n".join(lines)

    # Rough truncation to stay within token budget (4 chars ~ 1 token)
    max_chars = max_tokens * 4
    if len(result) > max_chars:
        result = result[:max_chars] + "\n... (truncated)"

    return result


def _extract_python_symbols(filepath: Path) -> list[str]:
    """Extract classes, functions, and key assignments from a Python file."""
    try:
        source = filepath.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(source)
    except (SyntaxError, UnicodeDecodeError, PermissionError, OSError):
        return []

    symbols = []
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ClassDef):
            bases = ", ".join(
                _ast_name(b) for b in node.bases
            )
            symbols.append(f"class {node.name}({bases})" if bases else f"class {node.name}")
            # Get methods
            for item in node.body:
                if isinstance(item, ast.FunctionDef | ast.AsyncFunctionDef):
                    args = _format_args(item.args)
                    prefix = "async " if isinstance(item, ast.AsyncFunctionDef) else ""
                    symbols.append(f"  {prefix}def {item.name}({args})")
        elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            args = _format_args(node.args)
            prefix = "async " if isinstance(node, ast.AsyncFunctionDef) else ""
            symbols.append(f"{prefix}def {node.name}({args})")
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id.isupper():
                    symbols.append(f"{target.id} = ...")

    return symbols


def _ast_name(node: ast.expr) -> str:
    """Convert an AST node to a readable name string."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        value = _ast_name(node.value)
        return f"{value}.{node.attr}"
    if isinstance(node, ast.Subscript):
        value = _ast_name(node.value)
        slice_val = _ast_name(node.slice) if isinstance(node.slice, ast.expr) else "..."
        return f"{value}[{slice_val}]"
    if isinstance(node, ast.Constant):
        return repr(node.value)
    return "..."


def _format_args(args: ast.arguments) -> str:
    """Format function arguments concisely."""
    parts = []
    for arg in args.args:
        if arg.arg == "self" or arg.arg == "cls":
            continue
        parts.append(arg.arg)
    if len(parts) > 4:
        return ", ".join(parts[:3]) + ", ..."
    return ", ".join(parts)


def _extract_js_symbols(filepath: Path) -> list[str]:
    """Extract exports, classes, functions from JS/TS files (regex-based)."""
    import re
    try:
        source = filepath.read_text(encoding="utf-8", errors="replace")
    except (PermissionError, OSError):
        return []

    symbols = []
    # Match exported functions and classes
    for match in re.finditer(
        r"export\s+(?:default\s+)?(?:async\s+)?(?:function|class)\s+(\w+)",
        source,
    ):
        symbols.append(match.group(0).strip())

    # Match exported const/let
    for match in re.finditer(
        r"export\s+(?:const|let|var)\s+(\w+)",
        source,
    ):
        symbols.append(f"export {match.group(1)}")

    # Match interface/type exports
    for match in re.finditer(
        r"export\s+(?:interface|type)\s+(\w+)",
        source,
    ):
        symbols.append(f"export type {match.group(1)}")

    return symbols[:20]  # Cap per file
