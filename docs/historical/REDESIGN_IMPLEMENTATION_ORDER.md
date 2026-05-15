# IdlerGear Redesign Implementation Order

**Updated:** 2026-03-08 (Based on official MCP best practices review)

## Critical Discovery: Missing MCP Primitives

After reviewing official Anthropic MCP documentation, we discovered IdlerGear is **not MCP-compliant**:

| Primitive | Required | Status | Impact |
|-----------|----------|--------|---------|
| Tools | ✅ Yes | ✅ Have (but too many) | Actions work but bloated |
| Resources | ✅ Yes | ❌ **Missing** | Context window waste |
| Prompts | ✅ Yes | ❌ **Missing** | No workflow standardization |

**Result:** Must implement Phase 0 before any other redesign work.

---

## Phase 0: MCP Compliance (Week 1) ⭐⭐⭐ CRITICAL

**Must complete before starting any other phases.**

### #436: Implement MCP Resources Primitive

**What:** Read-only data access without tool calls

**Resources to add:**
```
idlergear://project/vision              # Project mission
idlergear://project/context             # Full context
idlergear://project/context/minimal     # Minimal context
idlergear://project/tasks/open          # Open tasks
idlergear://project/runs/active         # Running processes
idlergear://project/notifications       # Notification queue
idlergear://files/{path}/annotation     # File metadata
idlergear://graph/stats                 # Graph statistics
```

**Benefits:**
- No tool call overhead for reading data
- Auto-updating resources
- Claude can subscribe to changes
- 90% token savings for data retrieval

**Implementation:**
1. Create `src/idlergear/mcp_resources.py`
2. Add resource handlers to `src/idlergear/mcp_server.py`
3. Test with Claude Code resource subscription

**Files to create/modify:**
- New: `src/idlergear/mcp_resources.py`
- Modify: `src/idlergear/mcp_server.py`

**Estimated effort:** 2-3 days

---

### #437: Implement MCP Prompts Primitive

**What:** Reusable instruction templates

**Prompts to add:**
```
/session_start              # Load context at session start
/capture_bug                # Create bug task from error
/capture_decision           # Document architectural decision
/review_changes             # Review uncommitted changes
/create_task_from_failure   # Create task from test failure
/summarize_session          # End-of-session knowledge capture
/find_related_code          # Find code related to task
/explain_architecture       # Explain project structure
```

**Benefits:**
- User-invokable via `/` commands in Claude Code
- Standardized workflows across AI assistants
- Reduces CLAUDE.md by 50%
- Reusable across Claude Code, Goose, Aider

**Implementation:**
1. Create `src/idlergear/mcp_prompts.py`
2. Add prompt handlers to `src/idlergear/mcp_server.py`
3. Test prompt templates with Claude Code

**Files to create/modify:**
- New: `src/idlergear/mcp_prompts.py`
- Modify: `src/idlergear/mcp_server.py`

**Estimated effort:** 2-3 days

---

### #438: Enable MCP Tool Search (On-Demand Loading)

**What:** Configure tool categories for efficient loading

**Tool organization:**

**Core Tools (6)** - Always loaded:
- `idlergear_capture` - Smart capture
- `idlergear_search` - Unified search
- `idlergear_execute` - Smart execution
- `idlergear_status` - State + notifications
- `idlergear_update` - Update entities
- `idlergear_annotate` - File annotation

**Advanced Tools (~15)** - Loaded on-demand:
- Task-specific: `task_create`, `task_update`, `task_close`
- Graph-specific: `graph_populate`, `graph_query`
- Run-specific: `run_start`, `run_logs`, `run_stop`
- File-specific: `file_register`, `file_deprecate`
- System: `daemon_status`, `indexing_pause`

**Benefits:**
- 90% context reduction (20K → 2K tokens)
- Only 6 tools loaded by default
- Advanced tools loaded when needed
- Scales without context bloat

**Implementation:**
1. Categorize all tools (core vs advanced)
2. Shorten all tool descriptions to <200 chars
3. Implement load logic in `mcp_server.py`
4. Test tool search threshold (>10% context)

**Files to modify:**
- `src/idlergear/mcp_server.py`
- All tool descriptions

**Estimated effort:** 3-4 days

---

## Phase 1: Consolidate Tools (Week 2)

**Depends on:** Phase 0 complete

### #432 (UPDATED): Simplify MCP Tools Interface

After Phase 0, implement the 6 smart high-level tools that replace 80% of current usage.

**Implementation:**
1. Create `src/idlergear/capture.py` - Intent detection
2. Enhance `src/idlergear/search.py` - Unified search
3. Create smart tool handlers in `mcp_server.py`
4. Add deprecation warnings to old tools

**Estimated effort:** 5-7 days

---

## Phase 2: Automatic Behaviors (Week 3-4)

**Depends on:** Phase 1 complete

### #429: Proactive Notification Queue
**Estimated effort:** 3-4 days

### #430: Auto-Annotation on File Read
**Estimated effort:** 3-4 days

### #431: Ambient Intelligence (Auto-Capture)
**Estimated effort:** 4-5 days

---

## Phase 3: Discoverability (Week 5)

**Depends on:** Phase 2 complete

### #432: TUI Dashboard Default
**Estimated effort:** 4-5 days

### #433: Better Error Messages
**Estimated effort:** 2-3 days

---

## Phase 4: Documentation (Week 6)

**Depends on:** Phase 3 complete

### #434: Simplify CLAUDE.md
Reduce from 500+ lines to <100 lines by moving content to prompts and resources.

**Estimated effort:** 2-3 days

---

## Phase 5: Migration (Week 7)

**Depends on:** Phase 4 complete

### #435: Deprecation Support
Add warnings, aliases, migration guide.

**Estimated effort:** 2-3 days

---

## Timeline Summary

| Phase | Duration | Dependencies | Priority |
|-------|----------|--------------|----------|
| Phase 0 (MCP Compliance) | 1 week | None | CRITICAL |
| Phase 1 (Tool Consolidation) | 1 week | Phase 0 | High |
| Phase 2 (Automatic Behaviors) | 2 weeks | Phase 1 | High |
| Phase 3 (Discoverability) | 1 week | Phase 2 | Medium |
| Phase 4 (Documentation) | 1 week | Phase 3 | Medium |
| Phase 5 (Migration) | 1 week | Phase 4 | Medium |

**Total:** 7 weeks

---

## Success Metrics (Post-Implementation)

| Metric | Current | Target | Improvement |
|--------|---------|--------|-------------|
| MCP primitives used | 1/3 (33%) | 3/3 (100%) | MCP compliant ✓ |
| Tools loaded | 100+ | 6 core + 15 advanced | 80% reduction |
| Context consumption | ~20K tokens | ~2K tokens | 90% reduction |
| Feature adoption by Claude | ~30% | 80%+ | 2.5x increase |
| CLAUDE.md size | 500+ lines | <100 lines | 80% reduction |
| Data retrieval overhead | Tool calls | Resources | Zero overhead |
| Workflow standardization | Via docs | Via prompts | Reusable |

---

## Official Sources

All changes based on official Anthropic guidance:

1. [MCP Specification (2025-11-25)](https://modelcontextprotocol.io/specification/2025-11-25)
2. [Claude Code MCP Integration](https://code.claude.com/docs/en/mcp)
3. [Anthropic: Code Execution with MCP](https://www.anthropic.com/engineering/code-execution-with-mcp)
4. [MCP Security Best Practices](https://modelcontextprotocol.io/specification/2025-11-25#security)
5. [Anthropic MCP Course](https://anthropic.skilljar.com/introduction-to-model-context-protocol)

---

## Next Steps

1. ✅ Issues created/updated (#436, #437, #438, #432)
2. ✅ Master task updated (#1)
3. **Start Phase 0.1:** Implement Resources (#436)
4. Review and approve implementation approach
5. Begin development

---

## Related Documents

- `UX_REDESIGN_PLAN.md` - Original redesign plan (now superseded)
- `MCP_BEST_PRACTICES_ANALYSIS.md` - Detailed analysis of MCP requirements
- `OOM_FIXES.md` - Memory optimization work (completed)
