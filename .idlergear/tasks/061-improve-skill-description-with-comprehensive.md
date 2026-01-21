---
id: 61
title: Improve skill description with comprehensive trigger keywords
state: closed
created: '2026-01-08T00:09:53.357145Z'
labels:
- enhancement
- 'priority: high'
- 'component: integration'
priority: high
---
## Summary

Write a trigger-rich description for the IdlerGear skill that matches natural user language, ensuring automatic activation when users discuss relevant topics.

## Problem

Current CLAUDE.md approach relies on Claude remembering to check instructions. Skills use **semantic matching** against the description field to auto-trigger.

From skills docs: "Claude matches requests against descriptions using semantic similarity, so write descriptions that include keywords users would naturally say."

## Vision Alignment

From vision - The Adoption Challenge:
> "Getting AI assistants to use it consistently requires hooks, slash commands, training"

A well-crafted description solves this by **automatic triggering** - no training needed.

## Proposed Description

```yaml
description: |
  IdlerGear knowledge management for AI-assisted development. 
  
  ALWAYS use when:
  - Starting any coding session (call idlergear_session_start first!)
  - User mentions: tasks, notes, bugs, ideas, TODO, technical debt
  - User asks: "what's next", "where did we leave off", "project status"
  - Tracking work: issues, features, backlog, priorities
  - Capturing knowledge: discoveries, decisions, research, documentation
  - Project context: vision, plans, goals, direction
  - Multi-agent: coordination, daemon, other AI assistants, queue
  
  Provides: task tracking, note capture, vision management, session 
  continuity, multi-agent coordination, GitHub sync. Replaces TODO.md,
  NOTES.md, and other ad-hoc knowledge files with structured API.
```

## Trigger Keyword Categories

### Session Management
- "session", "start", "continue", "resume"
- "where did we leave off", "what were we doing"
- "context", "project status"

### Task Management  
- "task", "issue", "bug", "feature", "todo"
- "backlog", "priority", "assign"
- "what's next", "what should I work on"

### Knowledge Capture
- "note", "idea", "discovery", "learned"
- "decision", "architecture", "design"
- "reference", "documentation", "wiki"

### Project Direction
- "vision", "goal", "plan", "direction"
- "why are we", "project purpose"

### Forbidden File Prevention
- "TODO.md", "NOTES.md", "create a file for"
- "track this", "remember this"

### Multi-Agent
- "coordination", "other agents", "daemon"
- "queue", "background task"

## Acceptance Criteria

- [ ] Description under 1024 characters (API limit)
- [ ] Includes natural user language patterns
- [ ] Covers all 6 knowledge types
- [ ] Includes common questions ("what's next")
- [ ] Mentions forbidden file alternatives
- [ ] Tested with various user prompts
- [ ] Triggers on 90%+ of relevant requests

## Testing Plan

Test activation with prompts:
1. "What should I work on next?" → Should trigger
2. "I found a bug" → Should trigger  
3. "Let me note this down" → Should trigger
4. "What's the project vision?" → Should trigger
5. "Create a TODO.md file" → Should trigger (to prevent!)
6. "Help me write a function" → Should NOT trigger
