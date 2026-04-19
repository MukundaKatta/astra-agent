# Astra Agent

> *Astra* (Sanskrit: "tool/weapon") — An AI coding agent built from studying the best.

## What It Is

Astra Agent is a next-generation AI coding agent, informed by deep analysis of production agent architectures. It features an async generator-based agent loop, pluggable tool system, MCP client integration, file-based memory, and a Rich-powered CLI.

The project is aimed at builders who want to understand and experiment with the architecture of coding agents rather than treat them as black boxes. It is both a usable prototype and a learning-oriented implementation shaped by studying real production patterns.

## Why Astra

Coding agents are becoming a serious part of developer tooling, but most people only see the surface experience. Astra focuses on the underlying mechanics:

- how the agent loop streams and recovers
- how tools are modeled and executed
- how MCP servers are bridged into the same tool system
- how sessions, permissions, and memory fit into a practical CLI workflow

## Current Status

Astra Agent already has a real codebase, CLI entrypoint, core runtime structure, and working architectural slices in place.

It is still early, but it is beyond a pure idea repo: the current value is in the implementation approach, the code organization, and the reference-driven design decisions that shape the next iterations.

## Quick Start

```bash
# Install
pip install -e .

# Run interactive mode
astra

# Single prompt
astra --prompt "What files are in this directory?"

# With auto-approve permissions
astra -p auto

# Resume a session
astra -r <session-id>
```

## Architecture

```
cli.py (Click REPL)
  -> agent/engine.py (QueryEngine: stateful session wrapper)
       -> agent/query.py (async generator agent loop)
            -> tools/* (bash, file_read/write/edit, grep, glob)
            -> mcp/bridge.py (MCP tools as regular tools)
       -> agent/context.py (system prompt builder)
       -> memory/prompt.py (memory injection)
       -> session/storage.py (JSON persistence)
  -> ui/console.py (Rich terminal output)
  -> mcp/client.py (MCP server connections)
```

### Core Design Patterns

| Pattern | Description |
|---------|-------------|
| **Async Generator Agent Loop** | `query()` yields stream events, handles tool calls, recovery, and loops until done |
| **Tool ABC + Registry** | Each tool is a class with `name`, `description`, `input_schema`, `call()` |
| **MCP Bridge** | MCP server tools wrapped as `MCPBridgeTool` and registered alongside built-in tools |
| **Permission Modes** | `default` (ask for writes), `auto` (allow all), `bypass` (skip checks) |
| **File-Based Memory** | YAML frontmatter `.md` files with `MEMORY.md` index, injected into system prompt |
| **Session Persistence** | JSON snapshots of conversation + usage, resumable via `--resume` |

## What Makes It Interesting

- It treats MCP as a first-class extension path instead of an afterthought.
- It keeps the agent loop explicit and inspectable.
- It emphasizes architecture and code readability, not just flashy demos.
- It acts as a bridge between production agent ideas and a smaller experimental codebase.

## Project Structure

```
src/astra/
├── __init__.py, __main__.py
├── cli.py                    # Click CLI with REPL + single-prompt modes
├── config.py                 # AstraConfig frozen dataclass
├── types.py                  # ToolResult, Usage, StopReason, StreamEvent
├── agent/
│   ├── query.py              # Core agent loop (async generator)
│   ├── engine.py             # QueryEngine (stateful session wrapper)
│   └── context.py            # System prompt builder
├── tools/
│   ├── __init__.py           # ToolRegistry + build_default_registry()
│   ├── base.py               # Tool ABC
│   ├── bash.py               # Shell command execution
│   ├── file_read.py          # Read files with line numbers
│   ├── file_write.py         # Create/overwrite files
│   ├── file_edit.py          # String replacement edits
│   ├── grep.py               # Regex search (ripgrep/grep)
│   └── glob.py               # File pattern matching
├── mcp/
│   ├── config.py             # Load .mcp.json configs
│   ├── client.py             # MCPManager (connect, discover, call)
│   └── bridge.py             # MCPBridgeTool adapter
├── memory/
│   ├── types.py              # MemoryType enum, Memory dataclass
│   ├── store.py              # MemoryStore CRUD
│   └── prompt.py             # Memory prompt injection
├── permissions/
│   └── checker.py            # 3-mode permission system
├── session/
│   ├── storage.py            # JSON session persistence
│   └── usage.py              # Token/cost tracking
└── ui/
    └── console.py            # Rich-based streaming UI
```

## Built-in Tools

| Tool | Description |
|------|-------------|
| `bash` | Execute shell commands with timeout support |
| `file_read` | Read files with line numbers, offset/limit support |
| `file_write` | Create or overwrite files |
| `file_edit` | Find-and-replace exact string edits |
| `grep` | Regex search via ripgrep (falls back to grep) |
| `glob` | File pattern matching |

## MCP Integration

Create a `.mcp.json` in your project root:

```json
{
  "mcpServers": {
    "my-server": {
      "command": "npx",
      "args": ["-y", "@some/mcp-server"]
    }
  }
}
```

MCP tools are automatically discovered and available as `mcp__servername__toolname`.

## Reference Codebases

This project was informed by analysis of:

### 1. Claude Code Source (`reference/claude-code-main/`)
Anthropic's production AI coding CLI (TypeScript/React/Ink), featuring 40+ tools, async generator agent loop, multi-agent coordination, and auto-dream memory consolidation.

### 2. Claw Code Port (`reference/claw-code-main/`)
Python clean-room reimplementation by Sigrid Jin, mirroring 207 commands and 100+ tools as metadata/shims.

### 3. Raw Source (`reference/cld-raw/`)
Pure TypeScript `src/` directory from the npm sourcemap.

### Analysis Document
See `docs/Claude-Code-Deep-Dive-Analysis.docx` for the comprehensive architecture analysis.

## Roadmap

- [x] Collect and organize reference codebases
- [x] Deep dive analysis document
- [x] Design Astra Agent architecture (inspired by patterns above)
- [x] Build core agent loop in Python
- [x] Implement tool system with plugin support
- [x] Add MCP client integration
- [x] Memory/context management system
- [x] CLI interface
- [x] First working prototype
- [ ] Tests and CI
- [ ] Context compaction (auto-compact on token budget)
- [ ] Multi-agent coordinator mode
- [ ] Plugin system for custom tools

## Who This Is For

- developers studying coding-agent internals
- builders experimenting with MCP-enabled agent workflows
- people who want a smaller reference implementation instead of a massive framework
- anyone interested in practical agent architecture patterns

## Author

**Mukunda** — ML Engineer | AWS + ML/AI + Python
