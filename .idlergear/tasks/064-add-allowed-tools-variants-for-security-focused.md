---
id: 64
title: Add allowed-tools variants for security-focused skill modes
state: open
created: '2026-01-08T00:11:29.523946Z'
labels:
- enhancement
- 'priority: low'
- 'component: integration'
priority: low
---
## Summary

Create skill variants with `allowed-tools` restrictions for security-sensitive operations, following Claude Code Skills best practice for tool access control.

## Problem

Current IdlerGear integration gives Claude full access to all 51 MCP tools. Some scenarios need restricted access:
- Read-only exploration (no modifications)
- Task-only mode (no daemon/queue access)
- Audit mode (read + log, no writes)

## Vision Alignment

From skills docs: "Specify which tools Claude can use without asking permission... Use cases include read-only file access, limited-scope operations, and security-sensitive workflows."

## Proposed Variants

### 1. idlergear-readonly
```yaml
name: idlergear-readonly
description: |
  Read-only IdlerGear access. View tasks, notes, vision, context 
  without making changes. Safe exploration mode.
allowed-tools: 
  - mcp__idlergear__idlergear_task_list
  - mcp__idlergear__idlergear_task_show
  - mcp__idlergear__idlergear_note_list
  - mcp__idlergear__idlergear_vision_show
  - mcp__idlergear__idlergear_context
  - mcp__idlergear__idlergear_status
  - mcp__idlergear__idlergear_search
  - Read
  - Grep
  - Glob
```

### 2. idlergear-tasks-only
```yaml
name: idlergear-tasks-only
description: |
  Task management only. Create, update, close tasks. No access to
  daemon, queue, or system operations.
allowed-tools:
  - mcp__idlergear__idlergear_task_create
  - mcp__idlergear__idlergear_task_list
  - mcp__idlergear__idlergear_task_show
  - mcp__idlergear__idlergear_task_close
  - mcp__idlergear__idlergear_task_update
```

### 3. idlergear-capture
```yaml
name: idlergear-capture
description: |
  Knowledge capture only. Create notes and tasks, no modifications
  to existing items or system operations.
allowed-tools:
  - mcp__idlergear__idlergear_task_create
  - mcp__idlergear__idlergear_note_create
  - mcp__idlergear__idlergear_reference_add
```

## Use Cases

| Variant | Use Case |
|---------|----------|
| readonly | New team member exploring project |
| tasks-only | Focused bug triage session |
| capture | Knowledge gathering without side effects |

## Acceptance Criteria

- [ ] 3 restricted variants created
- [ ] Each has appropriate allowed-tools list
- [ ] Variants don't trigger when full access is needed
- [ ] Clear naming distinguishes from main skill
- [ ] Documentation explains when to use each
- [ ] Tested: restricted tools actually restricted

## Priority

Low - Nice-to-have security feature. Main skill (#59) takes priority.
