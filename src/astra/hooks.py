"""Post-tool hooks — auto-lint, auto-test, and custom hooks after tool execution."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class HookResult:
    hook_name: str
    success: bool
    output: str


@dataclass
class HookConfig:
    """Configuration for post-tool hooks."""
    auto_lint: bool = False
    auto_test: bool = False
    lint_command: str | None = None
    test_command: str | None = None
    custom_hooks: list[dict[str, str]] = field(default_factory=list)

    @classmethod
    def from_file(cls, path: Path) -> HookConfig:
        """Load hook config from .astra-hooks.json."""
        if not path.exists():
            return cls()
        try:
            data = json.loads(path.read_text())
            return cls(
                auto_lint=data.get("auto_lint", False),
                auto_test=data.get("auto_test", False),
                lint_command=data.get("lint_command"),
                test_command=data.get("test_command"),
                custom_hooks=data.get("custom_hooks", []),
            )
        except Exception:
            return cls()


async def run_post_edit_hooks(
    file_path: str,
    cwd: str,
    hook_config: HookConfig,
) -> list[HookResult]:
    """Run configured hooks after a file edit."""
    results = []

    if not hook_config.auto_lint and not hook_config.auto_test:
        return results

    path = Path(file_path)

    # Auto-lint
    if hook_config.auto_lint:
        lint_cmd = hook_config.lint_command or _detect_linter(cwd, path)
        if lint_cmd:
            result = await _run_hook("auto-lint", lint_cmd, cwd)
            results.append(result)

    # Auto-test (only run if lint passed or no lint)
    if hook_config.auto_test:
        test_cmd = hook_config.test_command or _detect_test_runner(cwd, path)
        if test_cmd:
            result = await _run_hook("auto-test", test_cmd, cwd)
            results.append(result)

    return results


async def _run_hook(name: str, command: str, cwd: str) -> HookResult:
    """Execute a hook command."""
    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)
        output = stdout.decode("utf-8", errors="replace")
        if stderr:
            output += "\n" + stderr.decode("utf-8", errors="replace")
        # Truncate
        if len(output) > 5000:
            output = output[:5000] + "\n... (truncated)"
        return HookResult(
            hook_name=name,
            success=proc.returncode == 0,
            output=output.strip(),
        )
    except asyncio.TimeoutError:
        return HookResult(hook_name=name, success=False, output="Hook timed out (60s)")
    except Exception as e:
        return HookResult(hook_name=name, success=False, output=str(e))


def _detect_linter(cwd: str, file_path: Path) -> str | None:
    """Auto-detect the linter for the project."""
    root = Path(cwd)
    suffix = file_path.suffix

    if suffix == ".py":
        if (root / "ruff.toml").exists() or (root / ".ruff.toml").exists():
            return f"ruff check --fix {file_path}"
        if (root / "pyproject.toml").exists():
            content = (root / "pyproject.toml").read_text()
            if "ruff" in content:
                return f"ruff check --fix {file_path}"
            if "black" in content:
                return f"black {file_path}"
        return None

    if suffix in (".js", ".jsx", ".ts", ".tsx"):
        if (root / ".eslintrc.json").exists() or (root / ".eslintrc.js").exists():
            return f"npx eslint --fix {file_path}"
        if (root / "biome.json").exists():
            return f"npx biome check --apply {file_path}"
        return None

    return None


def _detect_test_runner(cwd: str, file_path: Path) -> str | None:
    """Auto-detect test runner for the project."""
    root = Path(cwd)
    suffix = file_path.suffix

    if suffix == ".py":
        if (root / "pytest.ini").exists() or (root / "pyproject.toml").exists():
            return "python -m pytest --tb=short -q"
        return None

    if suffix in (".js", ".jsx", ".ts", ".tsx"):
        if (root / "jest.config.js").exists() or (root / "jest.config.ts").exists():
            return "npx jest --bail"
        if (root / "vitest.config.ts").exists():
            return "npx vitest run"
        return None

    return None
