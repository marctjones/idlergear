---
id: 1
title: Knowledge-Types
created: '2026-01-07T00:09:35.729325Z'
updated: '2026-01-07T00:09:35.729345Z'
---
# Knowledge Types

IdlerGear manages six types of project knowledge, each with a specific purpose and workflow.

## Overview

| Type | Purpose | Lifecycle | GitHub Sync |
|------|---------|-----------|-------------|
| **Tasks** | Work to be done | open → closed | Issues |
| **Notes** | Quick capture | capture → promote/delete | Issues (labeled) |
| **Vision** | Project direction | rarely changes | VISION.md |
| **Plans** | Implementation phases | create → execute | Projects |
| **References** | Permanent docs | accumulates | Wiki |
| **Runs** | Script execution | start → complete | None |

## Knowledge Flow

```
Quick thought → Note
                  ↓
    ┌─────────────┼─────────────┐
    ↓             ↓             ↓
  Task         Reference     (delete)
    ↓
  Plan (groups tasks)
```

Notes are the inbox. They get promoted to Tasks (actionable work), References (permanent documentation), or deleted when no longer relevant.

---

## 1. Tasks

**Purpose:** Work that needs to be done.

Tasks have a clear lifecycle: open → in progress → closed. They can be prioritized, labeled, and assigned.

### When to Use

- Bug fixes
- Feature implementation
- Chores and maintenance
- Any actionable work item

### Commands

```bash
# Create
idlergear task create "Fix parser bug"
idlergear task create "Add auth" --priority high --label feature

# List
idlergear task list
idlergear task list --priority high
idlergear task list --label bug

# Show
idlergear task show 42

# Close
idlergear task close 42

# Edit
idlergear task edit 42 --priority high
```

### Fields

| Field | Description |
|-------|-------------|
| id | Unique identifier |
| title | Task summary |
| body | Detailed description |
| state | open, closed |
| priority | high, medium, low |
| labels | Categorization tags |
| created | Creation timestamp |
| updated | Last modification |

### GitHub Sync

Tasks sync bidirectionally with GitHub Issues:
- Priority becomes a label (`priority-high`)
- Labels map directly
- State maps to issue state

---

## 2. Notes

**Purpose:** Quick capture of thoughts, observations, and ideas.

Notes are the "inbox" of knowledge. They're fast to create and meant to be processed later.

### When to Use

- Quick observations you don't want to forget
- Research questions to explore
- Vague ideas to flesh out later
- Discoveries that might become tasks or references

### Commands

```bash
# Create
idlergear note create "Parser quirk with compound words"
idlergear note create "Should we support Windows?" --tag explore
idlergear note create "What if we cached the AST?" --tag idea

# List
idlergear note list
idlergear note list --tag idea

# Show
idlergear note show 1

# Delete
idlergear note delete 1

# Promote to task or reference
idlergear note promote 1 --to task
idlergear note promote 1 --to reference
```

### Tags

| Tag | Purpose |
|-----|---------|
| `explore` | Research questions, things to investigate |
| `idea` | Ideas to flesh out later |
| (none) | General observations |

### Workflow

1. **Capture** - Create notes freely during work
2. **Review** - Periodically review notes
3. **Process** - Promote useful ones, delete outdated ones

### GitHub Sync

Notes sync as GitHub Issues with the `note` label. Promotion removes the label.

---

## 3. Vision

**Purpose:** The project's purpose, mission, and long-term direction.

The vision is the "why" behind the project. It rarely changes and guides all decisions.

### When to Use

- Defining project purpose
- Setting long-term direction
- Communicating project goals to AI assistants

### Commands

```bash
# Show
idlergear vision show

# Edit
idlergear vision edit           # Opens in $EDITOR
idlergear vision edit --content "New vision..."
```

### Content Guidelines

A good vision includes:
- **Mission** - What the project does and why
- **Problem** - What problem it solves
- **Solution** - How it solves the problem
- **Non-goals** - What it explicitly doesn't do
- **Success criteria** - How to know it's working

### Example

```markdown
# MyParser

MyParser is a fast, memory-efficient parser for the XYZ language.

## Problem
Existing XYZ parsers are slow and use too much memory for large files.

## Solution
We use incremental parsing and memory-mapped files to handle
files of any size with constant memory usage.

## Non-Goals
- We don't interpret or execute XYZ code
- We don't provide language server features

## Success
- Parse 1GB files in under 10 seconds
- Memory usage stays under 100MB regardless of file size
```

### GitHub Sync

Vision can sync to a VISION.md file in the repository root.

---

## 4. Plans

**Purpose:** Define how to achieve a specific goal.

Plans group related tasks and define implementation sequence. More tactical than vision, more structured than notes.

### When to Use

- Planning a new feature
- Organizing a refactoring effort
- Tracking a release cycle
- Any multi-task initiative

### Commands

```bash
# Create
idlergear plan create auth-system --title "Authentication System"
idlergear plan create auth-system --body "Phase 1: OAuth..."

# List
idlergear plan list

# Show
idlergear plan show auth-system
idlergear plan show  # Current plan

# Switch
idlergear plan switch auth-system
```

### Structure

A plan typically includes:
- **Goal** - What we're trying to achieve
- **Phases** - Major milestones
- **Tasks** - Specific work items
- **Dependencies** - What must happen first

### Example

```markdown
# Authentication System

## Goal
Add user authentication with OAuth2 support.

## Phase 1: Core Auth
- [ ] Set up user model
- [ ] Implement session management
- [ ] Add login/logout endpoints

## Phase 2: OAuth2
- [ ] Add OAuth2 provider support
- [ ] Implement token refresh
- [ ] Add provider selection UI

## Phase 3: Security
- [ ] Add rate limiting
- [ ] Implement audit logging
- [ ] Security review
```

### GitHub Sync

Plans can sync with GitHub Projects v2 for Kanban-style tracking.

---

## 5. References

**Purpose:** Permanent documentation of how things work.

References are explanations that persist long-term. They document design decisions, technical details, and world knowledge.

### When to Use

- Documenting design decisions
- Explaining complex systems
- Recording API specifications
- Preserving institutional knowledge

### Commands

```bash
# Add
idlergear reference add "GGUF Format"
idlergear reference add "API Design" --body "REST conventions..."

# List
idlergear reference list

# Show
idlergear reference show "GGUF Format"

# Edit
idlergear reference edit "GGUF Format"

# Search
idlergear reference search "quantization"
```

### Content Guidelines

Good references:
- Have clear, descriptive titles
- Explain the "why" not just the "what"
- Include examples
- Stay up to date

### Cross-References

Use wiki-style links:

```markdown
See [[API-Design]] for REST conventions.
Related: [[Architecture]], [[Getting-Started]]
```

### GitHub Sync

References sync bidirectionally with GitHub Wiki pages.

---

## 6. Runs

**Purpose:** Track script execution and capture logs.

Runs are the history of what happened when scripts ran. They capture stdout, stderr, exit codes, and timing.

### When to Use

- Running development servers
- Executing build scripts
- Training ML models
- Any long-running process

### Commands

```bash
# Start
idlergear run start "./train.sh"
idlergear run start "python server.py" --name backend

# List
idlergear run list

# Status
idlergear run status backend

# Logs
idlergear run logs backend
idlergear run logs backend --tail 50
idlergear run logs backend --stream stderr

# Stop
idlergear run stop backend
```

### Fields

| Field | Description |
|-------|-------------|
| name | Run identifier |
| command | Command executed |
| pid | Process ID |
| status | running, stopped, failed |
| exit_code | Exit code (when finished) |
| started | Start timestamp |
| duration | Elapsed time |

### Log Files

Runs store logs in `.idlergear/runs/<name>/`:
- `command.txt` - The command executed
- `status.txt` - Current status
- `stdout.log` - Standard output
- `stderr.log` - Standard error

### No GitHub Sync

Runs are local only. They're machine-specific and often contain sensitive output.

---

## Choosing the Right Type

| Situation | Use |
|-----------|-----|
| "I need to fix this bug" | Task |
| "Interesting, the parser does X" | Note |
| "What is this project for?" | Vision |
| "How should we build feature Y?" | Plan |
| "How does the parser work?" | Reference |
| "Run the test suite" | Run |

## Best Practices

1. **Notes are temporary** - Process them regularly
2. **Tasks have clear completion** - Know when they're done
3. **Vision rarely changes** - Update only for major pivots
4. **Plans evolve** - Update as you learn
5. **References stay current** - Update when systems change
6. **Runs are queryable history** - Review when debugging

## Related

- [[Commands-Reference]] - All CLI commands
- [[Architecture]] - How knowledge is stored
- [[GitHub-Integration]] - Syncing with GitHub
