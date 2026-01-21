---
id: 66
title: Update `idlergear install` to generate skill structure
state: closed
created: '2026-01-08T00:11:30.392035Z'
labels:
- enhancement
- 'priority: high'
- 'component: cli'
- core-v1
priority: high
---
## Summary

Extend the `idlergear install` command to create the full Claude Code Skills structure alongside existing CLAUDE.md and hooks.

## Problem

Currently `idlergear install` creates:
- CLAUDE.md
- AGENTS.md
- .mcp.json
- .claude/hooks/ (with hooks install)

It does not create the Skills structure, requiring manual setup.

## Vision Alignment

From vision: "Works across all AI assistants"

Skills are the modern Claude Code integration method. Install should create them automatically.

## Proposed Changes

### New Install Output

```
$ idlergear install

Creating IdlerGear integration files...
  ✓ CLAUDE.md (project instructions)
  ✓ AGENTS.md (AI assistant reference)
  ✓ .mcp.json (MCP server config)
  ✓ .claude/skills/idlergear/SKILL.md (Claude Code skill)
  ✓ .claude/skills/idlergear/references/ (detailed docs)
  ✓ .claude/skills/idlergear/scripts/ (helper scripts)

Run 'idlergear hooks install' to add lifecycle hooks.
```

### Directory Structure Created

```
.claude/
├── skills/
│   └── idlergear/
│       ├── SKILL.md
│       ├── references/
│       │   ├── knowledge-types.md
│       │   ├── mcp-tools.md
│       │   ├── cli-commands.md
│       │   └── multi-agent.md
│       └── scripts/
│           ├── quick-context.sh
│           ├── quick-status.sh
│           └── session-start.sh
├── hooks/
│   └── (existing hooks)
└── commands/
    └── (existing slash commands)
```

### Implementation

Update `src/idlergear/templates/`:
- Add `skill.md.template`
- Add `references/*.md` templates
- Add `scripts/*.sh` templates

Update `src/idlergear/cli.py`:
```python
def install():
    # Existing: CLAUDE.md, AGENTS.md, .mcp.json
    create_claude_md()
    create_agents_md()
    create_mcp_json()
    
    # New: Skills structure
    create_skill_structure()
    
def create_skill_structure():
    skill_dir = Path(".claude/skills/idlergear")
    skill_dir.mkdir(parents=True, exist_ok=True)
    
    # Create SKILL.md from template
    write_template(skill_dir / "SKILL.md", "skill.md.template")
    
    # Create references/
    refs_dir = skill_dir / "references"
    refs_dir.mkdir(exist_ok=True)
    for ref in ["knowledge-types", "mcp-tools", "cli-commands", "multi-agent"]:
        write_template(refs_dir / f"{ref}.md", f"references/{ref}.md.template")
    
    # Create scripts/
    scripts_dir = skill_dir / "scripts"
    scripts_dir.mkdir(exist_ok=True)
    for script in ["quick-context", "quick-status", "session-start"]:
        path = scripts_dir / f"{script}.sh"
        write_template(path, f"scripts/{script}.sh.template")
        path.chmod(0o755)  # Make executable
```

### Flags

```bash
idlergear install              # Full install (includes skill)
idlergear install --no-skill   # Skip skill creation
idlergear install --skill-only # Only create skill structure
```

## Acceptance Criteria

- [ ] `idlergear install` creates skill directory structure
- [ ] SKILL.md template with proper frontmatter
- [ ] Reference docs templates created
- [ ] Helper scripts created and executable
- [ ] Existing install behavior preserved
- [ ] --no-skill flag to skip skill creation
- [ ] --skill-only flag for skill-only install
- [ ] Uninstall removes skill structure
- [ ] Tests cover new install behavior

## Dependencies

- Depends on #59 (SKILL.md design finalized)
- Depends on #60 (reference docs structure)
- Depends on #62 (scripts structure)

## Priority

High - Required to deploy skills to users. Should be done after skill design is finalized.
