# Astra Agent

> *Astra* (Sanskrit: "tool/weapon") — An AI coding agent built from studying the best.

## What is this?

Astra Agent is a project to build a next-generation AI coding agent, informed by deep analysis of production agent architectures. This repo contains reference implementations from three sources, a comprehensive analysis document, and will evolve into an original agent framework.

## Repository Structure

```
astra-agent/
├── reference/
│   ├── claude-code-source/    # Original Claude Code TypeScript source (leaked via npm sourcemap)
│   ├── claw-code-port/        # Claw Code — Python clean-room reimplementation by Sigrid Jin
│   └── cld-raw/               # Raw TypeScript source extracted from the npm package
├── docs/
│   └── Claude-Code-Deep-Dive-Analysis.docx   # Comprehensive architecture analysis
└── README.md
```

## Reference Codebases

### 1. Claude Code Source (`reference/claude-code-source/`)
The full TypeScript source of Anthropic's Claude Code CLI, exposed on March 31, 2026 via a sourcemap file accidentally shipped in the npm package. Key highlights:

- **785KB main.tsx** entry point with React/Ink terminal rendering
- **40+ pluggable tools** (Bash, file ops, search, agents, MCP, web)
- **Async generator query loop** — the core agent reasoning engine
- **Multi-agent coordinator mode** for parallel worker orchestration
- **Auto-Dream memory system** — 4-phase background consolidation engine
- **Unreleased features**: KAIROS (always-on assistant), Buddy (Tamagotchi pet), Coordinator mode, ULTRAPLAN

### 2. Claw Code Port (`reference/claw-code-port/`)
A Python clean-room reimplementation by engineer Sigrid Jin, built using OpenAI Codex via oh-my-codex (OmX). Mirrors the architectural patterns:

- **66 Python files** across the core orchestration layer
- **207 mirrored commands** and **100+ mirrored tools** (as metadata/shims)
- Session management, prompt routing, turn loops, and permission system
- Comprehensive test suite (22 tests)

### 3. Raw Source (`reference/cld-raw/`)
The pure TypeScript `src/` directory extracted directly from the npm sourcemap — no wrapper repo, just the code.

## Key Architectural Patterns (from Analysis)

| Pattern | Description |
|---------|-------------|
| **Async Generator Agent Loop** | `query()` yields stream events, handles tool calls, recovery, and compaction in a single loop |
| **Tool Composability** | Consistent interface: schema, call(), permissions, progress, rendering |
| **Prompt Cache Optimization** | Static/dynamic boundary marker separates cacheable vs. session-specific prompt sections |
| **Feature Gating** | Compile-time (Bun `feature()`) + runtime (GrowthBook) flags for safe experimentation |
| **Dream Memory** | Background consolidation of session transcripts into durable CLAUDE.md files |
| **Coordinator/Worker** | Spawn parallel agents, notify on completion (no polling), shared scratchpad |

## Roadmap

- [x] Collect and organize reference codebases
- [x] Deep dive analysis document
- [ ] Design Astra Agent architecture (inspired by patterns above)
- [ ] Build core agent loop in Python
- [ ] Implement tool system with plugin support
- [ ] Add MCP client integration
- [ ] Memory/context management system
- [ ] CLI interface
- [ ] First working prototype

## Author

**Mukunda** — ML Engineer | AWS + ML/AI + Python
