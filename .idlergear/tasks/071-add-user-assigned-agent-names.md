---
id: 71
title: Add user-assigned agent names
state: open
created: '2026-01-08T23:55:48.753076Z'
labels:
- feature
- 'component: daemon'
priority: medium
---
## Overview

Allow users to assign custom names to agents, overriding the auto-assigned animal names.

## Requirements

1. CLI command to rename agents:
   ```bash
   idlergear agent rename turtle "api-worker"
   idlergear agent rename 4ebf3b24 "frontend-dev"
   ```

2. Persist names in `.idlergear/agents/names.json`:
   ```json
   {
     "claude-code-4ebf3b24": {"animal": "turtle", "custom": "api-worker"},
     "claude-code-39957650": {"animal": "rabbit", "custom": null}
   }
   ```

3. Display priority: custom name > animal name > agent_id

4. Allow referencing by any name:
   ```bash
   idlergear message send api-worker "..."
   idlergear message send turtle "..."
   idlergear message send 4ebf3b24 "..."
   ```

## Depends on
- Animal name dictionary (#70)
