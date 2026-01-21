---
id: 72
title: Add full messaging CLI (idlergear agent + idlergear message)
state: open
created: '2026-01-08T23:55:48.932509Z'
labels:
- feature
- 'component: cli'
priority: medium
---
## Overview

Create a well-designed CLI for agent management and messaging that can be used from scripts.

## Commands

### Agent Management
```bash
idlergear agent list              # List agents with friendly names
idlergear agent list --json       # JSON output for scripts
idlergear agent rename <id> <name> # Assign custom name
idlergear agent show <name>       # Show agent details
```

### Messaging
```bash
# Send messages
idlergear message send <agent> "message"
idlergear message send --urgent <agent> "message"  # Injected into context
idlergear message send --all "message"             # Broadcast

# Read messages
idlergear message list                 # Your inbox
idlergear message list --agent <name>  # Specific agent's inbox  
idlergear message list --json          # JSON for scripts
idlergear message list --unread        # Only unread

# Message management
idlergear message read <id>            # Show full message
idlergear message mark-read <id>       # Mark as read
idlergear message mark-read --all      # Mark all as read
idlergear message clear                # Clear read messages
idlergear message clear --all          # Clear all messages
```

## Script-friendly features
- `--json` flag on all list commands
- Exit codes: 0=success, 1=error, 2=no messages
- Quiet mode: `--quiet` for scripts that only care about exit code

## Depends on
- Animal name dictionary (#70)
- User-assigned names (#71)
