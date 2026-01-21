---
id: 39
title: Integrate git MCP servers (DO NOT BUILD) + Add IdlerGear extensions
state: open
created: '2026-01-07T01:48:11.318169Z'
labels:
- enhancement
- mcp
- git
- goose
priority: high
---
## Research Complete: DO NOT BUILD - INTEGRATE INSTEAD

Research (Task #43, Note #9) found excellent git MCP servers already exist.

## Recommended Integration (Option A)

1. **Primary: cyanheads/git-mcp-server** (Node.js)
   - 27 tools covering all git operations
   - Dual-output: JSON for LLM, Markdown for humans
   - Configurable verbosity (minimal/standard/full)
   - Superior token efficiency
   - Production-grade features

2. **Secondary: github-mcp-server** (GitHub official)
   - GitHub platform integration (issues, PRs, Actions)
   - Complementary to local git operations

3. **Alternative: mcp-server-git** (Official Anthropic, Python)
   - Simpler, 14 core tools
   - Python-based (easier IdlerGear integration)
   - Official support

## What Exists vs What We Need

| Feature | cyanheads | Official | Verdict |
|---------|-----------|----------|---------|
| Structured status | ✅ JSON | ✅ text | **EXISTS** |
| Structured diff | ✅ JSON | ✅ text | **EXISTS** |
| Compact log | ✅ + verbosity | ✅ | **BETTER** |
| Token efficiency | ✅ configurable | ⚠️ text | **BETTER** |
| All git ops | ✅ 27 tools | ✅ 14 tools | **EXISTS** |

## IdlerGear-Specific Extensions to Build

**Phase 1: Task-Git Linking**
- `idlergear git commit-task <task_id>` - Auto-link commits to tasks
- `idlergear git status --for-task <id>` - Filter status by task files
- `idlergear git sync` - Update task status from commit messages

**Phase 2: Knowledge Extraction**
- `idlergear git capture` - Extract notes from commit history
- Auto-create notes from meaningful commits
- Link commits to reference documents

**Phase 3: Smart Filtering**
- Exclude .idlergear/ from noise
- Show only files relevant to current task/plan
- Project-context-aware status

## Implementation Plan

1. Add cyanheads/git-mcp-server as recommended dependency
2. Document configuration in .goosehints template  
3. Build thin IdlerGear wrappers for task-linking features
4. Do NOT reimplement existing git operations

See Note #9 for complete research findings.
