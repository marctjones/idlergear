# IdlerGear Integration Guide

Complete integration guide for all supported AI coding assistants.

## Table of Contents

- [Claude Code Integration](#claude-code-integration)
- [Goose CLI Integration](#goose-cli-integration)
- [Goose GUI Integration](#goose-gui-integration)
- [Token Efficiency Tips](#token-efficiency-tips)
- [Session Management Best Practices](#session-management-best-practices)

---

## Claude Code Integration

### Quick Setup (One Command!)

```bash
cd your-project
idlergear hooks install
```

This creates:
- `.claude/hooks/session_start` - Auto-load context every session
- `.claude/hooks/pre_tool_use` - Block forbidden files (TODO.md, NOTES.md, etc.)
- `.claude/hooks/stop` - Prompt for knowledge capture before ending
- `.claude/hooks.json` - Hook configuration

### Restart Claude Code

After installation, restart Claude Code to activate the hooks.

### What the Hooks Do

#### 1. SessionStart Hook ⚡
**Runs**: Automatically at the start of every Claude Code session

**Action**: Calls `idlergear session-start --mode minimal`

**Benefits**:
- Loads vision, plan, tasks, notes (~570 tokens)
- Restores previous session state (task ID, files, notes)
- Provides smart recommendations
- **Eliminates** "where did we leave off?" questions

#### 2. PreToolUse Hook 🚫
**Runs**: Before file creation/write operations

**Action**: Blocks forbidden files and suggests IdlerGear alternatives

**Forbidden Files**:
- `TODO.md`, `TASKS.md`, `BACKLOG.md`
- `NOTES.md`, `SESSION_*.md`, `SCRATCH.md`
- `FEATURE_IDEAS.md`, `RESEARCH.md`

**Example**:
```
❌ FORBIDDEN FILE: TODO.md

Instead, use:
  idlergear task create "Implement feature X"

Why? Knowledge in IdlerGear is queryable, linkable, and synced.
```

#### 3. Stop Hook 📝
**Runs**: Before Claude Code session ends

**Action**: Checks for uncaptured knowledge

**Checks**:
- In-progress tasks not saved
- Uncaptured bugs mentioned >3 times
- Undocumented decisions mentioned >2 times

**Example**:
```
⚠️  UNCAPTURED KNOWLEDGE DETECTED

- You mentioned "bug" 5 times but haven't created a task
- You mentioned "decision" 3 times but haven't created a note

Capture this knowledge?
  idlergear task create "Fix the bug in authentication"
  idlergear note create "Decided to use JWT instead of sessions"
```

### Testing Hooks

```bash
idlergear hooks test
```

This validates all hooks work correctly.

### Listing Hooks

```bash
idlergear hooks list
```

Shows all installed hooks and their status.

---

## Goose CLI Integration

### 1. Add IdlerGear MCP Server

Edit `~/.config/goose/config.yaml`:

```yaml
mcp_servers:
  idlergear:
    command: idlergear-mcp
    args: []
    env: {}
```

### 2. Generate .goosehints

```bash
cd your-project
idlergear goose init
```

This creates `.goosehints` with:
- IdlerGear usage instructions
- Session management best practices
- All 51 MCP tools documented
- Token efficiency tips

### 3. Start Goose

```bash
goose run
```

Goose will automatically see all 51 IdlerGear MCP tools!

### 4. Session Management (MCP Tools)

Every Goose session should start with:

```python
# ⚡ Start of EVERY session
result = idlergear_session_start(context_mode="minimal")
# Returns: vision, plan, tasks, notes + previous state + recommendations
```

During work:

```python
# Save progress
idlergear_session_save(
    current_task_id=42,
    working_files=["auth.py", "tests.py"],
    notes="Implemented JWT, testing RBAC"
)
```

End of session:

```python
# End with suggestions
idlergear_session_end(
    current_task_id=42,
    notes="Ready to implement role-based permissions"
)
```

---

## Goose GUI Integration

### Visual Setup

1. **Open Goose GUI Settings**
2. **Navigate to**: Extensions → MCP Servers
3. **Click**: "Add Custom Extension"
4. **Enter**:
   - **Name**: `idlergear`
   - **Command**: `idlergear-mcp`
   - **Args**: (leave empty)
   - **Environment**: (leave empty)
5. **Save** and restart Goose

### CLI-Based Setup

```bash
idlergear goose register
```

This displays detailed instructions for GUI setup.

### Using IdlerGear in Goose GUI

Once configured, all 51 MCP tools are available via the Goose GUI's MCP tool interface!

**Session Management** (same as CLI):
```python
idlergear_session_start(context_mode="minimal")  # Start
idlergear_session_save(current_task_id=42)       # During work
idlergear_session_end(current_task_id=42)        # End
```

---

## Token Efficiency Tips

### Context Modes

IdlerGear provides 4 context modes with progressive verbosity:

| Mode | Tokens | Use Case |
|------|--------|----------|
| **minimal** (DEFAULT) | ~570 | Session start, quick refresh |
| **standard** | ~7,040 | General development |
| **detailed** | ~11,459 | Deep planning/research |
| **full** | ~17,032 | Rare, explicit need |

**97% token savings** with minimal mode vs full!

### Recommendations

1. **Start minimal**: `idlergear_session_start(context_mode="minimal")`
2. **Upgrade when needed**: Call again with `mode="standard"` if you need more detail
3. **Avoid full mode**: Only use when absolutely necessary

### Token Savings Across All Tools

- **Filesystem**: 70% reduction (tree view vs `ls -R`)
- **Git**: 60% reduction (structured status vs `git status`)
- **Environment**: 60% reduction (consolidated vs multiple commands)
- **Session State**: 100 tokens (vs repeated "where did we leave off?" questions)

**Total**: ~6,000-10,000 tokens saved per development session!

---

## Session Management Best Practices

### 1. Always Start Sessions Properly

**Claude Code** (automatic with hooks):
```bash
# Hook runs automatically - nothing to do!
```

**Goose CLI/GUI**:
```python
idlergear_session_start(context_mode="minimal")
```

### 2. Save Progress Regularly

**Every 30-60 minutes** or when switching tasks:

```python
idlergear_session_save(
    current_task_id=42,
    working_files=["file1.py", "file2.py"],
    notes="Progress update"
)
```

### 3. End Sessions Cleanly

**Claude Code** (automatic with hooks):
```bash
# Stop hook prompts automatically
```

**Goose**:
```python
idlergear_session_end(
    current_task_id=42,
    notes="Next: Implement role-based permissions"
)
```

### 4. Use Task Linking

Link git commits to tasks automatically:

```python
# Instead of separate commit + task update
idlergear_git_commit_task(
    task_id=42,
    message="Fix authentication bug",
    files=["auth.py"]
)
```

### 5. Enable OpenTelemetry Auto-Capture

Start the OTel collector once:

```bash
idlergear otel start
```

Configure your AI assistant:

```bash
export OTEL_EXPORTER_OTLP_ENDPOINT="http://localhost:4318"
export OTEL_SERVICE_NAME="goose-session"
```

**Benefits**:
- ERROR logs → notes automatically
- FATAL logs → high-priority tasks automatically
- Zero manual error tracking!

---

## Comparison: Integration Methods

| Feature | Claude Code | Goose CLI | Goose GUI |
|---------|-------------|-----------|-----------|
| **Setup** | `idlergear hooks install` | Edit config.yaml | GUI settings |
| **Auto SessionStart** | ✅ (hook) | Manual MCP call | Manual MCP call |
| **Block Forbidden Files** | ✅ (hook) | .goosehints reminder | .goosehints reminder |
| **End-of-Session Prompts** | ✅ (hook) | Manual MCP call | Manual MCP call |
| **MCP Tools** | ✅ 51 tools | ✅ 51 tools | ✅ 51 tools |
| **Output Formats** | text, json | text, json, goose | goose (rich visuals) |
| **Token Efficiency** | ✅ 97% savings | ✅ 97% savings | ✅ 97% savings |

---

## Troubleshooting

### Claude Code Hooks Not Running

```bash
# Test hooks
idlergear hooks test

# Re-install
idlergear hooks install

# Restart Claude Code
```

### Goose MCP Server Not Found

```bash
# Verify installation
which idlergear-mcp

# Reinstall IdlerGear
cd idlergear
pip install -e .

# Check config.yaml syntax
cat ~/.config/goose/config.yaml
```

### Context Too Large

```bash
# Use minimal mode (default)
idlergear context --mode minimal  # ~570 tokens

# Or via MCP
idlergear_session_start(context_mode="minimal")
```

### Session State Not Persisting

```bash
# Check session state exists
idlergear session-status

# Manually save if needed
idlergear session-save

# Clear corrupted state
idlergear session-clear
```

---

## Next Steps

1. ✅ Install integration (hooks or MCP server)
2. ✅ Test with a small session
3. ✅ Use session management tools
4. ✅ Enable OpenTelemetry for auto-capture
5. ✅ Enjoy perfect session continuity!

For more details, see:
- [CLAUDE_CODE_HOOKS.md](./CLAUDE_CODE_HOOKS.md) - Claude Code hook details
- [README.md](../README.md) - Main documentation
- [MCP Tools Reference](../README.md#mcp-tools-reference) - All 51 tools documented
