---
id: 1
title: Multi-Agent Messaging Architecture
created: '2026-01-17T21:28:14.917415Z'
updated: '2026-01-17T21:28:14.917429Z'
---
## Limitation: No Periodic Polling

Claude Code cannot periodically poll for messages because:

1. **No idle hook** - Claude Code doesn't trigger anything when waiting for user input
2. **No background threads** - MCP servers are request/response only
3. **No timers** - No way to schedule periodic calls

## Current Behavior

- Messages are checked on `user-prompt-submit` hook (start of each interaction)
- Context-priority messages are processed and injected into context
- Notification-priority messages become tasks with `[message]` label
- Deferred messages are queued for end-of-session review

## Message Delivery Types

**context** - Injected into recipient's context immediately (they will see and act on it)
**notification** (default) - Converted to a task with [message] label (informational)
**deferred** - Queued for end-of-session review

## Implications

- Real-time messaging between agents is not possible
- Agent A sends message → Agent B won't see it until their next interaction
- "context" priority means it's injected, but doesn't interrupt ongoing work
- Messages are processed at session start via `idlergear_message_process`

## Workarounds

1. **External watch command** - Run in separate terminal to monitor inbox
2. **Daemon-based OS notifications** - Desktop/terminal bell (not implemented)
3. **File-based command queue** (#255) - Future enhancement for IPC

## Design Philosophy

Claude Code is **reactive, not proactive**. It only runs when the user or Claude triggers something.

This is by design - AI assistants should not interrupt users unprompted.

## Architecture

```
Agent A → idlergear message send → Daemon → SQLite inbox
                                              ↓
Agent B (next interaction) → user-prompt-submit hook → message_process → inject context
```

## Related

- Issue #249 (limitation documentation)
- Issue #255 (external command queue for better IPC)
- `src/idlergear/messaging.py` - Implementation
