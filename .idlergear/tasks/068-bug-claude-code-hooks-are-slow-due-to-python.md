---
id: 68
title: 'Bug: Claude Code hooks are slow due to Python startup overhead'
state: closed
created: '2026-01-08T03:30:20.172585Z'
labels:
- bug
- performance
priority: high
---
## Problem
The Claude Code hooks (ig_session-start.sh, ig_stop.sh, ig_user-prompt-submit.sh) are taking 2-4 seconds to execute because they call `idlergear` CLI commands, and each invocation has ~0.5s Python startup overhead.

## Evidence
- `idlergear context` call in ig_session-start.sh: ~4s total
- `idlergear task list` call in ig_stop.sh: ~2s total
- Multiple idlergear calls in ig_user-prompt-submit.sh: ~2.5s per pattern match

Just importing idlergear takes 0.5s:
```
time python -c "import idlergear"
real    0m0.554s
```

## Impact
- Adds noticeable latency to every Claude Code interaction
- Makes hook tests take 30+ seconds instead of <1 second
- Poor user experience

## Potential Solutions
1. **Use MCP instead of CLI** - hooks could query the already-running MCP server
2. **Lazy imports** - reduce Python startup time by deferring heavy imports
3. **Cache results** - session-start context could be cached
4. **Simplify hooks** - remove CLI calls from hot paths, use simpler file checks
