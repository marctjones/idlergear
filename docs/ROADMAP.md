# IdlerGear Roadmap & Release Plan

## Executive Summary

**Current Version:** v0.7.11
**Latest Milestone:** v0.8.0 - Session Management Advanced ✅
**Next Milestone:** v0.9.0 - Multi-Assistant & Collaboration

**Milestones Completed:** 4 of 6
- ✅ v0.5.11 - Plugin System Foundation
- ✅ v0.6.0 - File Registry Complete
- ✅ v0.7.0 - GitHub Integration
- ✅ v0.8.0 - Session Management Advanced
- 🚧 v0.9.0 - Multi-Assistant & Collaboration (17 open issues)
- 📋 v0.10.0 - Polish & Maturity (4 open issues)

**Philosophy:** Ship incrementally stable releases with useful features. Each milestone is independently valuable and can be adopted immediately.

---

## Completed Milestones

### ✅ v0.5.11 - Plugin System Foundation (Released)

**Theme:** Integrate with best-in-class intelligence tools
**Shipped:** 2026-01-11

**Key Features:**
- Plugin system (6 CLI tools, 6 MCP tools)
- LlamaIndex integration for semantic search
- Langfuse integration for observability
- Mem0 integration foundation
- Local embeddings with zero-config setup

**Impact:**
- 40% faster retrieval with semantic search
- Token tracking and cost monitoring
- Persistent vector storage

---

### ✅ v0.6.0 - File Registry Complete (Released)

**Theme:** Prevent AI from using outdated code
**Shipped:** 2026-01-21

**Key Features:**
- File status tracking (current/deprecated/archived/problematic)
- Automatic MCP file access interception
- File annotations (93% token savings on discovery)
- Multi-agent coordination via daemon broadcasts
- Access logging for audit trails

**Impact:**
- Prevents AI from reading deprecated files
- Search annotations instead of grep (200 vs 15,000 tokens)
- Real-time file registry updates across all agents

---

### ✅ v0.7.0 - GitHub Integration (Released)

**Theme:** Bidirectional sync with GitHub Projects v2
**Shipped:** 2026-01-24

**Key Features:**
- GitHub Projects v2 sync (create, link, bidirectional updates)
- Custom field sync (priority, due dates, labels)
- Status column mapping (auto-move tasks between columns)
- Vision/reference/plan sync to GitHub
- Token-efficient project queries

**Impact:**
- Visual Kanban boards in GitHub Projects UI
- Automatic task movement based on state
- Rich metadata in GitHub custom fields
- GitHub as source of truth for team collaboration

---

### ✅ v0.8.0 - Session Management Advanced (Released)

**Theme:** Experimental branching, knowledge harvesting, containerization
**Shipped:** 2026-01-25

**Key Features:**
- **Session Branching** - Git-like branching for experimental work
  - Create/checkout/merge/abandon branches
  - Compare branches with detailed diffs
  - Full lineage tracking with parent pointers
- **Knowledge Harvesting** - Extract insights from completed sessions
  - Harvest tasks, focus areas, tool usage
  - Identify patterns across multiple sessions
  - Save insights as notes
- **Container Support** - Isolated execution with Podman/Docker
  - Resource limits (memory, CPU)
  - Containerized testing infrastructure
  - Multi-version testing (Python 3.10, 3.11, 3.12)
- **Tmux Integration** - Persistent terminal sessions

**Impact:**
- Try multiple approaches without losing work
- Learn from session patterns and tool usage
- Reproducible test environments
- Success rate tracking over time

---

## Remaining Milestones

### 🚧 v0.9.0 - Multi-Assistant & Collaboration

**Theme:** Cross-assistant coordination and shared knowledge
**Target:** June 2026 (5-6 months)
**Status:** 17 open issues

**Planned Features:**

**Multi-Agent Coordination:**
1. **#279** - Daemon integration for multi-client monitoring [medium]
   - Real-time session monitoring across multiple AI assistants
   - Command queue for async task distribution
   - Broadcast messages to all active agents
   - Agent registration and heartbeat

2. **#313** - Memory decay and relevance scoring [medium]
   - Time-based relevance for notes and tasks
   - Decay functions for old knowledge
   - Boost frequently accessed items
   - Smart pruning of stale knowledge

**Cross-Session Knowledge:**
3. Session knowledge sharing between agents
4. Collaborative task management
5. Shared context pools

**Enhanced AI Integration:**
6. **#262** - Review AI assistant tools for integration opportunities [HIGH]
7. **#259** - Token-efficient SKILLS.md and AGENTS.md support [HIGH]
8. **#213** - Enhanced Gemini Context in GEMINI.md [medium]
9. **#212** - Implement Gemini CLI Slash Commands [medium]
10. **#214** - Investigate Gemini CLI Lifecycle Hooks [research]

**GitHub Collaboration:**
11. **#256** - Report issues to upstream projects with AI disclaimer [medium]

**Immediate Value:**
- ✅ Multiple AI assistants working on same codebase
- ✅ Shared knowledge across tools (Claude, Gemini, Goose, Aider, Cursor)
- ✅ Async task distribution
- ✅ Smart knowledge pruning
- ✅ Cross-tool session continuity

**Dependencies:**
- None (all foundational work complete in v0.7-v0.8)

**Implementation Order:**
1. #279 - Daemon integration (1-2 weeks)
2. #313 - Memory decay system (1-2 weeks)
3. #262 - AI assistant survey (1 week)
4. #259 - SKILLS.md/AGENTS.md framework (2 weeks)
5. #213, #212, #214 - Gemini enhancements (1 week)
6. #256 - Upstream issue reporting (3 days)

---

### 📋 v0.10.0 - Polish & Maturity

**Theme:** Production readiness and stability
**Target:** September 2026 (9 months)
**Status:** 4 open issues

**Planned Features:**

**Testing & Quality:**
1. **#109** - Comprehensive test plan: ~350 additional tests needed
   - Increase coverage to 80%+
   - Integration test suite expansion
   - Edge case coverage
   - Performance regression tests

**AI Training:**
2. **#94** - AI assistant adoption: Training LLMs to use IdlerGear for read AND write
   - Fine-tuning examples
   - Prompt engineering best practices
   - Read/write pattern recognition

**Advanced Features:**
3. **#72** - Create IdlerGear as Claude Code Plugin [medium]
   - Native plugin integration
   - Enhanced IDE features
   - Direct access from Claude Code UI

4. **#28** - Local wiki with multi-interface viewers (CLI, Textual, Kivy) [low]
   - Rich local wiki interface
   - Multiple viewing options
   - Offline-first design

**Immediate Value:**
- ✅ Production-grade stability
- ✅ 80%+ test coverage
- ✅ AI assistants trained on IdlerGear patterns
- ✅ Native IDE integration

**Implementation Order:**
1. #109 - Test coverage expansion (4-6 weeks)
2. #94 - AI training materials (2-3 weeks)
3. #72 - Claude Code plugin (2-3 weeks)
4. #28 - Local wiki (if time permits)

---

## Release Schedule

| Milestone | Target Date | Weeks | Status |
|-----------|-------------|-------|--------|
| v0.5.11 | Jan 2026 | - | ✅ Released |
| v0.6.0 | Jan 2026 | - | ✅ Released |
| v0.7.0 | Jan 2026 | - | ✅ Released |
| v0.8.0 | Jan 2026 | - | ✅ Released |
| **v0.9.0** | **Jun 2026** | **~20** | 🚧 In Progress |
| **v0.10.0** | **Sep 2026** | **~12** | 📋 Planned |

**Total time to v1.0:** ~9 months from now (September 2026)

---

## Path to v1.0

After v0.10.0, a final v1.0 release will:
1. Freeze the API
2. Provide LTS support guarantees
3. Document upgrade paths
4. Establish deprecation policies
5. Release production-ready documentation

**Estimated v1.0 release:** October 2026

---

## Issue Distribution

| Milestone | Total | Open | Closed | % Complete |
|-----------|-------|------|--------|-----------|
| v0.5.11 | - | 0 | - | 100% |
| v0.6.0 | - | 0 | - | 100% |
| v0.7.0 | 14 | 0 | 14 | 100% |
| v0.8.0 | 13 | 0 | 13 | 100% |
| v0.9.0 | 17 | 17 | 0 | 0% |
| v0.10.0 | 4 | 4 | 0 | 0% |
| **Total** | **48** | **21** | **27** | **56%** |

---

## Strategic Priorities

### High Priority (Must-Have for v1.0)
1. Multi-agent coordination (#279)
2. Memory decay and relevance (#313)
3. Test coverage expansion (#109)
4. AI assistant survey (#262)
5. SKILLS.md/AGENTS.md support (#259)

### Medium Priority (Should-Have)
1. Gemini enhancements (#213, #212, #214)
2. Upstream issue reporting (#256)
3. AI training materials (#94)
4. Claude Code plugin (#72)

### Low Priority (Nice-to-Have)
1. Local wiki with multi-interface (#28)
2. Additional polish features

---

## Success Metrics

**v0.9.0 Success Criteria:**
- [ ] 3+ AI assistants can work simultaneously on same codebase
- [ ] Daemon handles 10+ concurrent agents
- [ ] Memory decay pruning reduces context size by 30%+
- [ ] SKILLS.md/AGENTS.md reduces token usage by 90%+

**v0.10.0 Success Criteria:**
- [ ] 80%+ test coverage
- [ ] 0 critical bugs in production
- [ ] AI assistants use IdlerGear for read AND write operations
- [ ] Documentation complete and comprehensive

**v1.0 Success Criteria:**
- [ ] API stable and frozen
- [ ] Production deployments in use
- [ ] Community contributions accepted
- [ ] LTS support plan established

---

## Links

- **[Project Board](https://github.com/users/marctjones/projects/18)** - Visual roadmap
- **[Milestones](https://github.com/marctjones/idlergear/milestones)** - GitHub milestones
- **[Issues](https://github.com/marctjones/idlergear/issues)** - All open issues
- **[CHANGELOG](../CHANGELOG.md)** - Release history
