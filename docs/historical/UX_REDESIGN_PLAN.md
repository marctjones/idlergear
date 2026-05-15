# IdlerGear UX Redesign Implementation Plan

**Milestone:** UX Redesign: Simple & Automatic (GitHub Milestone #16)
**Vision:** Transform from 100+ complex tools to simple, automatic, AI-friendly interface

## Current Problems

1. **Too Many Tools** - 100+ MCP tools overwhelm Claude (decision paralysis)
2. **Manual Everything** - File annotations, bug capture, graph updates all require explicit calls
3. **Complex Documentation** - CLAUDE.md is 500+ lines of rules and reminders
4. **Low Adoption** - Only 30% of features actually used by Claude
5. **No Feedback** - Claude doesn't know what's happening in background

## Target State

- **10 smart MCP tools** instead of 100+ specific ones
- **Automatic behaviors** - File annotation, bug capture, graph updates happen automatically
- **Proactive notifications** - IdlerGear tells Claude what's happening
- **Minimal docs** - CLAUDE.md <100 lines, tools are self-explanatory
- **80%+ adoption** - Features are intuitive and actually used

## Implementation Phases

### Phase 1: Foundation (Week 1) - CRITICAL PATH ⭐

**Goal:** Make session start foolproof and automatic

**Tasks:**
- [ ] Rename `/context` → `/start` slash command
- [ ] Update CLAUDE.md to feature `/start` as first instruction
- [ ] Add "MANDATORY" language to session start
- [ ] Test with Claude Code to ensure it always runs

**Files to modify:**
- `src/idlergear/commands/ig_context.md` → rename to `ig_start.md`
- `CLAUDE.md` - Update session start instructions
- `.claude/rules/idlergear.md` - Update mandatory rules

**Success Criteria:**
- 95%+ of Claude Code sessions run `/start` automatically
- Clear error if session starts without it

**GitHub Issue:** #1 (Phase 1: Enhance session start reliability)

---

### Phase 2: Simplify MCP Interface (Week 2-3) - HIGH IMPACT ⭐⭐⭐

#### Phase 2.1: Unified Read Interface

**Goal:** Consolidate 50+ query tools into one smart search

**Current State:**
```python
# Too many choices!
idlergear_task_list()
idlergear_note_list()
idlergear_graph_query_symbols()
idlergear_file_search()
idlergear_reference_list()
idlergear_run_list()
# ... 40+ more
```

**New Interface:**
```python
# One tool to rule them all
idlergear_search(
    query="authentication",
    scope="auto"  # or "tasks", "files", "code", "all"
)
# Returns unified results across all knowledge types
```

**Implementation:**
1. Create new `idlergear_search()` tool
2. Smart scope detection based on query patterns
3. Unified result format with type tags
4. Deprecate old query tools (but keep them working)

**Files to create/modify:**
- `src/idlergear/search.py` - Unified search logic (already exists, enhance it)
- `src/idlergear/mcp_server.py` - Add `idlergear_search` handler
- Keep existing tools for backward compatibility with deprecation warnings

#### Phase 2.2: Unified Write Interface

**Goal:** Auto-detect intent when creating knowledge

**Current State:**
```python
# Claude must choose:
idlergear_task_create()
idlergear_note_create()
idlergear_reference_add()
idlergear_vision_edit()
# Paralysis!
```

**New Interface:**
```python
# Smart capture with auto-detection
idlergear_capture(
    content="Found a bug in auth.py line 42",
    intent="auto"  # Detects "bug" → creates task
)

idlergear_capture(
    content="JWT validation uses RS256",
    intent="auto"  # Detects fact → creates reference
)
```

**Implementation:**
1. Create `idlergear_capture()` tool
2. Intent detection patterns:
   - "bug:", "issue:", "error:" → task with label=bug
   - "TODO:", "need to" → task
   - "decided to", "chose to" → reference (decision)
   - Technical facts → reference
   - Quick thought → note
3. Confirmation mode (ask before creating)

**Files to create:**
- `src/idlergear/capture.py` - Intent detection logic
- `src/idlergear/mcp_server.py` - Add `idlergear_capture` handler

#### Phase 2.3: Smart High-Level Tools

**Goal:** Context-aware tools that adapt to situation

**New Tools:**

1. **`idlergear_status()`** - Replaces `idlergear_context()`
   ```python
   idlergear_status(
       mode="auto"  # Adapts based on recent activity
   )
   # Returns:
   # - Current tasks (prioritized by recent file reads)
   # - Running processes
   # - Pending notifications
   # - Proactive suggestions
   # - Recent activity summary
   ```

2. **`idlergear_execute()`** - Smart background execution
   ```python
   idlergear_execute(
       command="pytest tests/",
       background="auto"  # Detects if command needs tmux
   )
   # Auto-detects: long-running, sudo, interactive
   # Starts in tmux if needed, regular process if not
   ```

3. **`idlergear_find()`** - Alias for search (more intuitive)
   ```python
   idlergear_find("authentication code")
   # Same as idlergear_search but shorter
   ```

**GitHub Issue:** #432 (Phase 2.3: Simplify MCP tools)

---

### Phase 3: Automatic Behaviors (Week 3-4) - GAME CHANGER ⭐⭐⭐

#### Phase 3.1: Proactive Notification Queue

**Goal:** IdlerGear tells Claude what's happening instead of Claude asking

**Implementation:**
1. Notification queue in `.idlergear/notifications.json`
2. Types of notifications:
   - Background process completed: "pytest finished: 3 failures"
   - Indexing milestone: "Knowledge graph: 1,000 symbols indexed"
   - Pattern detected: "You're searching manually - try idlergear_search"
   - Suggested action: "Create bug tasks for test failures?"

3. Delivery mechanism:
   - Queue persisted to disk
   - Returned with `idlergear_status()` calls
   - Auto-clear after delivered

**Example:**
```python
# Claude calls idlergear_status()
{
    "tasks": [...],
    "runs": [...],
    "notifications": [
        {
            "type": "process_complete",
            "message": "pytest completed: 3 tests failed",
            "action": "idlergear task create 'Fix test failures' --label bug"
        },
        {
            "type": "suggestion",
            "message": "I noticed you read 5 files without annotations",
            "action": "Run idlergear_file_search to use 93% token savings"
        }
    ]
}
```

**Files to create:**
- `src/idlergear/notifications.py` - Queue management
- `src/idlergear/patterns.py` - Pattern detection
- Modify `src/idlergear/runs.py` - Emit notifications on completion
- Modify `src/idlergear/indexing/background.py` - Emit progress notifications

**GitHub Issue:** #429 (Phase 3.1: Proactive notification queue)

#### Phase 3.2: Auto-Annotation on File Read

**Goal:** Files get annotated automatically when Claude reads them

**Implementation:**
1. Hook into Claude Code file read operations
2. Check if file already annotated
3. If not, generate annotation automatically:
   - Extract docstring for description
   - Find classes/functions for components
   - Infer tags from path (test/, api/, graph/)
4. Save annotation for 93% token savings on next search

**Approach Options:**

**Option A: MCP Hook (if supported)**
```python
@mcp.hook("after_file_read")
def auto_annotate(file_path: str):
    if not has_annotation(file_path):
        create_annotation(file_path)
```

**Option B: Claude Code Hook**
```bash
# .claude/hooks/ig_post-tool-use.sh
# Detects when Read tool used, annotates file
```

**Option C: Explicit Tool (fallback)**
```python
# Claude must call after reading
idlergear_annotate(path="src/auth.py", auto=True)
```

**Files to modify:**
- `.claude/hooks/ig_post-tool-use.sh` - Add auto-annotation logic
- `src/idlergear/file_annotation_storage.py` - Add auto-generation
- `src/idlergear/indexing/background.py` - Already has auto-annotation logic, reuse it

**GitHub Issue:** #430 (Phase 3.2: Auto-annotation on file reads)

#### Phase 3.3: Ambient Intelligence - Auto-Capture from Mentions

**Goal:** Detect when Claude mentions bugs/decisions/TODOs and auto-capture

**Detection Patterns:**
```python
PATTERNS = {
    "bug": r"(bug|issue|error|broken|failing):?\s+(.+)",
    "todo": r"(TODO|FIXME|remember to|need to):?\s+(.+)",
    "decision": r"(decided to|chose to|decided on|going with):?\s+(.+)",
}
```

**Implementation:**
1. Hook into user prompt submit or tool responses
2. Scan for patterns
3. Extract content
4. Create appropriate knowledge item (with confirmation)

**Modes:**
- **Auto-capture**: Create immediately, notify Claude
- **Suggest**: Ask "Want to capture this as a bug task?"
- **Silent**: Just log, don't create

**Files to create:**
- `src/idlergear/ambient.py` - Pattern detection and capture
- `.claude/hooks/ig_user-prompt-submit.sh` - Scan prompts for patterns
- Modify `src/idlergear/notifications.py` - Add capture suggestions

**GitHub Issue:** #431 (Phase 3.3: Ambient intelligence - auto-capture)

---

### Phase 4: Discoverability & Polish (Week 5)

#### Phase 4.1: TUI Dashboard as Default

**Goal:** `idlergear` with no args launches interactive dashboard

**Features:**
- Real-time task overview (counts by state/label)
- Running processes with live status
- Recent activity timeline
- System health (indexed files, graph size, daemon status)
- Proactive suggestions from notification queue
- Keyboard shortcuts: [t]asks, [r]uns, [f]ind, [a]dd, [s]tatus, [q]uit

**Implementation:**
- Extend existing TUI (already partially built)
- Make it default command (currently requires `idlergear tui`)
- Add real-time updates (watch mode)

**Files to modify:**
- `src/idlergear/cli.py` - Make TUI default when no command given
- `src/idlergear/tui/` - Enhance dashboard views
- Add home dashboard view

**GitHub Issue:** #432 (Phase 4.1: TUI dashboard default)

#### Phase 4.2: Better Error Messages

**Goal:** Every error tells user how to fix it

**Bad:**
```
AbortError: database locked
```

**Good:**
```
Database locked by background indexer.
Wait 10s or run: idlergear doctor --fix-locks

Tip: Background indexing runs after tool calls.
Pause it with: idlergear pause-indexing
```

**Implementation:**
1. Wrap common errors with helpful context
2. Add suggestions for fixes
3. Include related commands
4. Add tips for preventing issue

**Files to modify:**
- All error handling in `src/idlergear/*.py`
- Create `src/idlergear/errors.py` - Helpful error messages
- Add `idlergear help <topic>` for detailed guidance

**GitHub Issue:** #433 (Phase 4.2: Error messages and inline help)

---

### Phase 5: Simplify Documentation (Week 6)

**Goal:** Reduce CLAUDE.md from 500+ lines to <100 lines

**New Structure:**
```markdown
# IdlerGear Usage

IdlerGear automatically tracks your work. Use tools naturally:
- `idlergear_start()` - Load project context (run first!)
- `idlergear_capture()` - Auto-detects type (bug/note/decision)
- `idlergear_search()` - Searches everything
- `idlergear_execute()` - Smart background execution
- `idlergear_status()` - Current state + suggestions

Features work automatically:
✓ Files annotated when read (93% token savings)
✓ Graph updates when code written (95% token savings)
✓ Bugs auto-captured from mentions
✓ Background processes auto-notify

Trust the tools. They're context-aware.
```

**Move to web docs:**
- Detailed API reference
- Advanced configuration
- Architecture diagrams
- Troubleshooting guide

**Files to modify:**
- `CLAUDE.md` - Drastically simplify
- `.claude/rules/idlergear.md` - Simplify
- Move details to new `docs/guide/` directory

**GitHub Issue:** #434 (Phase 5: Simplify CLAUDE.md)

---

### Phase 6: Migration & Deprecation (Week 7)

**Goal:** Smooth transition for existing users

**Implementation:**
1. **Deprecation warnings:**
   ```python
   # Old tool still works but warns
   idlergear_task_create(...)
   # Warning: Use idlergear_capture() instead.
   # This tool will be removed in v1.0
   ```

2. **Command aliases:**
   ```bash
   idlergear task create → idlergear capture
   idlergear context → idlergear start
   ```

3. **Migration guide:**
   - Before/after examples
   - Command mapping table
   - Deprecation timeline

**Timeline:**
- v0.9: New interface + warnings
- v0.10: Old commands work with loud warnings
- v1.0: Remove deprecated commands

**Files to create:**
- `MIGRATION.md` - Detailed upgrade guide
- Modify all deprecated tools to emit warnings
- Add aliases in `src/idlergear/cli.py`

**GitHub Issue:** #435 (Phase 6: Migration support)

---

## Implementation Priority (Which to Start First?)

### Option A: Start with Phase 2.3 (Smart High-Level Tools) ⭐ RECOMMENDED

**Why:**
- Highest immediate value
- Foundation for all other phases
- Can test with Claude immediately
- Doesn't break existing workflows

**Week 1 Tasks:**
1. Implement `idlergear_status()` to replace `idlergear_context()`
2. Implement `idlergear_search()` for unified searching
3. Implement `idlergear_capture()` with intent detection
4. Test with Claude Code to validate UX improvements

### Option B: Start with Phase 3.1 (Proactive Notifications)

**Why:**
- Solves biggest pain point (Claude doesn't know what's happening)
- Quick win (can implement in 2-3 days)
- Enables all other automatic behaviors

### Option C: Start with Phase 4.1 (TUI Dashboard)

**Why:**
- Most visible improvement
- Good for demos/videos
- Improves human usability immediately

## Recommendation: Start with Phase 2.3 + 3.1 in Parallel

**Week 1-2:**
- Implement `idlergear_status()`, `idlergear_search()`, `idlergear_capture()` (Phase 2.3)
- Implement notification queue (Phase 3.1)
- These work together: status returns notifications

**Week 3:**
- Auto-annotation on file read (Phase 3.2)
- Ambient intelligence - auto-capture (Phase 3.3)

**Week 4:**
- TUI dashboard (Phase 4.1)
- Better error messages (Phase 4.2)

**Week 5-6:**
- Simplify docs (Phase 5)
- Migration support (Phase 6)

## Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Number of MCP tools Claude uses | 30 tools (~30% of available) | 10 tools (~80% adoption) |
| CLAUDE.md size | 500+ lines | <100 lines |
| Files manually annotated | 100% manual | 80%+ automatic |
| Bugs manually captured | 100% manual | 80%+ automatic |
| Time to onboard new user | 30+ minutes | <5 minutes |
| Claude asks "what's happening?" | Often | Rarely (proactive notifications) |

## Questions to Resolve

1. **MCP Capabilities:** Does MCP support `after_file_read` hooks?
2. **Claude Code Hooks:** Can we reliably hook into file read operations?
3. **Notification Delivery:** Can we push notifications to Claude or only pull?
4. **Intent Detection:** What's acceptable false positive rate for auto-capture?
5. **Migration Timeline:** How long to support deprecated tools?

## Next Steps

1. ✅ Create master task (Task #1)
2. Review this plan with user
3. Start implementation of Phase 2.3 (smart high-level tools)
4. Create prototype of `idlergear_status()` and test with Claude
5. Iterate based on real-world usage

---

**Related GitHub Issues:**
- #1 - Phase 1: Session start
- #429 - Phase 3.1: Proactive notifications
- #430 - Phase 3.2: Auto-annotation
- #431 - Phase 3.3: Ambient intelligence
- #432 - Phase 4.1: TUI dashboard
- #433 - Phase 4.2: Better errors
- #434 - Phase 5: Simplify docs
- #435 - Phase 6: Migration
