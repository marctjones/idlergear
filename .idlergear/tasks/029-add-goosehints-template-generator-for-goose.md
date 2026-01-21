---
id: 29
title: Add .goosehints template generator for Goose integration
state: open
created: '2026-01-07T01:37:00.128513Z'
labels:
- enhancement
- goose
- templates
priority: high
---
## Summary
Create Goose-specific template with optimal integration patterns and knowledge capture reminders.

## Context
From Goose integration analysis (Note #4): Goose needs specific prompts and patterns to adopt IdlerGear effectively.

## Implementation

```bash
idlergear install --assistant goose
# Creates .goosehints with Goose-optimized instructions
```

## Template Contents

1. **Session Start**:
   - Mandatory: `idlergear context --mode smart`
   - Load recent context automatically

2. **Knowledge Capture Triggers**:
   ```
   When you discover something important, ALWAYS run:
   idlergear note create "your discovery" --tag idea
   
   When you find a bug, ALWAYS run:
   idlergear task create "bug description" --label bug
   
   When you make an architectural decision, ALWAYS run:
   idlergear reference add "Decision Title" --body "rationale"
   ```

3. **Session End**:
   - Prompt for knowledge review
   - Suggest uncommitted discoveries

4. **MCP Tool Usage Patterns**:
   - When to use which tools
   - Batch operations
   - Performance tips

## Acceptance Criteria
- [ ] `idlergear install --assistant goose` creates `.goosehints`
- [ ] Template includes all sections above
- [ ] Works with both Goose CLI and GUI
- [ ] Tests for template generation
- [ ] Documentation with examples

## Related
- Note #4 (Goose integration analysis)
- #93 (multi-assistant installation)
- Existing CLAUDE.md, AGENTS.md templates
