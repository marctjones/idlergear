---
id: 1
title: Home
created: '2026-01-07T00:09:30.637197Z'
updated: '2026-01-07T00:09:30.637209Z'
---
# IdlerGear

**Structured project management for AI-assisted development.**

IdlerGear provides a command-based API that both humans and AI assistants can use to track work, capture knowledge, and maintain project context across sessions.

## The Problem

AI coding assistants are stateless. Every session starts fresh. You constantly re-explain:
- What the project is trying to achieve
- What you learned last session about how something works
- What issues were discovered but deferred
- What the current implementation plan is

## The Solution

A **command-based API** that manages project knowledge across sessions, machines, and teams.

```bash
idlergear vision show      # What is this project?
idlergear task list        # What needs to be done?
idlergear context          # Full project context for AI
```

## Quick Start

```bash
# Install
pipx install idlergear

# Initialize in your project
cd your-project
idlergear init

# Start using it
idlergear task create "Fix login bug" --label bug
idlergear note create "Parser has a quirk with compound words"
idlergear context  # Get full project context
```

See [[Getting-Started]] for detailed installation instructions.

## Key Features

### Six Knowledge Types

IdlerGear organizes project knowledge into six categories:

| Type | Purpose | GitHub Sync |
|------|---------|-------------|
| **Tasks** | Work to be done | GitHub Issues |
| **Notes** | Quick capture, ideas | Issues with label |
| **Vision** | Project direction | VISION.md file |
| **Plans** | Implementation phases | GitHub Projects |
| **References** | Documentation | GitHub Wiki |
| **Runs** | Script execution logs | Local only |

See [[Knowledge-Types]] for details on each type.

### AI-First Design

- **MCP Server** - 90+ tools for AI assistants
- **Token-efficient** - Structured queries save 97% of context tokens
- **Session continuity** - State persists across AI sessions
- **Multi-agent** - Multiple AI assistants can coordinate

### Backend Flexibility

Same commands, configurable storage:

```bash
# Use GitHub Issues for tasks
idlergear config set backend.task github

# Use local files for references
idlergear config set backend.reference local
```

## Documentation

- [[Getting-Started]] - Installation and setup
- [[Commands-Reference]] - All CLI commands
- [[Knowledge-Types]] - The six knowledge types
- [[Architecture]] - System design
- [[MCP-Server]] - AI tool integration
- [[GitHub-Integration]] - Syncing with GitHub

## Why Not Just Use Files?

AGENTS.md defines **file conventions** in prose:
> "Look for the vision in docs/VISION.md"

IdlerGear provides a **structured API**:
```bash
idlergear vision show    # Returns the vision, wherever it's stored
```

Benefits:
- **Consistent interface** - Same commands across all projects
- **Backend-agnostic** - Could be local, GitHub, Jira, etc.
- **Write capability** - AI can store knowledge, not just read it
- **Token-efficient** - Structured data, not markdown parsing

## Cross-Assistant Support

IdlerGear works identically across:
- Claude Code
- Block's Goose
- Aider
- GitHub Copilot CLI
- Gemini CLI
- Any MCP-compatible assistant

## Getting Help

- [GitHub Issues](https://github.com/marctjones/idlergear/issues) - Bug reports and feature requests
- [[Commands-Reference]] - Full command documentation
