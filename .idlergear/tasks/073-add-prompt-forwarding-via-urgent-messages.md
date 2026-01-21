---
id: 73
title: Add prompt forwarding via urgent messages
state: open
created: '2026-01-08T23:55:49.121914Z'
labels:
- feature
- 'component: messaging'
priority: medium
---
## Overview

Enable one agent to send a prompt/request that another agent will act on by leveraging the urgent message injection mechanism.

## How it works

1. Agent A sends an urgent message with `action_requested=true`:
   ```python
   idlergear_message_send(
       to_agent="turtle",
       message="Please run the test suite and report any failures",
       priority="urgent",
       action_requested=True
   )
   ```

2. When Agent B (turtle) processes their inbox on next interaction:
   - Urgent message is injected into context
   - Formatted as a request: "Agent rabbit requests: Please run the test suite..."
   - Claude naturally responds to this request

3. Agent B can reply back:
   ```python
   idlergear_message_send(
       to_agent="rabbit", 
       message="Test results: 45 passed, 2 failed. Failures in test_auth.py",
       context={"in_reply_to": "<original_message_id>"}
   )
   ```

## CLI support
```bash
# Send a prompt/request to another agent
idlergear message send --urgent --request turtle "Run tests and report back"

# The --request flag formats it as an actionable prompt
```

## Limitations to document
- Receiving agent still needs human to trigger next interaction
- No guarantee of response time
- No synchronous request/response

## Depends on
- Full messaging CLI (#72)
