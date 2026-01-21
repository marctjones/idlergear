---
id: 69
title: MCP server doesn't track registered agent_id for message operations
state: open
created: '2026-01-08T23:20:05.402702Z'
labels:
- bug
- 'component: mcp'
priority: high
---
## Bug Description

When an agent registers with the daemon via MCP, the server doesn't store the assigned agent_id. This causes two problems:

1. **Message listing fails**: When calling `idlergear_message_list` without an agent_id, it returns "No agent_id provided or detected" instead of using the registered ID
2. **Sent messages have null sender**: The `from` field is null because the server doesn't know which agent is sending

## Expected Behavior

- MCP server should store the agent_id returned from `idlergear_daemon_register_agent`
- Subsequent calls to message tools should automatically use this stored ID
- `from` field in sent messages should be populated automatically

## Reproduction

1. Start daemon: `idlergear daemon start`
2. Open Claude Code (auto-registers via MCP)
3. Send a message: `idlergear_message_send(to_agent="other-agent", message="test")`
4. Check sent message - `from` is null
5. In receiving agent, call `idlergear_message_list()` - fails with "No agent_id provided or detected"

## Fix Location

`src/idlergear/mcp_server.py` - need to:
1. Store agent_id after successful registration in a module-level or class variable
2. Use stored agent_id as default in `idlergear_message_list`, `idlergear_message_send`, etc.
