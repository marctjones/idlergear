---
id: 65
title: Add model field to skills for appropriate model selection
state: open
created: '2026-01-08T00:11:29.899021Z'
labels:
- enhancement
- 'priority: low'
- 'component: integration'
priority: low
---
## Summary

Use the `model` field in skill frontmatter to specify appropriate Claude models for different IdlerGear operations, optimizing for speed vs capability.

## Problem

Currently all IdlerGear operations use whatever model the user has selected. Some operations are simple and fast (status check), others need deep reasoning (project analysis).

## Vision Alignment

From skills docs: "`model` (optional): Specifies which Claude model to use"

Optimizing model selection improves:
- Speed for simple operations
- Quality for complex analysis
- Cost efficiency

## Proposed Model Assignments

### Quick Operations → Haiku
```yaml
name: idlergear-quick
description: Quick status checks, simple queries, fast operations
model: haiku
```

Operations:
- `idlergear status`
- `idlergear task list`
- `idlergear note list`
- Simple CRUD operations

### Standard Operations → Sonnet (default)
```yaml
name: idlergear
description: Standard knowledge management operations
# model: sonnet (default, no need to specify)
```

Operations:
- Task creation with context
- Note capture
- Session management
- Most typical usage

### Deep Analysis → Opus
```yaml
name: idlergear-analysis
description: Deep project analysis, planning, architectural decisions
model: opus
```

Operations:
- Project health analysis
- Roadmap planning
- Architecture decisions
- Complex refactoring plans

## Implementation

### Option A: Separate Skills
Create distinct skills with model specified:
- `.claude/skills/idlergear-quick/SKILL.md` (haiku)
- `.claude/skills/idlergear/SKILL.md` (default/sonnet)
- `.claude/skills/idlergear-analysis/SKILL.md` (opus)

### Option B: User Selection
Document in main skill:
```markdown
## Model Selection

For quick operations, ask Claude to use haiku:
"Using haiku, show me the task list"

For deep analysis, ask Claude to use opus:
"Using opus, analyze this project's architecture"
```

## Acceptance Criteria

- [ ] Quick operations skill with haiku model
- [ ] Analysis skill with opus model
- [ ] Clear triggering distinction between skills
- [ ] Documentation explains model selection
- [ ] Tested: correct model used for each skill
- [ ] Cost/speed improvements measured

## Priority

Low - Optimization feature. Core functionality (#59) takes priority.

## Notes

- Model field may not be available in all Claude Code versions
- User can always override model selection
- Consider cost implications of opus usage
