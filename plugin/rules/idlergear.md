---
description: IdlerGear knowledge management rules
alwaysApply: true
---

# IdlerGear Usage Rules

## Session Start

**ALWAYS run this command at the start of EVERY conversation:**

```bash
idlergear context
```

This provides the project vision, current plan, and open tasks. Do NOT skip this step.

## FORBIDDEN: File-Based Knowledge

**DO NOT create any of these files:**
- `TODO.md`, `TODO.txt`, `TASKS.md`
- `NOTES.md`, `SESSION_*.md`, `SCRATCH.md`
- `FEATURE_IDEAS.md`, `RESEARCH.md`, `BACKLOG.md`
- Any markdown file for tracking work or capturing thoughts

**ALWAYS use IdlerGear commands instead.**

## FORBIDDEN: Inline TODOs

**DO NOT write inline TODO comments:**
- `// TODO: ...`
- `# FIXME: ...`
- `/* HACK: ... */`

**INSTEAD:** Create a task with `idlergear task create "..." --label technical-debt`

## REQUIRED: Use IdlerGear Commands

| Instead of... | Use this command |
|---------------|------------------|
| Creating TODO.md | `idlergear task create "description"` |
| Writing notes to files | `idlergear note create "content"` |
| Adding TODO comments | `idlergear task create "..." --label technical-debt` |
| Creating VISION.md | `idlergear vision edit` |
| Documenting findings | `idlergear reference add "title" --body "..."` |

## Knowledge Flow

```
note → explore → task
```
- Quick thoughts go to notes (capture now, review later)
- Research questions go to explorations (open-ended investigation)
- Actionable work goes to tasks (clear completion criteria)
- Use `idlergear note promote <id>` to convert notes to tasks/explorations

## Data Protection

**NEVER modify `.idlergear/` files directly** - Use CLI commands only
