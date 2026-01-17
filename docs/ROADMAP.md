# IdlerGear Roadmap & Issue Prioritization

## Executive Summary

**Total Open Issues:** 31
- **Actionable Features:** 20
- **Research/Notes:** 11 (knowledge capture, not blocking)

**Current Version:** v0.3.67

---

## Milestone Structure

### v0.4.0 - Test & Run Management
**Theme:** Complete test framework integration and run management polish
**Priority:** High (foundational for developer workflows)
**Target:** Q1 2026

**Issues (9):**
1. **#163** - Add --needs-tests flag to task create [medium]
2. **#164** - Track test file changes in task commits [medium]
3. **#165** - Warn on task close if needs-tests but no tests added [medium]
4. **#166** - Add test staleness warning to pre-commit hook [low → medium]
5. **#162** - Detect new files without test coverage in watch mode [low → medium]
6. **#144** - ig test Phase 3: Task integration [low → medium]
7. **#145** - ig test Phase 4: Hook integration [low → medium]
8. **#154** - Add ig run history and clean commands [low → medium]
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

**Key Features:**
- Tasks track test requirements
- Pre-commit warns about stale tests
- Watch mode detects untested code
- Complete hook integration
- Run history and cleanup commands

---

### v0.5.0 - Multi-Assistant Context
**Theme:** Universal AGENTS.md/SKILLS.md support with token efficiency
**Priority:** High (strategic differentiation)
**Target:** Q2 2026

**Issues (4):**
1. **#259** - Token-efficient SKILLS.md and AGENTS.md support [medium → HIGH]
2. **#213** - Enhanced Gemini Context in GEMINI.md [low → medium]
3. **#212** - Implement Gemini CLI Slash Commands [low → medium]
4. **#214** - Investigate Gemini CLI Lifecycle Hooks [research]

**Dependencies:**
- Existing: CLAUDE.md, GEMINI.md, .goosehints support
- MCP server (126 tools already implemented)

**Implementation Order:**
1. #214 - Research Gemini hooks (inform design)
2. #259 - Core AGENTS.md/SKILLS.md compression (FOUNDATIONAL)
3. #213 - Enhance GEMINI.md using #259 framework
4. #212 - Gemini slash commands

**Key Features:**
- 90% token reduction (7000 → 700 tokens)
- Single source: AGENTS.md generates CLAUDE.md, GEMINI.md, .goosehints, .aider.conf.yml
- Smart caching (0 tokens for unchanged sessions)
- Context compression: minimal/standard/full modes
- MCP tool: `idlergear_inject_context`

**Strategic Value:**
- First tool with universal AI assistant support
- Token efficiency as competitive advantage
- Write once, run everywhere for context

---

### v0.6.0 - GitHub Integration
**Theme:** Enhanced GitHub Projects v2 and upstream collaboration
**Priority:** Medium (team collaboration focus)
**Target:** Q3 2026

**Issues (2):**
1. **#257** - GitHub Projects v2 Integration [medium → HIGH]
2. **#256** - Report issues to upstream projects with AI disclaimer [medium]

**Dependencies:**
- ✅ GitHub backend (fully implemented)
- ✅ Label management (#206, #207, #209 - COMPLETE)

**Implementation Order:**
1. #257 - Projects v2 sync (foundational, enables visual project management)
2. #256 - Upstream issue reporting (builds on GitHub backend)

**Key Features:**
- Bi-directional GitHub Projects sync
- Kanban boards auto-updated from IdlerGear
- Custom field mapping (priority, effort, due dates)
- Upstream issue reporting with AI attribution
- Ethical disclosure templates
- Local tracking of external issues

**Use Cases:**
- Team collaboration via visual boards
- Sprint planning with Kanban
- Contributing to dependencies
- Multi-repo project tracking

---

### v0.7.0 - Developer Experience
**Theme:** Quality of life improvements for IdlerGear users
**Priority:** Low-Medium (polish & convenience)
**Target:** Q4 2026

**Issues (2):**
1. **#258** - Auto-mark managed files for exclusion [medium]
2. **#255** - External Command Queue for IPC [medium]

**Dependencies:**
- None (independent improvements)

**Implementation Order:**
1. #258 - Managed file exclusion (helps with #255)
2. #255 - Command queue (advanced IPC)

**Key Features:**
- Auto-update .gitignore for IdlerGear files
- Manifest of managed files
- File-based command queue for external processes
- Test runners can notify Claude Code sessions
- Background jobs send completion notifications

**Use Cases:**
- Cleaner repository (no IdlerGear noise)
- AI agents ignore infrastructure files
- Long-running tests notify on completion
- CI/CD integration with active sessions

---

### v1.0.0 - Stable Release
**Theme:** Production-ready, comprehensive documentation, stable APIs
**Priority:** Critical (milestone)
**Target:** Q1 2027

**Requirements:**
- All v0.4-v0.7 features complete
- Comprehensive documentation
- Migration guides
- Backward compatibility guarantees
- Performance benchmarks
- Security audit
- API stability commitment

**Exit Criteria:**
- No critical bugs
- >90% test coverage
- Documentation complete
- 3+ real-world deployments
- Performance baselines met

---

## Priority Changes Summary

### Upgraded to HIGH:
- **#259** - AGENTS.md/SKILLS.md support (strategic importance)
- **#257** - GitHub Projects v2 (high value, enables team workflows)

### Upgraded to MEDIUM:
- **#163-166** - Test framework features (foundational for v0.4)
- **#162** - Watch mode test coverage (completes test workflow)
- **#144, #145** - Test phases (integration work)
- **#154** - Run history (polish existing feature)
- **#213, #212** - Gemini features (support growing user base)

### Maintained LOW:
- **#141** - Run documentation (polish only)

### Research (Non-Blocking):
- **#214** - Gemini hooks investigation

---

## Dependencies Graph

```
v0.4.0 (Test & Run)
├── ✅ #168 Test config (DONE)
├── ✅ #167 Test blocking (DONE)
└── #163 → #164 → #165 → #166
    └── #144, #145 (integration)

v0.5.0 (Multi-Assistant)
├── #214 (research)
└── #259 (foundation)
    ├── #213 (Gemini context)
    └── #212 (Gemini commands)

v0.6.0 (GitHub)
├── ✅ GitHub backend (DONE)
├── ✅ Label management (DONE)
├── #257 (Projects sync)
└── #256 (Upstream reporting)

v0.7.0 (Dev Experience)
├── #258 (File management)
└── #255 (Command queue)

v1.0.0 (Release)
├── v0.4.0 complete
├── v0.5.0 complete
├── v0.6.0 complete
└── v0.7.0 complete
```

---

## Research/Note Issues (Non-Blocking)

These are knowledge capture, not actionable work items:

- #217 - Daemon architecture notes
- #218 - Project status analysis
- #219 - Session summary
- #220 - Goose integration analysis
- #221 - Tool usage analysis
- #222 - MCP opportunities
- #223 - Naming convention decision
- #224 - MCP filesystem research
- #225 - MCP git research
- #226 - MCP environment research
- #227 - MCP dependency analysis
- #228 - Node.js replacement decision
- #232 - OTel database evaluation
- #235 - Context modes implementation note
- #249 - Messaging limitation note

**Action:** These should be:
1. Converted to reference documents (if valuable)
2. Closed (if obsolete)
3. Promoted to tasks (if actionable)

---

## Next Steps

1. **Assign issues to milestones** (via GitHub CLI)
2. **Update priority labels** (low → medium/high as noted)
3. **Close/convert note issues** (research → references or tasks)
4. **Document roadmap** (add to README.md)
5. **Start v0.4.0** (next minor release)

---

## Implementation Velocity Estimate

Based on recent progress (10 issues completed in 1 session):

- **v0.4.0** (9 issues) - ~2-3 weeks
- **v0.5.0** (4 issues) - ~2-3 weeks
- **v0.6.0** (2 issues) - ~1-2 weeks
- **v0.7.0** (2 issues) - ~1 week
- **v1.0.0** (polish) - ~2-4 weeks

**Total estimated timeline:** ~8-13 weeks (Q1-Q2 2026)

---

## Risk Assessment

### Low Risk:
- v0.4.0 - Incremental improvements to existing features
- v0.7.0 - Independent quality improvements

### Medium Risk:
- v0.6.0 - GitHub API complexity, bidirectional sync

### High Risk:
- v0.5.0 - Multi-assistant support requires deep integration
- v1.0.0 - Stability guarantees and API freeze

**Mitigation:**
- Phased rollout per milestone
- Extensive testing for v0.5.0
- Beta period before v1.0.0
