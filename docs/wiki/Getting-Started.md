# Getting Started

## Installation

```bash
git clone https://github.com/marctjones/idlergear.git
cd idlergear
pip install -e .
```

## Initialize a Project

```bash
cd my-project
idlergear init
```

This creates the `.idlergear/` directory with:
- `config.toml` - Project configuration
- `vision.md` - Project vision statement

## Install AI Integration

```bash
idlergear install
```

This adds:
- `CLAUDE.md` - Rules and context for Claude Code
- `AGENTS.md` - Universal AI agent instructions
- `.mcp.json` - MCP server configuration
- `.claude/rules/idlergear.md` - Session rules

## Basic Usage

### Check project context
```bash
idlergear context
```

### Manage tasks
```bash
idlergear task create "Implement feature X"
idlergear task list
idlergear task close 1
```

### Capture notes
```bash
idlergear note create "Found that API requires auth header"
idlergear note list
idlergear note promote 1 --to task
```

### View vision
```bash
idlergear vision show
idlergear vision edit
```

## Configuration

Configure backends in `.idlergear/config.toml`:

```toml
[backends]
task = "github"      # Use GitHub Issues for tasks
note = "local"       # Keep notes local
vision = "github"    # Sync vision to repo
```

## Next Steps

- [[Knowledge Types]] - Learn about all 6 knowledge types
- [[Commands Reference]] - Full command documentation
- [[MCP Server]] - Claude Code integration
- [[GitHub Integration]] - Sync with GitHub
