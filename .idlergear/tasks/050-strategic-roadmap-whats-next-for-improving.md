---
id: 50
title: 'Strategic roadmap: What''s next for improving IdlerGear'
state: open
created: '2026-01-07T04:03:30.322225Z'
labels:
- planning
- roadmap
- core-v1
priority: high
---
# Strategic Roadmap: IdlerGear Next Steps

## Executive Summary

Based on comprehensive analysis of the current state, session histories, and user pain points, here are the highest-impact next steps for improving IdlerGear.

---

## Current State (Completed This Session)

✅ **Python-Native MCP Servers** (40 tools, 0 Node.js deps)
- Filesystem (11 tools)
- Git + task integration (18 tools)
- Process management (11 tools)

✅ **Token-Efficient Context** (97% reduction: 17K → 570 tokens)
- 4 progressive modes (minimal, standard, detailed, full)

✅ **OpenTelemetry Foundation** (automatic error → task/note conversion)
- SQLite storage (FTS5, JSON1)
- OTLP collector
- 4 exporters + 3 MCP tools

✅ **Goose Integration** (CLI commands, environment detection, .goosehints)

---

## TOP 5 STRATEGIC PRIORITIES

### 🥇 1. **Session Continuity** (GitHub #114) - HIGHEST USER PAIN POINT

**Problem:** 141x "where did we left off?" requests in session analysis

**Impact:** Eliminates #1 user frustration

**Implementation:**
```bash
# Session save/restore
idlergear session save "fixing-auth"
idlergear session restore  # Most recent
idlergear context --include-session  # Auto-include session state
```

**Estimated Effort:** 2-3 days
**ROI:** ⭐⭐⭐⭐⭐ (Critical UX improvement)

---

### 🥈 2. **Hook-Based Integration** (Tasks #4-12) - ENFORCE BEST PRACTICES

**Problem:** Claude doesn't consistently use IdlerGear (60% compliance)

**Impact:** Makes IdlerGear usage automatic, not optional

**Implementation:**
- ✅ SessionStart: Auto-load context (100% compliance)
- ✅ PreToolUse: Block forbidden files (0% violations)
- ✅ Stop: Prompt for knowledge capture before ending
- ✅ PostToolUse: Suggest task creation on test failures

**Estimated Effort:** 1-2 weeks (10 hooks total)
**ROI:** ⭐⭐⭐⭐⭐ (Solves adoption problem)

---

### 🥉 3. **Watch Mode** (GitHub #112) - PROACTIVE KNOWLEDGE CAPTURE

**Problem:** Knowledge only captured when explicitly remembered

**Impact:** Continuous, automatic knowledge accumulation

**Implementation:**
```bash
idlergear watch  # Interactive mode
# Prompts:
# - "5 files changed, commit now?"
# - "TODO comment detected → create task?"
# - "Test failure → create bug?"
# - "wiki older than code → sync?"
```

**Estimated Effort:** 3-4 days
**ROI:** ⭐⭐⭐⭐ (Reduces manual tracking burden)

---

### 4. **Wiki Sync** (GitHub #116) - 197x REQUESTS

**Problem:** Documentation drifts from reality

**Impact:** Keep GitHub Wiki in sync automatically

**Implementation:**
```bash
idlergear reference sync --pull   # Get latest from GitHub
idlergear reference sync --push   # Send local changes
idlergear reference sync --status # Show what needs syncing
```

**Estimated Effort:** 2-3 days
**ROI:** ⭐⭐⭐⭐ (High demand, clear value)

---

### 5. **Daemon Queue** (Task #19) - ASYNC EXECUTION

**Problem:** All work is synchronous, blocks terminal

**Impact:** Queue tasks, continue working, check results later

**Implementation:**
```bash
idlergear queue add "analyze codebase for security"
idlergear queue list
idlergear queue result q-001  # Check later
```

**Estimated Effort:** 1-2 weeks
**ROI:** ⭐⭐⭐ (Advanced feature, enables new workflows)

---

## QUICK WINS (High Impact, Low Effort)

### Quick Win #1: Output Format Flags (Task #28)
```bash
idlergear context --format json|markdown|html|goose
```
**Effort:** 1-2 hours | **Impact:** Better tool integration

### Quick Win #2: .goosehints Template (Task #29)
```bash
idlergear goose init  # Generate .goosehints
```
**Effort:** Already done! ✅

### Quick Win #3: Session Start Hook (Task #4)
```bash
# .claude/hooks/session-start.sh
idlergear context --format compact
```
**Effort:** 1 day | **Impact:** 100% context loading

---

## MEDIUM-TERM ROADMAP (Weeks 2-4)

### Week 2-3: Implementation Tracking
- Link implementations to tasks automatically
- Git commit → task update
- "implement X" → create task #42 → track progress

### Week 3-4: Decision Capture
- Detect architectural discussions
- Prompt to document decisions
- Stop hook blocks if decisions made but not documented

---

## LONG-TERM VISION (Months 2-6)

### Autonomous Issue Management (3 tiers)
- **Tier 1:** Enhanced prompting (60% → 90% compliance)
- **Tier 2:** Automatic task creation (test failures, TODOs)
- **Tier 3:** Daemon-initiated AI sessions (background analysis)

### Cross-Assistant Unified Experience
- Same knowledge across Claude Code, Goose, Aider, Copilot
- MCP-first architecture (universal protocol)
- Project-agnostic tooling

### Visual Knowledge Browser
```bash
idlergear serve --gui  # localhost:8080
```
- Kanban board for tasks
- Knowledge graph (notes → tasks → commits)
- Timeline of sessions and runs

---

## METRICS TO TRACK

### Leading Indicators (Behavior)
- **Context loading:** 90%+ sessions start with `idlergear context`
- **Task creation:** 80%+ bugs result in task creation
- **Forbidden files:** 0% TODO.md/NOTES.md created
- **Decision docs:** 50%+ architectural choices documented

### Lagging Indicators (Outcomes)
- **Token savings:** 97% on context (already achieved!)
- **Knowledge accumulation:** Growing notes/tasks/refs over time
- **Session continuity:** Fewer "what were we doing?" questions

---

## RECOMMENDED IMMEDIATE ACTION

**Start Here:**
1. ✅ Implement Task #49 (token-efficient context) - DONE!
2. ⏭️ Implement Task #4 (SessionStart hook) - 1 day, massive impact
3. ⏭️ Implement GitHub #114 (session persistence) - 2-3 days, #1 pain point
4. ⏭️ Implement Tasks #5-6 (PreToolUse + Stop hooks) - 2 days, enforcement

**Then:** Watch mode (#112) → Wiki sync (#116) → Daemon queue (#19)

---

## SUCCESS CRITERIA

✅ **Session starts:** 100% load context automatically
✅ **Knowledge capture:** 90%+ compliance (vs 60% today)
✅ **Zero forbidden files:** Enforced by hooks
✅ **Session continuity:** "where did we leave off?" → 0 requests
✅ **Documentation sync:** Wiki = code reality

---

## KEY INSIGHT

**The next major unlock is SESSION CONTINUITY + HOOK ENFORCEMENT.**

These two features solve the top 2 user pain points:
1. **"Where did we leave off?"** (141x requests) → Session persistence
2. **Inconsistent IdlerGear usage** (60% compliance) → Hooks enforce it

Everything else builds on this foundation.
