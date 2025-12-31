# IdlerGear

**A knowledge management API that synchronizes AI context management with human project management.**

AI coding assistants are stateless. Every session starts fresh. Knowledge is constantly lost:
- Issues discovered but forgotten next session
- Learnings not recorded for future AI instances
- Script output invisible to other agents
- Project vision drifts without protection
- Multiple AI instances can't coordinate

IdlerGear provides a **command-based API** that manages this knowledge across sessions, machines, and teams.

## Features (v0.2.0)

### Knowledge Types
- **Tasks** - Track work items with status
- **Notes** - Capture quick insights and learnings
- **Explorations** - Document research and discoveries
- **Vision** - Maintain project direction and goals
- **Plans** - Organize work into phases
- **References** - Store documentation and resources

### Backends
- **Local** - JSON file storage in `.idlergear/`
- **GitHub** - Issues, Projects, Wiki integration via `gh` CLI

### AI Integration
- **MCP Server** - Model Context Protocol for Claude Code
- **CLAUDE.md** - Rules and context for Claude Code sessions
- **AGENTS.md** - Universal AI agent conventions

## Why Not Just AGENTS.md?

AGENTS.md defines **file conventions**: "look for vision in docs/VISION.md"

IdlerGear provides a **command-based API**:

```bash
idlergear vision show    # Returns authoritative vision, wherever it's stored
```

The difference:
- **Backend-agnostic** - Same command whether data is in local file, GitHub, or Jira
- **Configurable** - Project decides where data lives, command stays the same
- **Deterministic** - No AI interpretation needed, just run the command

## Quick Start

```bash
# Install
git clone https://github.com/marctjones/idlergear.git
cd idlergear
pip install -e .

# Initialize a project
cd my-project
idlergear init
idlergear install  # Adds CLAUDE.md, AGENTS.md, .mcp.json

# Use it
idlergear vision show
idlergear task create "Implement feature X"
idlergear task list
idlergear note create "Found that API requires auth header"
idlergear context  # Get full project context for AI
```

## Commands

```bash
idlergear --version          # Show version
idlergear init               # Initialize IdlerGear in project
idlergear install            # Install AI integration files
idlergear uninstall          # Remove AI integration files

idlergear task create TEXT   # Create a task
idlergear task list          # List all tasks
idlergear task complete ID   # Mark task complete

idlergear note create TEXT   # Capture a note
idlergear note list          # List all notes
idlergear note promote ID    # Promote note to task

idlergear vision show        # Show project vision
idlergear vision edit        # Edit vision (opens editor)

idlergear context            # Show full context for AI sessions

idlergear config set KEY VAL # Configure settings
idlergear config get KEY     # Get config value
```

## Configuration

Configure backends in `.idlergear/config.toml`:

```toml
[backends]
task = "github"      # Use GitHub Issues for tasks
note = "local"       # Keep notes local
vision = "github"    # Sync vision to repo
```

## Design

IdlerGear manages 11 types of knowledge (tasks, reference, explorations, vision, plans, notes, outputs, contexts, configuration, resources, codebase) across four quadrants (local/shared x volatile/persistent).

See [DESIGN.md](DESIGN.md) for the full knowledge model and architecture.

## The Key Insight

**Context management is an AI problem. Project management is a human problem. IdlerGear synchronizes them.**

## License

**All Rights Reserved.** This code is not open source. No license is granted for use, modification, or distribution without explicit written permission from the author.
