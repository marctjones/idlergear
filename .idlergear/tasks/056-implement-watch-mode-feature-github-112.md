---
id: 56
title: 'Implement Watch Mode feature (GitHub #112)'
state: closed
created: '2026-01-07T04:52:02.134995Z'
labels:
- enhancement
- automation
- watch-mode
priority: high
---
Implement proactive knowledge capture via file system watching.

## Requirements

### File System Monitoring
- Watch project files for changes
- Detect TODO comments in code
- Track uncommitted changes
- Monitor test failures

### Proactive Prompts
- "5 files changed, commit now?" (after 5+ file changes)
- "TODO detected → create task?" (when TODO comment added)
- "Test failure → create bug?" (when tests fail)
- "Documentation drift detected" (code changed but docs didn't)

### Smart Thresholds
- Configurable change thresholds
- Debouncing (don't prompt too often)
- Context-aware prompts

### Features
- `idlergear watch start` - Start watch daemon
- `idlergear watch stop` - Stop daemon
- `idlergear watch status` - Show watch status
- `idlergear watch config` - Configure thresholds

### Configuration
```toml
[watch]
enabled = false
debounce = 30  # seconds
thresholds.files_changed = 5
thresholds.uncommitted_lines = 100
thresholds.test_failures = 1
detect_todos = true
detect_fixmes = true
```

## User Demand

176x release-related, 168x issue update requests - high automation demand!

## Integrations

- Git status monitoring
- Test runner integration (pytest, jest, etc.)
- Code pattern detection (TODO, FIXME, HACK)
- Documentation sync detection

## Effort Estimate

3-4 days

## Success Criteria

- File system watching working
- Smart prompts implemented
- Daemon mode operational
- CLI commands working
- Tests written
- Documentation updated
