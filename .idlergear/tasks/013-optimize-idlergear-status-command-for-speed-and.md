---
id: 13
title: Optimize idlergear status command for speed and comprehensive output
state: closed
created: '2026-01-03T05:33:56.952449Z'
labels:
- enhancement
- 'priority: high'
- 'effort: medium'
- core-v1
- 'component: cli'
priority: high
---
## Summary

Based on session analysis, "status" is the most frequent keyword (59x) and "what is the status" is the #1 most common command pattern (4x). The `idlergear status` command needs to be fast and comprehensive.

## Problem

Analysis of 72 Claude Code session transcripts shows:
- **"status" keyword appears 59 times** - frequent status checking
- **"what is the status"** is the single most common command (4x)
- Users check status before taking action (status-first workflow)
- Currently no dedicated status command exists (related to #113)

## Proposed Solution

Create a fast, comprehensive status command that shows:

### Quick One-Line Summary
```bash
$ idlergear status
3 open tasks (1 in progress), 2 notes, 1 run active, 5 uncommitted files
```

### Detailed Dashboard
```bash
$ idlergear status --detailed

=== Project Status: idlergear ===

Tasks (3 open, 1 in progress)
  #42 [high] [in_progress] Implement SessionStart hook
  #43 [med]  [open]        Add status command
  #44 [low]  [open]        Update docs

Notes (2 recent)
  - "Parser quirk with compound words"
  - "Should we support Windows?" [explore]

Runs (1 active)
  ● training - running 12m (stdout: 2.4MB)

Git (5 uncommitted)
  M src/parser.py
  M tests/test_parser.py
  A src/new_feature.py
  ? notes.txt
  ? scratch.py

Last commit: 2h ago "feat: add new feature"
Last release: v0.3.0 (3 days ago)
```

### Performance Requirements

- **< 100ms** for one-line summary
- **< 500ms** for detailed view
- Cacheable results (avoid repeated git calls)
- Parallel data fetching where possible

### MCP Tool

```python
status()           # Returns structured JSON with all status info
status_summary()   # One-line summary string
```

### Implementation

```python
def get_status(detailed=False):
    """Get project status."""
    if detailed:
        return {
            'tasks': {
                'open': list_tasks(state='open'),
                'in_progress': [t for t in list_tasks() if t.get('status') == 'in_progress']
            },
            'notes': list_notes()[-5:],  # Last 5 notes
            'runs': list_runs(),
            'git': get_git_status(),
            'vision': get_vision(),
            'last_commit': get_last_commit(),
            'last_release': get_last_release()
        }
    else:
        # Fast summary
        open_tasks = len(list_tasks(state='open'))
        in_progress = len([t for t in list_tasks() if t.get('status') == 'in_progress'])
        notes = len(list_notes())
        runs = len([r for r in list_runs() if r.get('status') == 'running'])
        uncommitted = len(get_uncommitted_files())
        
        return f"{open_tasks} open tasks ({in_progress} in progress), {notes} notes, {runs} run active, {uncommitted} uncommitted files"
```

### Acceptance Criteria

- [ ] `idlergear status` shows one-line summary
- [ ] `idlergear status --detailed` shows full dashboard
- [ ] Executes in < 100ms (summary) or < 500ms (detailed)
- [ ] MCP tool available: `idlergear_status()`
- [ ] Shows: tasks, notes, runs, git status, last commit, last release
- [ ] Color-coded output (optional, via --color flag)
- [ ] JSON output available (via --json flag)

## Related

- Issue #113 (Add idlergear status command)
- Session analysis reference: "Claude Code Session Analysis - Common Command Patterns"
- "status" keyword frequency: 59x
- Most common command: "what is the status" (4x)
