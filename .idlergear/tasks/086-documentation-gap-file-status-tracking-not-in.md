---
id: 86
title: 'Documentation gap: File status tracking not in CLAUDE.md or global rules'
state: closed
created: '2026-02-27T03:30:21.811001Z'
accessed: '2026-02-27T03:33:39.350471Z'
access_count: 1
relevance_score: 1.0
labels:
- documentation
- enhancement
- 'priority: medium'
priority: medium
---
## Problem

File status tracking (deprecation, archiving, versioning) is a key feature but **not documented in the files Claude Code reads automatically** at session start.

## What's Missing

**CLAUDE.md** (both project and global `~/.claude/rules/idlergear.md`):
- ❌ No mention of `idlergear_file_deprecate()`
- ❌ No mention of `idlergear_file_register()`
- ❌ No mention of `idlergear_file_status()`
- ❌ No mention of file status types (current/deprecated/archived/problematic)
- ❌ No guidance on WHEN to mark files as deprecated
- ❌ No workflow examples for refactoring with versioning

**What IS documented:**
- ✅ File annotations (`idlergear_file_annotate`) - well documented
- ✅ File search (`idlergear_file_search`) - well documented
- ✅ 93% token savings - well promoted

## What Exists

Documentation DOES exist in:
- ✅ `docs/guides/file-registry.md` - comprehensive guide
- ✅ `.claude/skills/idlergear/SKILL.md` - has file status section (lines 56-79)
- ✅ `.claude/skills/idlergear/references/mcp-tools.md` - tool reference

**But these are only loaded:**
- When `/idlergear` skill is explicitly invoked
- Not at session start

## Impact

Claude Code doesn't proactively:
- Mark old files as deprecated during refactoring
- Use `status="current"` filter when searching files
- Suggest deprecating files when creating new versions
- Warn about deprecated files in codebase

## Solution

Add file status tracking section to both:
1. `CLAUDE.md` (project-level)
2. `~/.claude/rules/idlergear.md` (global rules)

Should include:
- When to deprecate files (refactoring, creating new versions)
- How to link old → new versions with `successor` field
- Filtering searches with `status="current"`
- Pattern-based auto-deprecation (config.toml)

**Example section to add:**

```markdown
## MANDATORY: File Status Tracking

When refactoring or creating new file versions, mark old files as deprecated:

**When to use:**
- Creating new version of a file → deprecate old version
- Refactoring moves functionality → deprecate old location
- Experimental code abandoned → archive it

**Tools:**
```python
# Mark old file as deprecated
idlergear_file_deprecate(
    path="src/api_old/auth.py",
    successor="src/api/auth.py",
    reason="Migrated to OAuth2"
)

# Search only current files
idlergear_file_search(query="auth", status="current")
```

**Rules:**
- ✅ Deprecate old files when creating new versions
- ✅ Always provide `successor` path
- ✅ Use `status="current"` filter in searches
- ❌ Don't leave old versions without deprecation notice
```
