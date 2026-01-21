---
id: 16
title: Add wiki sync prompts when wiki content is mentioned or stale
state: open
created: '2026-01-03T05:33:58.693403Z'
labels:
- enhancement
- 'priority: medium'
- 'effort: medium'
- 'component: sync'
priority: medium
---
## Summary

Based on session analysis, "wiki" is mentioned 58 times (4th most frequent keyword), indicating frequent wiki interaction but potential sync issues. Add prompts when wiki content needs syncing.

## Problem

Analysis of 72 Claude Code session transcripts shows:
- **"wiki" keyword appears 58 times** - 4th most frequent keyword
- Users frequently reference wiki content
- Wiki likely out of sync with local references
- No automatic prompts to sync

## Proposed Solution

Add wiki sync awareness and prompts in multiple places:

### 1. UserPromptSubmit Hook - Detect Wiki References

```bash
#!/bin/bash
# Detect wiki mentions and check sync status

INPUT=$(cat)
PROMPT=$(echo "$INPUT" | jq -r '.prompt')

# Pattern: Wiki reference
if echo "$PROMPT" | grep -qiE "(wiki|reference|documentation)"; then
  # Check when wiki was last synced
  WIKI_SYNC_FILE=".idlergear/.last_wiki_sync"
  
  if [ -f "$WIKI_SYNC_FILE" ]; then
    LAST_SYNC=$(cat "$WIKI_SYNC_FILE")
    NOW=$(date +%s)
    DIFF=$((NOW - LAST_SYNC))
    DAYS=$((DIFF / 86400))
    
    if [ "$DAYS" -gt 7 ]; then
      cat <<EOF
{
  "additionalContext": "Wiki mentioned. Last sync was ${DAYS} days ago.\n\nConsider syncing:\n  idlergear reference sync --pull  (get latest from GitHub)\n  idlergear reference sync --push  (send local changes to GitHub)"
}
EOF
    fi
  else
    cat <<EOF
{
  "additionalContext": "Wiki mentioned but no sync history found.\n\nTo sync with GitHub Wiki:\n  idlergear reference sync"
}
EOF
  fi
fi

exit 0
```

### 2. PostToolUse Hook - Detect Reference Changes

```bash
#!/bin/bash
# Prompt to sync after reference changes

INPUT=$(cat)
TOOL=$(echo "$INPUT" | jq -r '.tool_name')

# Check for reference-related MCP tools
if echo "$TOOL" | grep -qE "idlergear_reference_(add|edit)"; then
  cat <<EOF
{
  "additionalContext": "Reference modified locally.\n\nDon't forget to sync to GitHub Wiki:\n  idlergear reference sync --push\n\nOr check what's different:\n  idlergear reference sync --status"
}
EOF
fi

exit 0
```

### 3. Staleness Detection

Create `idlergear reference status` command:

```bash
#!/usr/bin/env python3
"""Check reference staleness vs source files."""

import os
from pathlib import Path
from datetime import datetime, timedelta

def check_reference_staleness():
    """Check if references are stale compared to source files."""
    ref_dir = Path('.idlergear/wiki')
    src_dirs = ['src/', 'lib/', 'pkg/']
    
    stale_refs = []
    
    for ref_file in ref_dir.glob('*.md'):
        ref_mtime = datetime.fromtimestamp(ref_file.stat().st_mtime)
        
        # Find related source files (heuristic: similar names)
        ref_name = ref_file.stem.lower()
        
        for src_dir in src_dirs:
            if not Path(src_dir).exists():
                continue
            
            for src_file in Path(src_dir).rglob('*'):
                if not src_file.is_file():
                    continue
                
                src_name = src_file.stem.lower()
                
                # Simple similarity check
                if src_name in ref_name or ref_name in src_name:
                    src_mtime = datetime.fromtimestamp(src_file.stat().st_mtime)
                    
                    # If source changed > 1 day after reference
                    if src_mtime > ref_mtime + timedelta(days=1):
                        stale_refs.append({
                            'reference': ref_file.name,
                            'source': str(src_file),
                            'ref_age': (datetime.now() - ref_mtime).days,
                            'src_age': (datetime.now() - src_mtime).days
                        })
    
    return stale_refs

if __name__ == '__main__':
    stale = check_reference_staleness()
    if stale:
        print("Stale references detected:")
        for item in stale:
            print(f"  {item['reference']} (ref: {item['ref_age']}d old, src: {item['src_age']}d old)")
            print(f"    Related: {item['source']}")
    else:
        print("All references up to date")
```

### 4. SessionStart Hook - Check Wiki Sync

Add to session start:

```bash
# Check wiki sync status at session start
WIKI_STATUS=$(idlergear reference sync --status 2>/dev/null)

if echo "$WIKI_STATUS" | grep -qE "(diverged|ahead|behind)"; then
  CONTEXT="${CONTEXT}\n\n=== WIKI SYNC STATUS ===\n${WIKI_STATUS}\n\nConsider running: idlergear reference sync\n"
fi
```

### 5. MCP Tools

```python
# New MCP tools
reference_sync_status()      # Check sync status
reference_sync(direction)    # Sync (pull/push/both)
reference_check_staleness()  # Check if refs are stale vs code
```

## Configuration

Add to `.idlergear/config.toml`:

```toml
[reference]
# Auto-sync settings
auto_sync = false            # Auto-sync on reference changes
sync_on_session_start = true # Check sync status at session start
staleness_days = 7           # Warn if reference older than code by N days

# GitHub Wiki settings
wiki_repo = "owner/repo.wiki.git"
wiki_branch = "master"       # GitHub wikis use master
```

## Acceptance Criteria

- [ ] Detects "wiki" mentions in prompts
- [ ] Checks last sync timestamp
- [ ] Warns if > 7 days since last sync
- [ ] Prompts to sync after reference add/edit
- [ ] Detects staleness (reference older than related source files)
- [ ] SessionStart shows sync status
- [ ] MCP tools for sync status and sync operations
- [ ] Tracks sync history (`.idlergear/.last_wiki_sync`)
- [ ] Configurable staleness threshold

## Related

- Session analysis: "wiki" mentioned 58x (4th most frequent)
- Issue #116 (Add idlergear reference sync command)
- Reference: "Claude Code Session Analysis - Common Command Patterns"
