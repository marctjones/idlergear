# IdlerGear Wiki

**IdlerGear is a knowledge management API that synchronizes AI context management with human project management.**

## Quick Navigation

- [[Getting Started]]
- [[Knowledge Types]]
- [[Commands Reference]]
- [[MCP Server]]
- [[GitHub Integration]]
- [[Architecture]]

## What is IdlerGear?

AI coding assistants are stateless. Every session starts fresh. IdlerGear provides a **command-based API** that manages knowledge across sessions, machines, and teams.

### Key Features (v0.2.0)

| Feature | Description |
|---------|-------------|
| **6 Knowledge Types** | Tasks, Notes, Explorations, Vision, Plans, References |
| **2 Backends** | Local (JSON files) and GitHub (Issues/Projects/Wiki) |
| **MCP Server** | 35 tools for Claude Code integration |
| **CLI** | Full command-line interface |

### Why Not Just AGENTS.md?

AGENTS.md defines **file conventions**: "look for vision in docs/VISION.md"

IdlerGear provides a **command-based API**:
```bash
idlergear vision show    # Returns vision, wherever it's stored
```

The difference:
- **Backend-agnostic** - Same command whether data is local, GitHub, or Jira
- **Configurable** - Project decides where data lives, command stays the same
- **Deterministic** - No AI interpretation needed, just run the command

## Installation

```bash
git clone https://github.com/marctjones/idlergear.git
cd idlergear
pip install -e .
```

## Quick Start

```bash
cd my-project
idlergear init
idlergear install  # Adds CLAUDE.md, AGENTS.md, .mcp.json

# Start using it
idlergear vision show
idlergear task create "Implement feature X"
idlergear context  # Full project context for AI
```

## Links

- [GitHub Repository](https://github.com/marctjones/idlergear)
- [Releases](https://github.com/marctjones/idlergear/releases)
- [Issues](https://github.com/marctjones/idlergear/issues)
