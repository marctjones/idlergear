# IdlerGear Roadmap & Release Plan

## Executive Summary

**Total Open Issues:** 23
- **v0.4.0:** 9 issues (test & run management)
- **v0.5.0:** 5 issues (planning & foundation) ⭐ QUICK WINS
- **v0.6.0:** 2 issues (structured information + POC)
- **v0.7.0:** 7 issues (multi-assistant & collaboration)
- **v0.8.0:** 2 issues + polish (developer experience)

**Current Version:** v0.3.72

**Philosophy:** Ship incrementally stable releases with useful features. Each milestone is independently valuable and can be adopted immediately.

---

## Milestone Releases

### v0.4.0 - Test & Run Awareness ✅ READY TO SHIP
**Theme:** Complete test framework integration and run management polish
**Priority:** High (foundational for developer workflows)
**Target:** Q1 2026 (2-3 weeks)
**Status:** Well-structured, clear dependencies, ready to implement

**Issues (9):**
1. **#163** - Add --needs-tests flag to task create [medium]
2. **#164** - Track test file changes in task commits [medium]
3. **#165** - Warn on task close if needs-tests but no tests added [medium]
4. **#166** - Add test staleness warning to pre-commit hook [medium]
5. **#162** - Detect new files without test coverage in watch mode [medium]
6. **#144** - ig test Phase 3: Task integration [medium]
7. **#145** - ig test Phase 4: Hook integration [medium]
8. **#154** - Add ig run history and clean commands [medium]
9. **#141** - ig run Phase 4: Polish and documentation [low]

**Dependencies:**
- ✅ #168 - Test config schema (COMPLETE)
- ✅ #167 - Test failure blocking (COMPLETE)

**Implementation Order:**
1. #163 - --needs-tests flag (foundation)
2. #164 - Track test file changes
3. #165 - Warn on close without tests
4. #166 - Staleness warning (uses #168 config)
5. #162 - Detect uncovered files (watch mode)
6. #144, #145 - Full integration (depends on 1-3)
7. #154, #141 - Run management polish

**Immediate Value:**
- ✅ Tasks track test requirements
- ✅ Pre-commit warns about stale tests
- ✅ Watch mode detects untested code
- ✅ Complete hook integration
- ✅ Run history and cleanup commands

---

### v0.5.0 - Planning & Foundation ⭐ QUICK WINS
**Theme:** Foundational improvements enabling future features
**Priority:** High (unblocks v0.7.0)
**Target:** Q1 2026 (2-3 weeks after v0.4.0)
**Status:** All foundational items, no dependencies, fast to ship

**Issues (5):**
1. **#260** - Clarify Plans vs Milestones vs Projects vs Meta-Issues [HIGH] ⭐
2. **#263** - Implement project priorities registry [HIGH] ⭐
3. **#265** - Add GitHub GraphQL API support [HIGH] ⭐
4. **#266** - Implement documentation coverage tracking [HIGH] ⭐
5. **#261** - Review official MCP servers for integration opportunities [medium]

**Dependencies:**
- None (all foundational)

**Implementation Order:**
1. #260 - Planning concepts (clarifies terminology, informs all future work)
2. #265 - GraphQL API (enables #257 in v0.7.0)
3. #263 - Priorities registry (organizational foundation)
4. #261 - MCP servers review (1-2 day research)
5. #266 - Documentation coverage (automated enforcement)

**Immediate Value:**
- ✅ **Priorities tracking:** YAML-based registry with tiers, validation matrix
- ✅ **Planning clarity:** Clear distinction between Plans/Milestones/Projects/Epics
- ✅ **GraphQL API ready:** For GitHub Projects v2 in v0.7.0
- ✅ **Documentation enforcement:** Pre-commit hooks prevent docs drift
- ✅ **MCP integration options:** Know what's available for future integration

**Enables Future Work:**
- Unblocks #257 (GitHub Projects v2) in v0.7.0
- Informs #264 (structured info system) in v0.6.0
- Provides priorities for #264 to query

---

### v0.6.0 - Structured Information 🎯 FOCUSED EPIC
**Theme:** Token-efficient structured information access with knowledge graph POC
**Priority:** High (strategic differentiation)
**Target:** Q2 2026 (4-5 weeks after v0.5.0)
**Status:** Research + epic, well-scoped

**Issues (2):**
1. **#267** - Investigate NetworkX for knowledge graph POC [HIGH RESEARCH] ⭐
2. **#264** - Token-efficient structured information access system [HIGH EPIC] ⭐

**Dependencies:**
- Optional: #263 (priorities registry from v0.5.0) provides data to query

**Implementation Order:**
1. **#267 - NetworkX POC (1 week)** ⭐ RESEARCH FIRST
   - Standalone program: `tools/knowledge_graph_poc.py`
   - Load IdlerGear data, build graph, demonstrate queries
   - Measure token efficiency (targeting 70%+ savings)
   - **Decision point:** Proceed with graph integration or stay with current approach

2. **#264 - Structured Info System (3-4 weeks)** ⭐ EPIC
   - Phase 1: Document parser (pandoc-based, section extraction)
   - Phase 2: Info command (`idlergear info priorities`, `idlergear info api`)
   - Phase 3: MCP tools (`idlergear_info_query`, `idlergear_info_api`)
   - Phase 4: May use graph representation if #267 POC succeeds
   - **Note:** Will spawn child issues for each phase

**Immediate Value:**
- ✅ **70-90% token savings** for context queries
- ✅ **Query priorities:** `idlergear info priorities --tier tier-1`
- ✅ **Query API docs:** `idlergear info api task.create`
- ✅ **Query references:** `idlergear info ref "token-efficient-context"`
- ✅ **Query documents:** `idlergear info doc README.md --section "Installation"`
- ✅ **GitHub wiki access:** `idlergear info wiki "Architecture" --section "MCP Server"`
- ✅ **Mode-based queries:** minimal/standard/detailed/full for token efficiency
- ✅ **Smart caching:** 0 tokens for unchanged data

**Strategic Value:**
- First tool with universal structured information access
- Works with any document format (via pandoc)
- Query subsections instead of full documents
- Knowledge graph foundation (if POC succeeds)

---

### v0.7.0 - Multi-Assistant & Collaboration 🌐 COMBINED VALUE
**Theme:** Universal AI assistant support and GitHub Projects v2 integration
**Priority:** High (strategic + high-value team features)
**Target:** Q2-Q3 2026 (4-5 weeks after v0.6.0)
**Status:** Combines multi-assistant strategy with GitHub collaboration

**Issues (7):**

**Multi-Assistant Support:**
1. **#262** - Review AI assistant tools for integration opportunities [HIGH] ⭐
2. **#259** - Token-efficient SKILLS.md and AGENTS.md support [HIGH]
3. **#213** - Enhanced Gemini Context in GEMINI.md [medium]
4. **#212** - Implement Gemini CLI Slash Commands [medium]
5. **#214** - Investigate Gemini CLI Lifecycle Hooks [research]

**GitHub Collaboration:**
6. **#257** - GitHub Projects v2 Integration [HIGH]
7. **#256** - Report issues to upstream projects with AI disclaimer [medium]

**Dependencies:**
- #257 requires: #260, #263, #265 from v0.5.0 ✅
- #259 informed by: #262 survey results
- #213, #212 can use: #259 framework

**Implementation Order:**
1. **#262 - AI tools survey (1 week)** ⭐ FOUNDATIONAL
   - Analyze: Claude Code, Gemini CLI, Goose, Aider, Copilot CLI, Cursor
   - Identify integration opportunities
   - Inform #259 design

2. **#259 - AGENTS.md/SKILLS.md support (2 weeks)**
   - Single source: AGENTS.md generates tool-specific files
   - CLAUDE.md, GEMINI.md, .goosehints, .aider.conf.yml, cursor-context.md
   - 90% token reduction (7000 → 700 tokens)
   - Smart caching, context compression modes

3. **#213, #212, #214 - Gemini enhancements (1 week)**
   - Use #259 framework for Gemini
   - Slash commands, enhanced context
   - Hooks investigation (research)

4. **#257 - GitHub Projects v2 (2 weeks)**
   - Bi-directional sync with improved architecture
   - Uses #260 (planning concepts), #263 (priorities), #265 (GraphQL)
   - Kanban boards, custom fields, milestone awareness
   - Release readiness validation

5. **#256 - Upstream issue reporting (3 days)**
   - Use GitHub credentials to report issues
   - AI-generated disclaimer, ethical templates
   - Local tracking of external issues

**Immediate Value:**
- ✅ **Universal AI assistant support:** Works with Claude, Gemini, Goose, Aider, Cursor, Copilot CLI
- ✅ **Write once, run everywhere:** Single AGENTS.md for all tools
- ✅ **90% token savings:** Smart context compression
- ✅ **Visual project boards:** GitHub Projects v2 Kanban
- ✅ **Upstream contributions:** Report issues to dependencies with AI attribution
- ✅ **Switch tools freely:** No vendor lock-in, preserve project knowledge

**Strategic Value:**
- First tool with universal AI assistant support
- Token efficiency as competitive advantage
- Team collaboration via visual boards
- Ethical AI-generated issue reporting

---

### v0.8.0 - Developer Experience & Polish 💎 PRODUCTION READY
**Theme:** Quality of life improvements, comprehensive documentation, production readiness
**Priority:** Medium-High (polish & stability)
**Target:** Q4 2026 - Q1 2027 (2-4 weeks after v0.7.0)
**Status:** Independent improvements + comprehensive polish

**Issues (2 + polish):**
1. **#258** - Auto-mark managed files for exclusion [medium]
2. **#255** - External Command Queue for IPC [medium]

**Plus:**
- Comprehensive documentation review
- Performance optimization
- Bug fixes and stability improvements
- User experience refinement
- Test coverage improvements (>85%)
- Real-world deployment validation

**Implementation Order:**
1. #258 - Managed file exclusion (helps with #255)
2. #255 - Command queue (advanced IPC)
3. Documentation pass (all features from v0.4-v0.7)
4. Performance profiling and optimization
5. Bug triage and fixes
6. UX improvements based on usage

**Immediate Value:**
- ✅ **Cleaner repositories:** Auto-update .gitignore for IdlerGear files
- ✅ **Better IPC:** File-based command queue for external processes
- ✅ **Test notifications:** Long-running tests notify on completion
- ✅ **CI/CD integration:** Background jobs communicate with sessions
- ✅ **Complete documentation:** All features fully documented
- ✅ **Production quality:** Performance benchmarks, high test coverage
- ✅ **Stable API:** Ready for broader adoption

**Goals:**
- High test coverage (>85%)
- Complete user documentation
- Performance benchmarks established
- Real-world deployments validated
- Community feedback incorporated
- **Note:** v1.0 will come when truly production-ready, not on fixed timeline

---

## Dependencies Graph

```
v0.4.0 (Test & Run) - No dependencies
├── ✅ #168 Test config (COMPLETE)
├── ✅ #167 Test blocking (COMPLETE)
└── #163 → #164 → #165 → #166
    └── #144, #145 (integration)
    └── #154, #141 (polish)

v0.5.0 (Planning & Foundation) - No dependencies ⭐ QUICK WINS
├── #260 (Planning concepts) ⭐ FOUNDATIONAL
├── #265 (GraphQL API) ⭐ ENABLES v0.7.0
├── #263 (Priorities registry) ⭐ FOUNDATIONAL
├── #261 (MCP survey - 1-2 day research)
└── #266 (Documentation coverage)

v0.6.0 (Structured Information) - Optional dependency on v0.5.0
├── #267 (NetworkX POC) ⭐ RESEARCH FIRST (1 week)
│   └── Decision: graph-based or traditional
└── #264 (Structured info system) ⭐ EPIC (3-4 weeks)
    ├── May use #267 graph representation
    ├── Can query #263 priorities (from v0.5.0)
    └── Will spawn child issues

v0.7.0 (Multi-Assistant & Collaboration) - Depends on v0.5.0
├── #262 (AI tools survey) ⭐ FOUNDATIONAL (1 week)
├── #259 (AGENTS.md/SKILLS.md) ← informed by #262 (2 weeks)
│   ├── #213 (Gemini context)
│   ├── #212 (Gemini commands)
│   └── #214 (Gemini hooks - research)
└── GitHub collaboration
    ├── #257 (Projects v2) ← REQUIRES #260, #263, #265 from v0.5.0 ✅
    └── #256 (Upstream reporting)

v0.8.0 (Developer Experience & Polish) - No dependencies
├── #258 (File management)
├── #255 (Command queue)
└── Comprehensive polish
    ├── Documentation (all v0.4-v0.7 features)
    ├── Performance optimization
    ├── Bug fixes
    └── UX improvements
```

---

## Priority Tiers

### HIGH (Foundational - Ship First):
- **v0.5.0 all issues** (#260, #263, #265, #266, #261) ⭐ QUICK WINS
- **v0.6.0 all issues** (#267, #264) ⭐ STRATEGIC
- **v0.7.0 surveys + key features** (#262, #259, #257)

### MEDIUM (Important - Ship After Foundation):
- **v0.4.0 all issues** (#163-166, #162, #144, #145, #154)
- **v0.7.0 enhancements** (#213, #212, #256)
- **v0.8.0 all issues** (#258, #255)

### LOW (Polish):
- **v0.4.0 documentation** (#141)

### RESEARCH (Inform Implementation):
- **v0.6.0 POC** (#267) ⭐ BLOCKING (informs #264 architecture)
- **v0.7.0 surveys** (#262, #214) ⭐ FOUNDATIONAL (informs #259)

---

## Implementation Timeline

Based on recent progress (10 issues completed in 1 session):

| Milestone | Duration | Target | Cumulative |
|-----------|----------|--------|------------|
| v0.4.0 - Test & Run | 2-3 weeks | Q1 2026 | ~3 weeks |
| v0.5.0 - Planning & Foundation ⭐ | 2-3 weeks | Q1 2026 | ~6 weeks |
| v0.6.0 - Structured Information | 4-5 weeks | Q2 2026 | ~11 weeks |
| v0.7.0 - Multi-Assistant & Collaboration | 4-5 weeks | Q2-Q3 2026 | ~16 weeks |
| v0.8.0 - Developer Experience & Polish | 2-4 weeks | Q4 2026 - Q1 2027 | ~20 weeks |

**Total estimated timeline:** ~14-20 weeks to v0.8.0 (Q1 2026 → Q1 2027)

**Key Changes from Previous Plan:**
- ✅ v0.5.0 ships **2-3 weeks faster** (was 5-6 weeks, now 2-3 weeks)
- ✅ Each milestone has **immediate value** (no research-only releases)
- ✅ v0.7.0 combines related features for **coherent release**
- ✅ Dependencies respected (v0.5.0 unblocks v0.7.0)
- ✅ Similar total timeline but **better incremental adoption**

**Notes:**
- Epic #264 will spawn child issues for each phase
- POC #267 will inform #264 architecture (graph-based or traditional)
- Survey issues (#261, #262) may spawn child issues based on findings
- Each milestone can be adopted independently

---

## Risk Assessment

### Low Risk (Ready to Ship):
- **v0.4.0** - Incremental improvements to existing features
- **v0.5.0** - All foundational, no dependencies, clear scope ⭐ FASTEST

### Medium Risk (Well-Scoped):
- **v0.6.0** - Research-informed implementation, POC validates approach
- **v0.8.0** - Independent quality improvements, well-understood work

### High Risk (Requires Careful Implementation):
- **v0.7.0** - GitHub API complexity, bidirectional sync, multi-assistant integration

**Mitigation Strategies:**
- **Phased rollout per milestone** - Each release is independently stable
- **POC before architecture** - #267 validates NetworkX before #264 implementation
- **Surveys inform design** - #262, #261 research before #259 implementation
- **Extensive testing for v0.7.0** - High-risk milestone gets extra attention
- **Beta period for v0.8.0** - Community feedback before final polish
- **v1.0 when ready** - No rush, ship when truly production-ready

---

## Incremental Value Proposition

Each milestone ships immediately useful features:

| After v0.4.0 | After v0.5.0 ⭐ | After v0.6.0 | After v0.7.0 | After v0.8.0 |
|--------------|----------------|--------------|--------------|--------------|
| ✅ Test tracking | ✅ Priorities registry | ✅ Token-efficient queries | ✅ Universal AI support | ✅ Production quality |
| ✅ Run history | ✅ Planning clarity | ✅ Query API docs | ✅ Visual project boards | ✅ Complete docs |
| ✅ Hook integration | ✅ GraphQL ready | ✅ Query priorities | ✅ Upstream contributions | ✅ Performance optimized |
| | ✅ Docs enforcement | ✅ Document parser | ✅ Switch AI tools freely | ✅ High test coverage |
| | | ✅ GitHub wiki access | | ✅ Stable API |

**Philosophy:** You can start using features from each milestone immediately. No waiting for "v1.0" to get value.

---

## Next Steps

1. ✅ **Issues assigned to new milestones** (COMPLETE)
2. ✅ **Old empty milestones closed** (#7, #8 closed)
3. ✅ **Obsolete note issues closed** (#232 closed)
4. ✅ **ROADMAP.md updated** (this document)
5. **Start v0.4.0 implementation** - First stable release with test awareness
6. **Communicate roadmap** - Share with users, gather feedback
7. **Update README.md** - Link to roadmap, highlight v0.5.0 quick wins

---

## Changelog from Previous Roadmap

**Major Restructuring:**
1. **v0.5.0 split** - Foundation items moved to new quick-wins v0.5.0
2. **v0.6.0 refocused** - Now purely structured information + POC (was GitHub Integration)
3. **v0.7.0 expanded** - Combined multi-assistant + GitHub collaboration (related features together)
4. **v0.8.0 enhanced** - Added developer experience to polish milestone
5. **Timeline optimized** - v0.5.0 now ships 2-3 weeks faster (was 5-6 weeks)
6. **Dependencies clarified** - v0.5.0 unblocks v0.7.0, v0.6.0 POC informs implementation
7. **Incremental value emphasized** - Each milestone independently useful

**Result:** Better incremental adoption, faster time-to-value, clearer dependencies.
