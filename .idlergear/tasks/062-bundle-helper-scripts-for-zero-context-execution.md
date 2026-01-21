---
id: 62
title: Bundle helper scripts for zero-context execution
state: open
created: '2026-01-08T00:11:28.842565Z'
labels:
- enhancement
- 'priority: medium'
- 'component: integration'
priority: medium
---
## Summary

Create bundled scripts in the IdlerGear skill that Claude can execute without loading their contents into context, following the Skills best practice for zero-context execution.

## Problem

Currently, when Claude needs to check context or status, it must:
1. Call MCP tool (loads response into context)
2. Or read documentation (loads into context)

Skills best practice: "Scripts in your Skill directory can be executed without loading their contents into context. Claude runs the script and only the output consumes tokens."

## Vision Alignment

From vision: "Token Efficiency - 97% context reduction"

Zero-context scripts maximize this by only consuming tokens for output, not the script itself.

## Proposed Scripts

```
.claude/skills/idlergear/scripts/
├── quick-context.sh      # Minimal context (~100 tokens output)
├── quick-status.sh       # One-line project status
├── session-start.sh      # Full session initialization
├── check-forbidden.sh    # Validate no forbidden files exist
├── task-summary.sh       # Brief task list
└── health-check.sh       # Verify IdlerGear is working
```

### Script Implementations

**quick-context.sh**
```bash
#!/bin/bash
# Returns minimal context - vision summary + top 3 tasks
idlergear context --mode minimal --format compact
```

**quick-status.sh**
```bash
#!/bin/bash
# One-line status
idlergear status --oneline
```

**session-start.sh**
```bash
#!/bin/bash
# Full session initialization with state restoration
idlergear session-start --format json
```

**check-forbidden.sh**
```bash
#!/bin/bash
# Check for forbidden files, exit 1 if found
idlergear check --files --quiet
```

## Benefits

| Approach | Context Cost |
|----------|--------------|
| Read CLAUDE.md | ~2000 tokens |
| Call MCP tool | ~500-1000 tokens |
| Run bundled script | Output only (~100 tokens) |

## Acceptance Criteria

- [ ] Scripts created in .claude/skills/idlergear/scripts/
- [ ] Scripts are executable (chmod +x)
- [ ] Scripts use idlergear CLI commands
- [ ] Output is minimal and structured
- [ ] Scripts handle errors gracefully
- [ ] `idlergear install` creates scripts directory
- [ ] Documentation shows how to use scripts

## Integration with SKILL.md

Add to SKILL.md:
```markdown
## Quick Commands (Zero-Context)

Run these scripts for minimal token usage:
- `./scripts/quick-status.sh` - One-line status
- `./scripts/quick-context.sh` - Minimal context
- `./scripts/session-start.sh` - Start session
```
