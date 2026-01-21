# IdlerGear Quick Start Guide

Get up and running with IdlerGear in under 5 minutes.

## What is IdlerGear?

IdlerGear is a **knowledge management API** for AI-assisted development. It prevents knowledge loss across AI sessions by providing persistent storage for tasks, notes, and project context.

**Problem**: AI assistants are stateless. Every session starts fresh.
**Solution**: IdlerGear provides commands like `idlergear task create` and `idlergear note create` that work identically across all AI assistants.

## Installation

### Option 1: pipx (Recommended)
```bash
pipx install idlergear
```

### Option 2: pip
```bash
pip install idlergear
```

### Option 3: From Source
```bash
git clone https://github.com/marctjones/idlergear.git
cd idlergear
pip install -e .
```

## Initialize Your Project

```bash
cd your-project
idlergear init
idlergear install
```

This creates:
- `.idlergear/` directory for knowledge storage
- `.mcp.json` for MCP server integration (if using Claude Code/Gemini/Copilot)
- `CLAUDE.md`, `AGENTS.md` (instruction files for AI assistants)
- `.claude/hooks/` (lifecycle hooks for Claude Code)

## First Steps

### 1. Set Your Project Vision
```bash
idlergear vision edit
```

This opens your editor. Describe what your project does and its goals. Your AI assistant will reference this for context.

### 2. Create Your First Task
```bash
idlergear task create "Set up authentication" --label feature
```

### 3. Start a Session
```bash
idlergear context
```

This shows your project vision, open tasks, and recent notes. **Always run this at session start.**

## Essential Commands

### Task Management
```bash
idlergear task create "Fix login bug" --label bug
idlergear task list
idlergear task close <id>
idlergear task show <id>
```

### Quick Notes
```bash
idlergear note create "API requires auth header"
idlergear note list
idlergear note promote <id> --to task  # Convert note to task
```

### Project Context
```bash
idlergear context                 # Minimal mode (~570 tokens)
idlergear context --mode standard # More detail (~2,500 tokens)
idlergear vision show             # View project vision
idlergear search "authentication" # Search all knowledge
```

### File Status Tracking
```bash
# Mark old file as deprecated
idlergear file deprecate old_auth.py --successor auth_v2.py

# Annotate files for token-efficient discovery (93% savings!)
idlergear file annotate auth.py --description "Authentication endpoints" --tags api auth

# Search files by annotation
idlergear file search --query "authentication"
```

### Background Processes
```bash
idlergear run start "npm run dev" --name frontend
idlergear run logs frontend
idlergear run stop frontend
```

## AI Assistant Integration

IdlerGear works with **all major AI assistants**:

| Assistant | Setup |
|-----------|-------|
| **Claude Code** | Already configured after `idlergear install` |
| **Gemini CLI** | Run `idlergear install --gemini` |
| **GitHub Copilot** | Run `idlergear install --copilot` |
| **Cursor AI** | Run `idlergear install --cursor` |
| **Aider** | Run `idlergear install --aider` |
| **Goose** | Run `idlergear install --goose` |

### MCP Integration (Claude Code, Gemini, Copilot)

If using Claude Code, Gemini CLI, or GitHub Copilot CLI, IdlerGear provides **146 MCP tools** for direct integration:

- `idlergear_session_start` - Load context at session start
- `idlergear_task_create`, `idlergear_task_list` - Task management
- `idlergear_note_create` - Capture insights
- `idlergear_file_search` - Token-efficient file discovery
- ...and 142 more

**Your AI assistant can call these tools directly instead of using CLI commands.**

## Typical Workflow

### Morning: Start New Session
```bash
# Get project context
idlergear context

# See what's next
idlergear task list
```

### During Work: Capture Knowledge
```bash
# Bug found
idlergear task create "Fix CORS issue in /api/auth" --label bug

# Quick insight
idlergear note create "JWT tokens expire after 1 hour"

# Mark old file
idlergear file deprecate auth_old.py --successor auth.py
```

### End of Day: Review
```bash
# See what was accomplished
idlergear task list --state closed

# Check project status
idlergear status
```

## Key Concepts

### Knowledge Types
- **Tasks** - Actionable work items with clear completion criteria
- **Notes** - Quick insights, learnings, ideas (use `--tag explore` for research)
- **Vision** - Project goals and direction (guides AI assistant decisions)
- **References** - Permanent documentation (API specs, architecture decisions)

### Knowledge Flow
```
note → task           # Promote idea to actionable work
note → reference      # Promote research to documentation
```

### Token Efficiency

IdlerGear dramatically reduces AI context size:

| Traditional | IdlerGear | Savings |
|-------------|-----------|---------|
| Read 15 files to find auth code (15K tokens) | `idlergear file search --query auth` (200 tokens) | **93%** |
| Read entire task list (2.5K tokens) | `idlergear task list --preview` (200 tokens) | **92%** |
| Scan full project history (10K tokens) | `idlergear context --mode minimal` (570 tokens) | **94%** |

## Next Steps

1. **Set up GitHub integration** (optional):
   ```bash
   gh auth login  # One-time setup
   idlergear config set backends.task github
   ```

2. **Enable multi-agent coordination** (optional):
   ```bash
   idlergear daemon start
   # Now multiple AI assistants can coordinate on same project
   ```

3. **Read comprehensive guides**:
   - [File Registry Guide](docs/guides/file-registry.md)
   - [Knowledge Graph Guide](docs/guides/knowledge-graph.md)
   - [GitHub Projects Integration](docs/guides/github-projects.md)

## Troubleshooting

**"Command not found: idlergear"**
- Ensure pipx/pip installation completed
- Check `pipx list` or `pip list | grep idlergear`
- Add `~/.local/bin` to PATH for pipx

**"IdlerGear not initialized"**
- Run `idlergear init` in your project directory
- Then run `idlergear install`

**"MCP server not connected" (Claude Code)**
- Check `.mcp.json` exists
- Restart Claude Code
- Run `idlergear install --upgrade` to regenerate config

**"How do I use this with [AI assistant]?"**
- See [AGENTS.md](AGENTS.md) for detailed instructions
- Check assistant-specific files: CLAUDE.md, GEMINI.md, COPILOT.md

## Learn More

- [Full Documentation](README.md)
- [Development Guide](DEVELOPMENT.md)
- [Roadmap](ROADMAP.md)
- [Installation Guide](INSTALLATION_GUIDE.md)

---

**Remember**: IdlerGear is a **command-based API**. Always use commands, not files.

- ✅ `idlergear task create "..."`
- ❌ Creating `TODO.md`
- ✅ `idlergear note create "..."`
- ❌ Writing `# TODO:` comments

This ensures knowledge persists across sessions and is accessible to all AI assistants.
