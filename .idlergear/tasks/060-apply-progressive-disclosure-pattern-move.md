---
id: 60
title: Apply progressive disclosure pattern - move detailed docs to references/
state: closed
created: '2026-01-08T00:09:53.100891Z'
labels:
- enhancement
- 'priority: high'
- 'component: docs'
priority: high
---
## Summary

Restructure IdlerGear documentation to follow the progressive disclosure pattern from Claude Code Skills, keeping core instructions minimal while detailed docs load on-demand.

## Problem

Current state:
- CLAUDE.md: ~200 lines always loaded
- README.md: ~370 lines
- AGENTS.md: Additional instructions
- All context consumed upfront regardless of need

Skills best practice: "Keep SKILL.md under 500 lines. Split content into separate files."

## Vision Alignment

From vision: "Token Efficiency - 97% context reduction (17K → 570 tokens!)"

Progressive disclosure directly supports this goal by loading detailed content only when needed.

## Proposed Solution

### Current Structure
```
CLAUDE.md (200 lines - always loaded)
AGENTS.md (always loaded)
README.md (370 lines)
```

### New Structure
```
.claude/skills/idlergear/
├── SKILL.md (~100 lines - loaded on trigger)
└── references/
    ├── knowledge-types.md      # From README knowledge types section
    ├── mcp-tools.md            # Full 51 MCP tools reference
    ├── cli-commands.md         # CLI command reference
    ├── hooks-guide.md          # Hook installation and config
    ├── multi-agent.md          # Daemon coordination
    ├── github-integration.md   # GitHub backend setup
    └── troubleshooting.md      # Common issues
```

### Loading Behavior

1. **Startup**: Only skill name + description loaded (~100 tokens)
2. **Trigger**: SKILL.md body loads (~500 tokens)
3. **On-demand**: References load when Claude needs them

## Content Migration Plan

| Source | Destination | Action |
|--------|-------------|--------|
| CLAUDE.md forbidden files | SKILL.md core | Keep (essential) |
| CLAUDE.md command tables | references/cli-commands.md | Move |
| CLAUDE.md daemon section | references/multi-agent.md | Move |
| README MCP tools table | references/mcp-tools.md | Move |
| README knowledge types | references/knowledge-types.md | Move |

## Acceptance Criteria

- [ ] SKILL.md core under 200 lines
- [ ] All detailed docs in references/
- [ ] References linked from SKILL.md
- [ ] References one level deep (per best practice)
- [ ] Token usage measured before/after
- [ ] Claude correctly loads references when needed

## Token Savings Estimate

| Stage | Current | With Progressive Disclosure |
|-------|---------|----------------------------|
| Startup | ~2000 tokens | ~100 tokens |
| Triggered | - | ~500 tokens |
| Full docs | - | ~2000 tokens (on-demand) |

**Savings**: 75-95% reduction in typical sessions
