---
id: 1
title: ig-run and ig-test Issue Priority and Dependencies
created: '2026-01-11T08:41:29.634598Z'
updated: '2026-01-11T08:41:29.634616Z'
---
# Issue Priority and Dependency Analysis

## Summary

**31 open issues** across 2 implementation plans:
- **ig run**: 4 phases, 10 sub-issues
- **ig test**: 4 phases, 13 sub-issues

## Priority Distribution

| Priority | Count | Issues |
|----------|-------|--------|
| **High** | 10 | #138, #142, #146-149, #156-157 |
| **Medium** | 10 | #139-140, #143, #150-153, #158-161 |
| **Low** | 11 | #141, #144-145, #154-155, #162-168 |

---

## ig run: Dependency Graph

```
Phase 1 (High Priority) - Must complete first
├── #146 Create ig CLI entry point ──┐
├── #147 Script hash calculation ────┼──► #149 Header/footer output
├── #148 PTY runner ─────────────────┘
│
▼
Phase 2 (Medium Priority) - Depends on Phase 1
├── #150 metadata.json storage ──► #151 MCP tools update
│
▼
Phase 3 (Medium Priority) - Depends on Phase 1
├── #152 --stream flag ──┬──► Requires daemon infrastructure
├── #153 Agent registration ──┘
│
▼
Phase 4 (Low Priority) - Can start after Phase 1
├── #154 history/clean commands
├── #155 Documentation
```

### ig run Execution Order

1. **Start together (no dependencies):**
   - #146 CLI entry point
   - #147 Hash calculation  
   - #148 PTY runner

2. **After #146-148:**
   - #149 Header/footer (needs hash from #147, runner from #148)

3. **After Phase 1 complete:**
   - #150 metadata.json (can start immediately)
   - #152 --stream flag (can start immediately)
   - #153 Agent registration (can start immediately)

4. **After #150:**
   - #151 MCP tools update

5. **Anytime after Phase 1:**
   - #154 history/clean
   - #155 Documentation (should wait for feature completion)

---

## ig test: Dependency Graph

```
Phase 1 (High Priority) - Independent checks
├── #156 Staleness check ──┐
├── #157 Failure check ────┼──► All can be done in parallel
├── #158 Coverage gaps ────┤    (add to doctor.py)
├── #159 External runs ────┘
│
▼
Phase 2 (Medium Priority) - Depends on existing testing.py
├── #160 Stale detection ──┐
├── #161 Relevant tests ───┼──► Modify watch.py
├── #162 New uncovered ────┘
│
▼
Phase 3 (Low Priority) - Task integration
├── #163 --needs-tests flag ──► #164 Track commits ──► #165 Close warning
│
▼
Phase 4 (Low Priority) - Hook integration
├── #168 Config schema ──► #166 Staleness warning ──► #167 Failure blocking
```

### ig test Execution Order

1. **Phase 1 (all parallel, no dependencies):**
   - #156, #157, #158, #159

2. **Phase 2 (after Phase 1 complete):**
   - #160, #161 can run in parallel
   - #162 after #160, #161

3. **Phase 3 (sequential):**
   - #163 → #164 → #165

4. **Phase 4 (sequential):**
   - #168 (config first) → #166 → #167

---

## Recommended Implementation Order

### Week 1: Foundation
1. ig run Phase 1 (#146-149) - **High priority, blocks everything**
2. ig test Phase 1 (#156-159) - **High priority, independent**

### Week 2: Enhancement  
3. ig run Phase 2 (#150-151) - Metadata for AI visibility
4. ig test Phase 2 (#160-162) - Watch mode integration

### Week 3: Integration
5. ig run Phase 3 (#152-153) - Daemon features
6. ig test Phase 3 (#163-165) - Task integration

### Week 4: Polish
7. ig run Phase 4 (#154-155) - History, docs
8. ig test Phase 4 (#166-168) - Hook integration

---

## Parallel Work Opportunities

These issue groups have no dependencies between them:

**Group A (ig run core):** #146, #147, #148
**Group B (ig test doctor):** #156, #157, #158, #159
**Group C (ig run daemon):** #152, #153

Can work on A + B simultaneously for maximum velocity.
