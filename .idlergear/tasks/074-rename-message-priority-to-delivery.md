---
id: 74
title: Rename message priority to delivery (context/notification)
state: closed
created: '2026-01-09T00:04:38.075155Z'
labels:
- feature
- 'component: messaging'
- breaking-change
priority: medium
---
## Overview

The current `priority: urgent/normal` naming is misleading. "Urgent" implies time-sensitivity, but what actually matters is where the message goes.

## Rename

| Old | New | Meaning |
|-----|-----|---------|
| `priority: urgent` | `delivery: context` | Injected into Claude's context, Claude will act on it |
| `priority: normal` | `delivery: notification` | Becomes a task with `[message]` label, informational only |

## Changes needed

1. **MCP tools** - Update `idlergear_message_send` parameter:
   - `priority` → `delivery`
   - Values: `context` (default?) or `notification`

2. **Message schema** - Update stored message format

3. **CLI** - Update flags:
   - `--urgent` → `--context` or `-c`
   - Default could be `--notification` or `-n`

4. **Documentation** - Update all references

5. **Backwards compatibility** - Accept `priority` as alias during transition?

## Example

```python
# Before
idlergear_message_send(to_agent="turtle", message="...", priority="urgent")

# After  
idlergear_message_send(to_agent="turtle", message="...", delivery="context")
```

```bash
# Before
idlergear message send --urgent turtle "..."

# After
idlergear message send --context turtle "..."
idlergear message send -c turtle "..."
```
