# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.

## Project Overview

**IdlerGear is a knowledge management API that synchronizes AI context management with human project management.**

It provides a **command-based API** (not file conventions like AGENTS.md):
- `idlergear vision show` - not "look for VISION.md in docs/"
- `idlergear task list` - not "check GitHub Issues or TODO.md"
- Same commands everywhere, configurable backends

See `DESIGN.md` for the full vision, knowledge model (6 types), and architecture.

## Development

```bash
source venv/bin/activate
./run.sh  # format, lint, test
```

See DEVELOPMENT.md for practices.

## CRITICAL: IdlerGear Usage Rules

### Session Start

**ALWAYS run this command at the start of EVERY conversation:**

```bash
idlergear context
```

This provides the project vision, current plan, and open tasks. Do NOT skip this step.

### FORBIDDEN: File-Based Knowledge

**DO NOT create any of these files:**
- `TODO.md`, `TODO.txt`, `TASKS.md`
- `NOTES.md`, `SESSION_*.md`, `SCRATCH.md`
- `FEATURE_IDEAS.md`, `RESEARCH.md`, `BACKLOG.md`
- Any markdown file for tracking work or capturing thoughts

**ALWAYS use IdlerGear commands instead.**

### FORBIDDEN: Inline TODOs

**DO NOT write inline TODO comments:**
- `// TODO: ...`
- `# FIXME: ...`
- `/* HACK: ... */`

**INSTEAD:** Create a task with `idlergear task create "..." --label technical-debt`

### REQUIRED: Use IdlerGear Commands

| Instead of... | Use this command |
|---------------|------------------|
| Creating TODO.md | `idlergear task create "description"` |
| Writing notes to files | `idlergear note create "content"` |
| Adding TODO comments | `idlergear task create "..." --label technical-debt` |
| Creating VISION.md | `idlergear vision edit` |
| Documenting findings | `idlergear reference add "title" --body "..."` |

### During Development

| Action | Command |
|--------|---------|
| Found a bug | `idlergear task create "..." --label bug` |
| Had an idea | `idlergear note create "..."` |
| Research question | `idlergear note create "..." --tag explore` |
| Completed work | `idlergear task close <id>` |
| Check project goals | `idlergear vision show` |
| View open tasks | `idlergear task list` |

### Knowledge Flow

```
note → task or reference
```
- Quick thoughts go to notes (capture now, review later)
- Use `--tag explore` for research questions, `--tag idea` for ideas
- Actionable work goes to tasks (clear completion criteria)
- Use `idlergear note promote <id> --to task` to convert notes to tasks

### Data Protection

**NEVER modify `.idlergear/` files directly** - Use CLI commands only

## IdlerGear Usage

**ALWAYS run at session start:**
```bash
idlergear context
```

**FORBIDDEN files:** `TODO.md`, `NOTES.md`, `SESSION_*.md`, `SCRATCH.md`
**FORBIDDEN comments:** `// TODO:`, `# FIXME:`, `/* HACK: */`

**Use instead:**
- `idlergear task create "..."` - Create actionable tasks
- `idlergear note create "..."` - Capture quick thoughts
- `idlergear note create "..." --tag explore` - Research questions
- `idlergear vision show` - Check project goals

See AGENTS.md for full command reference.
