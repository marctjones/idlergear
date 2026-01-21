---
id: 1
title: Getting-Started
created: '2026-01-07T00:09:12.244162Z'
updated: '2026-01-07T00:09:12.244180Z'
---
# Getting Started

Install and configure IdlerGear for your project.

## Requirements

- Python 3.10+
- Git
- GitHub CLI (`gh`) - optional, for GitHub integration

## Installation

### Using pipx (Recommended)

```bash
pipx install idlergear
```

### Using pip

```bash
pip install idlergear
```

### From Source

```bash
git clone https://github.com/marctjones/idlergear.git
cd idlergear
pip install -e .
```

## Quick Start

### 1. Initialize in Your Project

```bash
cd your-project
idlergear init
```

This creates:
- `.idlergear/` - Data directory
- `.idlergear/config.toml` - Configuration
- `.idlergear/vision.md` - Project vision (empty)

### 2. Install AI Assistant Integration

For Claude Code:

```bash
idlergear install
```

This creates:
- `.mcp.json` - MCP server configuration
- `.claude/hooks/` - Shell hooks
- `.claude/commands/` - Slash commands
- `.claude/rules/` - AI instructions

### 3. Set Your Vision

```bash
idlergear vision edit
```

Write a brief description of your project's purpose. This helps AI assistants understand context.

### 4. Start Using It

```bash
# Create a task
idlergear task create "Set up authentication" --priority high

# Create a note
idlergear note create "Consider using OAuth2 for enterprise support"

# Get full context (for AI sessions)
idlergear context
```

## Creating a New Project

For a completely new project with full integration:

```bash
idlergear new my-project
cd my-project
```

This creates a project with:
- Git repository initialized
- IdlerGear configured
- Claude Code integration installed
- README.md with IdlerGear instructions

## GitHub Integration

To sync with GitHub Issues, Wiki, and Projects:

### 1. Authenticate with GitHub CLI

```bash
gh auth login
```

### 2. Configure GitHub Backends

```bash
idlergear setup-github
```

Or manually:

```bash
idlergear config set backend.task github
idlergear config set backend.reference github
```

### 3. Sync

```bash
idlergear task sync      # Sync tasks ↔ Issues
idlergear reference sync # Sync references ↔ Wiki
```

See [[GitHub-Integration]] for details.

## Using with AI Assistants

### Claude Code

After running `idlergear install`, Claude Code automatically has access to IdlerGear via MCP.

Start a session:
```
/ig_start
```

Or manually:
```bash
idlergear context
```

### Goose

```bash
idlergear goose setup
```

### Other MCP-Compatible Assistants

Add to your MCP configuration:

```json
{
  "mcpServers": {
    "idlergear": {
      "command": "idlergear",
      "args": ["serve"]
    }
  }
}
```

## Daily Workflow

### Session Start

```bash
idlergear session-start
```

This loads:
- Project context (vision, plan, tasks)
- Previous session state (last task, working files)
- Recommendations for what to work on

### During Work

```bash
# Found a bug? Create a task
idlergear task create "Fix null pointer in parser" --label bug

# Had an insight? Create a note
idlergear note create "Parser could be 10x faster with caching"

# Finished a task?
idlergear task close 42
```

### Session End

```bash
idlergear session-end --task 42 --notes "Finished auth, need tests tomorrow"
```

## Configuration

### Backend Configuration

```bash
# Use GitHub Issues for tasks
idlergear config set backend.task github

# Use local files for notes
idlergear config set backend.note local
```

### View Configuration

```bash
idlergear config backend show
```

### Configuration File

Edit `.idlergear/config.toml` directly:

```toml
[backend]
task = "github"
note = "local"
vision = "local"
plan = "local"
reference = "github"
```

## Common Workflows

### Task Management

```bash
# Create task
idlergear task create "Implement feature X" --body "Details..." --label feature

# List tasks
idlergear task list
idlergear task list --priority high

# Show task
idlergear task show 42

# Close task
idlergear task close 42
```

### Knowledge Capture

```bash
# Quick note
idlergear note create "Parser quirk with unicode"

# Research question
idlergear note create "Should we support WebSocket?" --tag explore

# Idea for later
idlergear note create "Could add plugin system" --tag idea

# Promote note to task
idlergear note promote 1 --to task
```

### Documentation

```bash
# Add reference document
idlergear reference add "API Design" --body "REST conventions..."

# Search references
idlergear reference search "authentication"

# Sync to GitHub Wiki
idlergear reference sync
```

## Troubleshooting

### "Command not found: idlergear"

Ensure the installation directory is in your PATH:

```bash
# For pipx
pipx ensurepath

# For pip
export PATH="$HOME/.local/bin:$PATH"
```

### "Not initialized"

Run in your project directory:

```bash
idlergear init
```

### "GitHub sync failed"

Check GitHub CLI authentication:

```bash
gh auth status
```

### Check Installation Health

```bash
idlergear doctor
idlergear doctor --fix  # Auto-fix issues
```

## Updating IdlerGear

```bash
# Check for updates
idlergear update --check

# Update
idlergear update
```

## Uninstalling

From a project:

```bash
idlergear uninstall
```

Completely:

```bash
pipx uninstall idlergear
```

## Next Steps

- [[Commands-Reference]] - All CLI commands
- [[Knowledge-Types]] - The six knowledge types
- [[GitHub-Integration]] - Syncing with GitHub
- [[MCP-Server]] - AI tool integration
