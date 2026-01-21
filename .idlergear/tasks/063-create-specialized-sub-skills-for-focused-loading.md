---
id: 63
title: Create specialized sub-skills for focused loading (tasks, notes, session, daemon)
state: open
created: '2026-01-08T00:11:29.191474Z'
labels:
- enhancement
- 'priority: medium'
- 'component: integration'
priority: medium
---
## Summary

Following Anthropic's pattern of separate skills (pdf, xlsx, pptx, docx), create specialized IdlerGear sub-skills that load only when their specific functionality is needed.

## Problem

A monolithic IdlerGear skill loads all instructions even when user only needs one feature. This wastes context on irrelevant documentation.

## Vision Alignment

From vision: "Token Efficiency" and "The Adoption Challenge"

Specialized skills:
1. Load less context (only relevant docs)
2. Trigger more precisely (specific keywords)
3. Improve adoption (right tool for right job)

## Proposed Sub-Skills

### 1. idlergear-tasks
```yaml
name: idlergear-tasks
description: |
  Task and issue management. Use when user mentions: bug, todo, task, 
  issue, feature request, backlog, priority, "what's next", work items,
  technical debt, fix needed.
```
**Triggers**: bug, todo, task, issue, backlog, priority
**Scope**: Task CRUD, labels, priorities, closing

### 2. idlergear-notes
```yaml
name: idlergear-notes  
description: |
  Quick knowledge capture. Use when user mentions: note, idea, 
  discovery, learned something, remember this, explore, research,
  observation, insight, "jot this down".
```
**Triggers**: note, idea, explore, research, discovery
**Scope**: Note CRUD, tags, promotion to task/reference

### 3. idlergear-session
```yaml
name: idlergear-session
description: |
  Session continuity and context management. Use when: starting session,
  user asks "where did we leave off", "what were we doing", context,
  project status, resume work, session state.
```
**Triggers**: session, context, "where left off", status
**Scope**: session-start, session-save, context modes

### 4. idlergear-daemon
```yaml
name: idlergear-daemon
description: |
  Multi-agent coordination. Use when: multiple AI assistants, 
  coordination, daemon, queue commands, agent registration,
  background tasks, other agents working on codebase.
```
**Triggers**: daemon, agents, coordination, queue
**Scope**: Agent registration, queue, locks, messaging

### 5. idlergear-references
```yaml
name: idlergear-references
description: |
  Documentation and knowledge base. Use when: reference, documentation,
  wiki, design decision, architecture, "how does X work", explain system.
```
**Triggers**: reference, wiki, documentation, decision
**Scope**: Reference CRUD, search, GitHub wiki sync

## Directory Structure

```
.claude/skills/
├── idlergear/           # Main skill (overview + links)
│   └── SKILL.md
├── idlergear-tasks/
│   ├── SKILL.md
│   └── references/
├── idlergear-notes/
│   ├── SKILL.md
│   └── references/
├── idlergear-session/
│   ├── SKILL.md
│   └── references/
├── idlergear-daemon/
│   ├── SKILL.md
│   └── references/
└── idlergear-references/
    ├── SKILL.md
    └── references/
```

## Benefits

| Scenario | Monolithic | Sub-Skills |
|----------|------------|------------|
| "I found a bug" | Load all IdlerGear docs | Load only tasks skill |
| "Note this idea" | Load all IdlerGear docs | Load only notes skill |
| "Start session" | Load all IdlerGear docs | Load only session skill |

**Estimated savings**: 60-80% context reduction per interaction

## Acceptance Criteria

- [ ] 5 sub-skills created with focused scopes
- [ ] Each skill has distinct trigger keywords
- [ ] No overlap in triggering (or clear priority)
- [ ] Main idlergear skill links to sub-skills
- [ ] Each sub-skill under 200 lines
- [ ] Tested: correct skill triggers for each scenario
- [ ] `idlergear install` creates all skill directories

## Priority

Medium - Depends on #59 (main skill creation) being completed first.
