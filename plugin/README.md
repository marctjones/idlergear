# IdlerGear Claude Code Plugin

Knowledge management for AI-assisted development.

## Installation

```bash
# Install IdlerGear CLI first
pip install idlergear

# Install the plugin
/plugin install https://github.com/marctjones/idlergear
```

## What's Included

### Slash Commands
- `/context` - Show project context (vision, plan, tasks)
- `/task <description>` - Create a new task
- `/note <content>` - Create a quick note

### MCP Server
Direct tool access for:
- Task management (synced to GitHub Issues)
- Note taking
- Reference documentation
- Project vision and plans

### Rules
Automatically enforced rules that:
- Remind you to check context at session start
- Block file-based TODO tracking
- Encourage using IdlerGear commands

## Quick Start

1. Initialize IdlerGear in your project:
   ```bash
   idlergear init
   ```

2. Set up GitHub backend (optional):
   ```bash
   idlergear setup-github
   ```

3. Check context at session start:
   ```bash
   idlergear context
   ```

## Learn More

- [IdlerGear Documentation](https://github.com/marctjones/idlergear/wiki)
- [GitHub Issues](https://github.com/marctjones/idlergear/issues)
