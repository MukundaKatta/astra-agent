# Astra Agent

> *Astra* (Sanskrit: "tool/weapon") — An AI coding agent built from studying the best.

## What is this?

Astra Agent is a next-generation AI coding agent, informed by deep analysis of production agent architectures. It features an async generator-based agent loop, pluggable tool system, MCP client integration, file-based memory, and a Rich-powered CLI.

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
cli.py (Click REPL + slash commands)
  -> commands.py (19 slash commands: /diff, /undo, /commit, /plan, etc.)
  -> agent/engine.py (QueryEngine: stateful session wrapper)
       -> agent/query.py (async generator agent loop)
            -> tools/* (bash, file_read/write/edit, grep, glob, web_search, web_fetch)
            -> mcp/bridge.py (MCP tools as regular tools)
       -> agent/context.py (system prompt builder)
       -> agent/compaction.py (context compaction)
       -> agent/repomap.py (AST-based codebase indexing)
       -> memory/prompt.py (memory injection)
       -> session/storage.py (JSON persistence)
  -> providers/* (multi-model: Anthropic, OpenAI, Ollama/local)
  -> hooks.py (auto-lint, auto-test after edits)
  -> ui/console.py (Rich terminal output with diff highlighting)
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

## Project Structure

```
src/astra/
├── __init__.py, __main__.py
├── cli.py                    # Click CLI with REPL + slash command integration
├── commands.py               # 19 slash commands (/diff, /undo, /commit, /plan, etc.)
├── config.py                 # AstraConfig frozen dataclass
├── hooks.py                  # Auto-lint, auto-test post-edit hooks
├── types.py                  # ToolResult, Usage, StopReason, StreamEvent
├── agent/
│   ├── query.py              # Core agent loop (async generator)
│   ├── engine.py             # QueryEngine (stateful session wrapper)
│   ├── context.py            # System prompt builder
│   ├── compaction.py         # Context compaction (summarize old messages)
│   └── repomap.py            # AST-based repo map with symbol extraction
├── tools/
│   ├── __init__.py           # ToolRegistry + build_default_registry()
│   ├── base.py               # Tool ABC
│   ├── bash.py               # Shell command execution
│   ├── file_read.py          # Read files with line numbers
│   ├── file_write.py         # Create/overwrite files
│   ├── file_edit.py          # String replacement edits with diff output
│   ├── grep.py               # Regex search (ripgrep/grep)
│   ├── glob.py               # File pattern matching
│   ├── web_search.py         # DuckDuckGo web search (no API key)
│   └── web_fetch.py          # URL fetcher with HTML-to-text
├── providers/
│   ├── __init__.py           # Provider abstraction
│   ├── base.py               # LLMProvider ABC
│   ├── anthropic_provider.py # Claude models (primary)
│   ├── openai_provider.py    # OpenAI/Azure/Ollama/LM Studio
│   └── registry.py           # Auto-detect provider from model name
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
    └── console.py            # Rich UI with diff highlighting + permission preview
```

## Built-in Tools

| Tool | Description |
|------|-------------|
| `bash` | Execute shell commands with timeout support |
| `file_read` | Read files with line numbers, offset/limit support |
| `file_write` | Create or overwrite files |
| `file_edit` | Find-and-replace exact string edits with unified diff output |
| `grep` | Regex search via ripgrep (falls back to grep) |
| `glob` | File pattern matching |
| `web_search` | DuckDuckGo search (no API key required) |
| `web_fetch` | Fetch URLs with HTML-to-text conversion |

## Slash Commands

| Command | Description |
|---------|-------------|
| `/help` | Show all available commands |
| `/exit`, `/quit` | Exit the agent |
| `/save` | Save the current session |
| `/usage`, `/tokens` | Show token usage and cost |
| `/clear` | Clear conversation history |
| `/compact` | Compact old messages to save context |
| `/diff` | Show git diff of recent changes |
| `/undo` | Undo last git commit (soft reset) |
| `/commit [msg]` | Auto-commit with conventional message |
| `/test [args]` | Run project tests |
| `/lint [args]` | Run linter and fix issues |
| `/fix [issue]` | Analyze and fix errors |
| `/plan [task]` | Create implementation plan (no changes) |
| `/ask [question]` | Ask about codebase (no changes) |
| `/model [name]` | Show or switch the model |
| `/map` | Show repo structure with key symbols |
| `/files` | List files in working directory |

## Multi-Model Support

```bash
# Anthropic Claude (default)
astra -m claude-sonnet-4-20250514

# OpenAI (requires `pip install astra-agent[openai]`)
astra -m gpt-4o

# Ollama local models
astra -m ollama/llama3

# LM Studio
astra -m lmstudio/codestral
```

## Auto Hooks

```bash
# Auto-lint after file edits
astra --auto-lint

# Auto-test after file edits
astra --auto-test

# Both
astra --auto-lint --auto-test
```

Configure hooks via `.astra-hooks.json`:
```json
{
  "auto_lint": true,
  "auto_test": false,
  "lint_command": "ruff check --fix",
  "test_command": "pytest --tb=short -q"
}
```

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
- [x] Web search and fetch tools
- [x] Slash command system (19 commands)
- [x] Context compaction
- [x] Repo map with AST symbol extraction
- [x] Multi-model support (OpenAI, Ollama, LM Studio)
- [x] Auto-lint and auto-test hooks
- [x] Diff display for file edits
- [x] Interactive permission prompting with diff preview
- [ ] Tests and CI
- [ ] Multi-agent coordinator mode
- [ ] Plugin system for custom tools
- [ ] Conversation branching/forking
- [ ] Cost budgets and limits

## Author

**Mukunda** — ML Engineer | AWS + ML/AI + Python
