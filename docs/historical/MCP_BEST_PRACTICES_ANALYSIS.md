# MCP Best Practices Analysis for IdlerGear Redesign

**Date:** 2026-03-08
**Purpose:** Verify IdlerGear redesign follows official MCP and Claude Code integration patterns

## Official Sources Reviewed

1. [MCP Specification (2025-11-25)](https://modelcontextprotocol.io/specification/2025-11-25)
2. [Claude Code MCP Integration Docs](https://code.claude.com/docs/en/mcp)
3. [Anthropic: Code Execution with MCP](https://www.anthropic.com/engineering/code-execution-with-mcp)
4. [Anthropic Course: Introduction to MCP](https://anthropic.skilljar.com/introduction-to-model-context-protocol)
5. [Anthropic Course: MCP Advanced Topics](https://anthropic.skilljar.com/model-context-protocol-advanced-topics)

## Key Official Patterns

### 1. Three Core Primitives (Must Use All)

**Tools** (Model-Controlled)
- Functions the LLM can call
- Should be specific and focused
- Loaded on-demand for efficiency

**Resources** (App-Controlled)
- Data the AI can read but not change
- Static or semi-static content
- Context-controlled by application

**Prompts** (User-Controlled)
- Reusable instruction templates
- Parametrized prompts
- Shared across applications

### 2. Tool Loading Patterns

**Anti-Pattern:** Load 100+ tool definitions upfront
- Consumes massive context window
- Slows down agent
- Increases costs

**Best Practice:** On-demand tool loading
- Use MCP tool search (auto-activates at >10% context)
- Code execution to discover tools dynamically
- 98%+ token savings reported

### 3. Security Patterns

- Environment variables for sensitive data (not config files)
- TLS/HTTPS for all communication
- Least privilege principle
- Trust verification before installation

## IdlerGear Current State vs Best Practices

### ✅ What We're Doing Right

1. **Local-first architecture** - No network calls, secure by default
2. **Environment variable configuration** - GitHub tokens via env vars
3. **Python SDK** - Using official MCP Python SDK
4. **Stdio transport** - Standard Claude Code transport

### ❌ What We're Doing Wrong

| Issue | Current State | MCP Best Practice | Impact |
|-------|--------------|-------------------|---------|
| **Too many tools** | 100+ tools | 10-20 focused tools | Context window bloat |
| **All tools loaded upfront** | All 100+ in context | On-demand via tool search | Slow, expensive |
| **Missing Resources** | Everything is a tool | Use Resources for data | Wrong primitive |
| **Missing Prompts** | All in CLAUDE.md | Use MCP Prompts | Not reusable |
| **No tool categories** | Flat namespace | Group by domain | Hard to discover |

### ⚠️ What Needs Improvement

1. **Tool descriptions too long** - Many 200+ char descriptions
2. **Duplicate functionality** - Multiple ways to do same thing
3. **No progressive disclosure** - All features visible always

## Redesign Recommendations (Aligned with MCP Best Practices)

### 1. Use All Three Primitives

#### Tools (10-15 core actions)
```python
# Keep only actions that modify state
tools = [
    "idlergear_capture",       # Create task/note/reference (intent detection)
    "idlergear_execute",       # Run command (smart background)
    "idlergear_update",        # Update task/note status
    "idlergear_search",        # Unified search

    # Low-level tools (for advanced use)
    "idlergear_task_create",
    "idlergear_file_annotate",
    "idlergear_graph_populate",
]
```

#### Resources (Read-only data) - **NEW!**
```python
# Static/semi-static data exposed as resources
resources = [
    "idlergear://project/vision",              # Project vision
    "idlergear://project/context",             # Full context
    "idlergear://project/context/summary",     # Minimal context
    "idlergear://project/tasks/open",          # Open tasks list
    "idlergear://project/tasks/{id}",          # Specific task
    "idlergear://project/runs/active",         # Running processes
    "idlergear://project/notifications",       # Pending notifications
    "idlergear://files/{path}/annotation",     # File annotations
    "idlergear://graph/stats",                 # Graph statistics
]
```

**Benefits:**
- Claude can READ resources without calling tools
- Resources update automatically (app-controlled)
- Much more efficient than tool calls for data retrieval

#### Prompts (Instruction templates) - **NEW!**
```python
# Reusable prompt templates
prompts = [
    {
        "name": "session_start",
        "description": "Load project context at session start",
        "arguments": [
            {"name": "mode", "description": "Context mode (minimal/standard/full)"}
        ]
    },
    {
        "name": "capture_bug",
        "description": "Capture bug from error message",
        "arguments": [
            {"name": "error", "description": "Error message or description"},
            {"name": "file", "description": "File where error occurred", "required": false}
        ]
    },
    {
        "name": "review_changes",
        "description": "Review uncommitted changes",
        "arguments": [
            {"name": "task_id", "description": "Related task ID", "required": false}
        ]
    }
]
```

**Benefits:**
- Standardized workflows
- Reduced CLAUDE.md size
- Reusable across AI assistants
- User can trigger via `/` commands

### 2. Tool Organization Best Practices

#### Group by Domain (Not Flat)
```python
# Current (flat):
idlergear_task_create
idlergear_task_list
idlergear_task_update
# ... 100+ more

# Better (grouped):
namespace = "idlergear"
tools = {
    "capture": "Smart capture with intent detection",
    "search": "Unified search across all knowledge",
    "execute": "Smart background execution",
    "status": "Current project state + notifications",

    # Advanced (loaded on-demand)
    "tasks.create": "Create task explicitly",
    "tasks.update": "Update task",
    "files.annotate": "Annotate file",
    "graph.query": "Query knowledge graph",
}
```

#### Progressive Disclosure
```python
# Basic tools (always loaded)
basic_tools = ["capture", "search", "status", "execute"]

# Advanced tools (loaded on-demand via tool search)
advanced_tools = ["tasks.*", "files.*", "graph.*", "runs.*"]
```

### 3. Leverage Code Execution Pattern

From Anthropic's 2026 guidance on code execution:

**Instead of:**
```python
# Claude calls many tools
result1 = idlergear_task_list()
result2 = idlergear_note_list()
result3 = idlergear_reference_list()
# 3 tool calls, ~5000 tokens
```

**Do this:**
```python
# Claude writes code that uses MCP tools
import idlergear_mcp
tasks = idlergear_mcp.search(query="open tasks", scope="tasks")
notes = idlergear_mcp.search(query="", scope="notes")
refs = idlergear_mcp.search(query="", scope="references")
# 1 code execution, ~500 tokens (90% savings)
```

**How to enable:**
- Ensure our MCP server tools are code-execution compatible
- Provide clear Python API in tool descriptions
- Document code execution patterns

### 4. Resource Implementation Plan

**New Module:** `src/idlergear/mcp_resources.py`

```python
from mcp.server import Server
from mcp.types import Resource

@server.list_resources()
async def list_resources() -> list[Resource]:
    """List available resources."""
    return [
        Resource(
            uri="idlergear://project/vision",
            name="Project Vision",
            description="High-level project goals and mission",
            mimeType="text/markdown"
        ),
        Resource(
            uri="idlergear://project/context",
            name="Project Context",
            description="Full project context (tasks, notes, runs, etc.)",
            mimeType="application/json"
        ),
        Resource(
            uri="idlergear://project/tasks/open",
            name="Open Tasks",
            description="List of open tasks",
            mimeType="application/json"
        ),
        # ... more resources
    ]

@server.read_resource()
async def read_resource(uri: str) -> str:
    """Read resource content."""
    if uri == "idlergear://project/vision":
        from idlergear.vision import get_vision
        return get_vision()
    elif uri == "idlergear://project/context":
        from idlergear.context import get_context
        return json.dumps(get_context(mode="standard"))
    # ... more resource handlers
```

**Benefits:**
- Claude can subscribe to resources (auto-update)
- No tool call overhead for reading data
- More efficient context management

### 5. Prompt Implementation Plan

**New Module:** `src/idlergear/mcp_prompts.py`

```python
from mcp.server import Server
from mcp.types import Prompt, PromptArgument

@server.list_prompts()
async def list_prompts() -> list[Prompt]:
    """List available prompt templates."""
    return [
        Prompt(
            name="session_start",
            description="Load project context at session start",
            arguments=[
                PromptArgument(
                    name="mode",
                    description="Context detail level: minimal, standard, full",
                    required=False
                )
            ]
        ),
        Prompt(
            name="capture_bug",
            description="Capture bug from error or test failure",
            arguments=[
                PromptArgument(name="error", description="Error message", required=True),
                PromptArgument(name="file", description="File path", required=False),
                PromptArgument(name="line", description="Line number", required=False)
            ]
        ),
        # ... more prompts
    ]

@server.get_prompt()
async def get_prompt(name: str, arguments: dict) -> str:
    """Generate prompt from template."""
    if name == "session_start":
        mode = arguments.get("mode", "standard")
        context = get_context(mode=mode)
        return f"""# Session Start

{context}

## What should we work on?
Based on the context above, here are your options:
1. Continue task #{highest_priority_task}
2. Review test failures (3 failures)
3. Start a new task

What would you like to do?"""

    elif name == "capture_bug":
        error = arguments["error"]
        file = arguments.get("file", "")
        return f"""# Bug Detected

Error: {error}
File: {file}

Create bug task? [Y/n]"""
```

**Benefits:**
- Standardized interactions
- Reusable across assistants (Claude Code, Goose, Aider)
- User can invoke via Claude Code's `/` commands
- Reduces CLAUDE.md complexity

## Revised Tool Count (MCP-Aligned)

### Core Tools (Always Loaded) - 6 tools
```python
[
    "idlergear_capture",     # Smart capture
    "idlergear_search",      # Unified search
    "idlergear_execute",     # Smart execution
    "idlergear_status",      # State + notifications
    "idlergear_update",      # Update entities
    "idlergear_annotate",    # File annotation
]
```

### Advanced Tools (On-Demand) - ~15 tools
```python
[
    # Task-specific
    "idlergear_task_create", "idlergear_task_update", "idlergear_task_close",

    # Graph-specific
    "idlergear_graph_populate", "idlergear_graph_query",

    # Run-specific
    "idlergear_run_start", "idlergear_run_logs", "idlergear_run_stop",

    # File-specific
    "idlergear_file_register", "idlergear_file_deprecate",

    # Other
    "idlergear_daemon_status", "idlergear_indexing_pause",
]
```

### Resources (Read-Only Data) - ~12 resources
```python
[
    "idlergear://project/vision",
    "idlergear://project/context",
    "idlergear://project/tasks/open",
    "idlergear://project/runs/active",
    "idlergear://project/notifications",
    "idlergear://files/{path}/annotation",
    "idlergear://graph/stats",
    # ... etc
]
```

### Prompts (Templates) - ~8 prompts
```python
[
    "session_start",
    "capture_bug",
    "review_changes",
    "create_task_from_failure",
    "summarize_session",
    "find_related_code",
]
```

## Implementation Priority (Revised)

### Phase 0: MCP Primitives Foundation (Week 1) ⭐⭐⭐
**MUST DO FIRST** - This is MCP best practice foundation

1. **Implement Resources**
   - Add resource handlers to mcp_server.py
   - Create `idlergear://project/*` resources
   - Test with Claude Code resource subscription

2. **Implement Prompts**
   - Add prompt handlers to mcp_server.py
   - Create common prompt templates
   - Test with Claude Code `/` commands

3. **Enable Tool Search**
   - Configure tool categories (basic vs advanced)
   - Test on-demand tool loading
   - Verify >10% context threshold works

**Files to create:**
- `src/idlergear/mcp_resources.py`
- `src/idlergear/mcp_prompts.py`
- Modify `src/idlergear/mcp_server.py` to register resources and prompts

### Phase 1: Consolidate Tools (Week 2)
Continue with original Phase 2.3 plan after foundation is built

### Phase 2-6: As Originally Planned
Continue with automatic behaviors, TUI, docs, migration

## Validation Checklist

Before shipping, verify:

- [ ] All three MCP primitives used (Tools, Resources, Prompts)
- [ ] Tool count < 25 (core + advanced)
- [ ] Resources used for all read-only data
- [ ] Prompts used for common workflows
- [ ] Tool search configured (on-demand loading)
- [ ] Security: Tokens in env vars, no secrets in config
- [ ] Tool descriptions < 200 chars each
- [ ] Test with code execution pattern
- [ ] Test with Claude Code resource subscription
- [ ] Test prompts via `/` commands

## Expected Improvements

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Tools loaded | 100+ | 6 core + 15 on-demand | 80% reduction |
| Context consumed | ~20K tokens | ~2K tokens | 90% reduction |
| Data retrieval overhead | Tool call per query | Resource subscription | Zero overhead |
| Workflow standardization | Via docs | Via prompts | Reusable |
| Code execution efficiency | Not optimized | Optimized | 98% token savings |

## Sources

1. [MCP Specification](https://modelcontextprotocol.io/specification/2025-11-25)
2. [Claude Code MCP Docs](https://code.claude.com/docs/en/mcp)
3. [Anthropic: Code Execution with MCP](https://www.anthropic.com/engineering/code-execution-with-mcp)
4. [MCP Security Best Practices](https://modelcontextprotocol.io/specification/2025-11-25#security)
5. [Anthropic MCP Courses](https://anthropic.skilljar.com/introduction-to-model-context-protocol)

## Next Steps

1. ✅ Review this analysis with user
2. Implement Phase 0 (Resources + Prompts) first
3. Then proceed with original redesign phases
4. Test compliance with MCP spec at each step
