---
id: 31
title: 'Add session end capture: idlergear session end'
state: open
created: '2026-01-07T01:37:00.152192Z'
labels:
- enhancement
- ux
- adoption
priority: high
---
## Summary
Add session end workflow that prompts for knowledge capture before closing an AI session.

## Context
From Goose integration analysis (Note #4): AI assistants often discover things but don't capture them. Session end is a natural checkpoint.

## Implementation

```bash
idlergear session end
```

## Workflow

1. **Detect discoveries**:
   - Uncommitted git changes?
   - New files created?
   - Tests run recently?
   - Error logs?

2. **Prompt for capture**:
   ```
   Session Summary:
   - 5 files modified
   - 2 tests run
   - 1 error encountered
   
   What did we discover this session? [enter note]
   Any tasks to create? [y/n]
   Any decisions to document? [y/n]
   ```

3. **Interactive capture**:
   - Note creation
   - Task creation
   - Reference addition

4. **Save session state** (links to #114):
   - Current task
   - Uncommitted changes
   - Next steps

## Options

```bash
idlergear session end --auto           # Auto-detect, no prompts
idlergear session end --interactive    # Full prompts (default)
idlergear session end --summary-only   # Just show summary, no capture
```

## AI Integration

For AI assistants (Goose, Claude Code):
```bash
# In .goosehints or CLAUDE.md:
"Before ending our session, run: idlergear session end --interactive"
```

## Acceptance Criteria
- [ ] Detects uncommitted changes, new files, test runs
- [ ] Interactive prompts for knowledge capture
- [ ] Auto mode makes smart suggestions
- [ ] Integrates with session persistence (#114)
- [ ] Works in both human and AI workflows
- [ ] Tests for detection and capture
- [ ] Documentation with examples

## Related
- Note #4 (Goose integration analysis)
- #114 (session persistence)
- #112 (watch mode - similar detection logic)
