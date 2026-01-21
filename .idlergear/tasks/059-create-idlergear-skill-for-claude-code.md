---
id: 59
title: Create IdlerGear Skill for Claude Code (.claude/skills/idlergear/SKILL.md)
state: closed
created: '2026-01-08T00:09:52.828392Z'
labels:
- enhancement
- 'priority: high'
- core-v1
- 'component: integration'
priority: high
---
## Summary

Create a proper Claude Code Skill to replace/supplement the current CLAUDE.md approach, following Anthropic's SKILL.md best practices for progressive disclosure and automatic triggering.

## Problem

Current approach has adoption issues:
- CLAUDE.md is always loaded (~2000 tokens) regardless of need
- Relies on Claude remembering to check instructions
- No automatic triggering based on user intent
- All context consumed upfront

## Vision Alignment

From DESIGN.md vision:
> "The Adoption Challenge: Getting AI assistants to use it consistently requires hooks, slash commands, training"

Skills provide **automatic triggering** based on description matching - directly addressing the adoption problem.

## Proposed Solution

Create `.claude/skills/idlergear/SKILL.md`:

```yaml
---
name: idlergear
description: |
  Knowledge management for AI-assisted development. Use when:
  - Starting a session (run idlergear_session_start)
  - Creating tasks, notes, or references
  - Checking project status or context
  - Tracking bugs, ideas, or technical debt
  - Coordinating with other AI agents on same codebase
  - User mentions: tasks, notes, bugs, TODO, "what's next", 
    "where did we leave off", project status, vision, plans
---

# IdlerGear Knowledge Management

## Session Start (MANDATORY)
Call `idlergear_session_start()` at the beginning of EVERY session.

## Quick Reference
[Core commands - kept under 100 lines]

## Forbidden Actions
[Brief list with alternatives]

For detailed documentation, see references/
```

## Directory Structure

```
.claude/skills/idlergear/
├── SKILL.md                    # Core instructions (<500 lines)
├── references/
│   ├── knowledge-types.md      # Detailed knowledge type docs
│   ├── mcp-tools.md            # Full MCP tool reference  
│   ├── hooks-guide.md          # Hook configuration details
│   └── multi-agent.md          # Daemon coordination docs
├── scripts/
│   ├── context.sh              # Zero-context context loading
│   ├── status.sh               # Quick status check
│   └── session-start.sh        # Session initialization
└── assets/
    └── templates/              # CLAUDE.md, AGENTS.md templates
```

## Benefits

1. **Automatic triggering** - Claude activates skill when user mentions relevant keywords
2. **Progressive disclosure** - Only loads full docs when needed
3. **Context savings** - ~500 lines vs ~2000 lines always loaded
4. **Better adoption** - Skill triggers automatically, no remembering required

## Acceptance Criteria

- [ ] SKILL.md created with proper YAML frontmatter
- [ ] Description includes comprehensive trigger keywords
- [ ] Core instructions under 500 lines
- [ ] Detailed docs moved to references/
- [ ] Helper scripts in scripts/
- [ ] Skill triggers correctly on relevant user requests
- [ ] `idlergear install` updated to create skill structure

## References

- [Claude Code Skills Documentation](https://code.claude.com/docs/en/skills)
- [Anthropic Skills Repository](https://github.com/anthropics/skills)
- [skill-creator SKILL.md](https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md)
