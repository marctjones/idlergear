---
id: 12
title: Document hook installation and configuration in user guide
state: open
created: '2026-01-03T05:23:30.492055Z'
labels:
- documentation
- 'priority: medium'
- 'effort: small'
- 'component: docs'
priority: medium
---
## Summary

Create comprehensive documentation for IdlerGear hooks: installation, configuration, customization, and troubleshooting.

## Proposed Documentation

### README.md Update

Add section:

```markdown
## Claude Code Integration

IdlerGear includes powerful Claude Code hooks for:
- **Automatic context loading** at session start
- **Forbidden file prevention** (no TODO.md, NOTES.md)
- **Knowledge capture prompts** when stopping
- **Activity-based suggestions** (commit after N edits, bug task on test failure)

### Setup

Hooks are installed automatically with `idlergear install`. To install hooks separately:

\`\`\`bash
idlergear install --hooks-only
\`\`\`

### Configuration

Hooks are configured in \`.claude/hooks.json\`. To customize:

1. Edit hook scripts in \`.claude/hooks/\`
2. Update configuration in \`.claude/hooks.json\`
3. Test with: \`./test-hooks-manual.sh\`

See [Hook Reference](docs/hooks.md) for details.
```

### Create docs/hooks.md

Complete guide covering:

1. **Overview** - What hooks are, why they help
2. **Installation** - Setup instructions
3. **Available Hooks** - Each hook with examples
4. **Customization** - How to modify behavior
5. **Troubleshooting** - Common issues
6. **Testing** - How to validate hooks
7. **Advanced** - Writing custom hooks

### CLAUDE.md Update

Add section explaining hooks enforce the guidelines:

```markdown
## Enforcement via Hooks

IdlerGear hooks automatically enforce these guidelines:

- **SessionStart hook** - Loads project context every session
- **PreToolUse hook** - Blocks forbidden file creation
- **Stop hook** - Prompts for knowledge capture

You don't need to remember these rules - the hooks help enforce them.
```

### Acceptance Criteria

- [ ] README.md mentions hooks
- [ ] Complete docs/hooks.md reference
- [ ] CLAUDE.md explains enforcement
- [ ] Installation instructions
- [ ] Customization guide
- [ ] Troubleshooting section
- [ ] Testing instructions
- [ ] Examples for each hook
- [ ] Environment variable reference
- [ ] JSON schema documentation

## Related

- All hook implementation issues
- Integration strategy reference
- Reference: "Claude Code Hooks and IdlerGear Integration Opportunities"
