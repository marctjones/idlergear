# IdlerGear Release Roadmap & Milestone Reorganization

## Current State (January 2026)
- **Current Version**: v0.5.19
- **Open Issues**: 5 (all for future milestones)
- **Completed Milestones**: v0.4.0, v0.5.0, v0.6.0 (original), v0.7.0 (original)
- **Active Milestones**: v0.6.0 (in progress), v0.7.0 (planned), v0.8.0 (5 issues), v0.9.0 (planned)
- **Recent Completions**: File Registry core (#287-289, #294), AI Assistant Integrations (#299, #300)

## Problem Analysis

### Issues
1. **Milestone bloat**: Completed milestones (v0.4-v0.7) still open
2. **Version gap**: Current version 0.5.4, but next milestone is v0.8.0
3. **Unorganized work**: 15 critical issues have no milestone
4. **No epics**: Large features not properly grouped
5. **Missing release dates**: No target dates for planning
6. **Project board outdated**: Doesn't reflect current priorities

### Opportunities
1. File Registry is ready to implement (10 detailed tasks)
2. Clear feature groupings emerging
3. Good balance of near-term and long-term work

## New Release Structure

### Release Philosophy
- **Minor releases** (0.x.0): Every 2-3 months with major features
- **Patch releases** (0.x.y): As needed for bug fixes
- **Stable v1.0**: When core feature set is complete and battle-tested

### Release Cadence
- Q1 2026 (March): v0.6.0 - File Registry & Quality
- Q2 2026 (June): v0.7.0 - GitHub Integration
- Q3 2026 (September): v0.8.0 - Session Management Advanced
- Q4 2026 (December): v0.9.0 - Multi-Assistant & Collaboration
- Q1 2027 (March): v0.10.0 - Polish & Maturity

---

## v0.6.0 - File Registry & Quality
**Target**: March 1, 2026 (6 weeks)
**Theme**: Major new feature + quality improvements
**Status**: In Progress - Core features completed, advanced features remain

### Epic: File Registry & Deprecated File Detection (#286)
**Problem**: AI assistants access outdated/archived files causing bugs
**Solution**: Explicit registry with MCP interception
**Priority**: HIGH - Solves critical user pain point

#### Phase 1: Core Infrastructure (Weeks 1-2) ✅ COMPLETED
- ✅ #287: FileRegistry data model and storage (HIGH, Medium effort) - Implemented in file_registry.py
- ✅ #288: CLI commands for registry management (HIGH, Medium effort) - 7 commands in cli.py
- ✅ #289: MCP tools for AI assistant access (HIGH, Small effort) - 8 MCP tools in mcp_server.py

#### Phase 2: MCP Interception (Weeks 2-3)
- #290: MCP tool interception for file operations (HIGH, Large effort) ⭐ **Critical**

#### Phase 3: Multi-Agent Coordination (Week 4)
- #291: Daemon integration for registry broadcasts (MEDIUM, Medium effort)

#### Phase 4: Auto-Detection & Polish (Weeks 5-6)
- #292: Auto-detection scanner (LOW, Medium effort)
- #293: Audit command (LOW, Small effort)
- #295: Performance optimization (LOW, Small effort)

#### Phase 5: Testing & Documentation (Week 6)
- #296: End-to-end integration testing (HIGH, Medium effort)
- ✅ #294: User guide and documentation (MEDIUM, Small effort) - Comprehensive docs created

### AI Assistant Integrations ✅ LARGELY COMPLETED
- ✅ #299: Cursor AI IDE Integration - .mdc rules generation complete
- ✅ #300: Aider Configuration - .aider.conf.yml generation complete
- ⚠️ #298: GitHub Copilot CLI Integration - Template complete, MCP testing pending
- ✅ Gemini CLI - GEMINI.md enhanced with comprehensive guidance
- ✅ Goose - .goosehints integration complete
- ✅ AGENTS.md - Enhanced with comprehensive multi-assistant guidance (205 lines)

### Quality Improvements
- #285: Fix pipx installation support (HIGH priority)

### Success Criteria
- ✅ AI blocked from reading deprecated files 95% of time
- ✅ Registry setup takes < 5 minutes
- ✅ Changes propagate to all agents within 1 second
- ✅ Performance overhead < 10ms per file operation
- ✅ pipx installation works correctly

---

## v0.7.0 - GitHub Integration
**Target**: June 1, 2026 (12 weeks from now)
**Theme**: Enhanced GitHub workflow integration
**Status**: Detailed design needed

### GitHub Projects v2 Sync
- #257: Feature Request: GitHub Projects v2 Integration (EPIC)
- #282: Status column mapping for GitHub Projects (HIGH)
- #283: Custom field sync for GitHub Projects (MEDIUM)
- #284: Bidirectional sync for GitHub Projects (HIGH)

### Dependencies
- Requires stable v0.6.0 release
- Needs GitHub Projects v2 API research

### Success Criteria
- ✅ Bidirectional sync with GitHub Projects v2
- ✅ Custom fields mapped correctly
- ✅ Status updates propagate both ways
- ✅ No data loss during sync

---

## v0.8.0 - Session Management Advanced
**Target**: September 1, 2026 (18 weeks from now)
**Theme**: Advanced session capabilities
**Status**: Design in progress

### Epic: Advanced Session Management (#271)
- #273: Session branching and merging (MEDIUM)
- #274: Session knowledge harvesting (MEDIUM)
- #275: Session analytics and monitoring (MEDIUM)
- #279: Daemon integration for multi-client monitoring (MEDIUM)

### Dependencies
- Requires v0.6.0 (daemon registry integration)
- Builds on v0.7.0 (project sync foundation)

### Success Criteria
- ✅ Branch/merge sessions without data loss
- ✅ Harvest knowledge from completed sessions
- ✅ Monitor multiple concurrent sessions
- ✅ Analytics show session productivity metrics

---

## v0.9.0 - Multi-Assistant & Collaboration
**Target**: December 1, 2026 (24 weeks from now)
**Theme**: Multi-assistant orchestration
**Status**: Research phase

### Gemini Integration
- #212: Implement Gemini CLI Slash Commands (MEDIUM)
- #213: Enhanced Gemini Context in GEMINI.md (MEDIUM)
- #214: Investigate Gemini CLI Lifecycle Hooks (LOW)

### Multi-Assistant Support
- #259: SKILLS.md and AGENTS.md support for all AI assistants (MEDIUM)
- #262: Review AI assistant tools for IdlerGear integration (LOW)

### Dependencies
- Requires v0.8.0 (session management)
- Needs Gemini API research

### Success Criteria
- ✅ Gemini integrated with full feature parity
- ✅ SKILLS.md/AGENTS.md work across all assistants
- ✅ Multiple assistants can coordinate on same project
- ✅ Clear documentation for each supported assistant

---

## v0.10.0 - Polish & Maturity
**Target**: March 1, 2027 (30 weeks from now)
**Theme**: Pre-release maturity milestone
**Status**: Preparing for eventual 1.0 after extended stability period

### Polish & UX
- #281: Expand 'idle*' standalone command pattern (LOW)
- #258: Auto-mark managed files for exclusion (MEDIUM)
- #255: External Command Queue for IPC (MEDIUM)
- #256: Report issues to upstream with disclaimer (LOW)

### Maturity Goals
- ✅ All v0.9.0 features stable for 3+ months
- ✅ 80%+ test coverage on core features
- ✅ Comprehensive documentation
- ✅ No critical bugs
- ✅ Production validation at multiple sites
- ✅ API stability improvements
- ✅ Performance benchmarks established

**Note**: True v1.0 will come when production-ready, not on a fixed timeline.

---

## Milestone Cleanup Actions

### Close Completed Milestones
These milestones have 0 open issues and should be closed:
- v0.4.0 Release (5 closed issues)
- v0.5.0 - Planning & Foundation (7 closed issues)
- v0.6.0 - Structured Information (3 closed issues)
- v0.7.0 - Session Management Foundation (4 closed issues)

### Delete Outdated Milestone
- v0.8.0 - Session Management Advanced
  - **Reason**: Should be v0.8.0, not v0.8.0 (wrong version number)
  - **Action**: Move issues to new v0.8.0, delete old

---

## Issue Prioritization Framework

### Priority Levels
- **CRITICAL**: Blocks release or causes data loss
- **HIGH**: Major feature or significant bug
- **MEDIUM**: Important but not blocking
- **LOW**: Nice-to-have or future enhancement

### Priority Assignment by Milestone

**v0.6.0 (File Registry)**
- Critical: #290 (MCP interception - core feature)
- High: #287, #288, #289, #296, #285
- Medium: #291, #294
- Low: #292, #293, #295

**v0.7.0 (GitHub Integration)**
- High: #282, #284
- Medium: #283

**v0.8.0 (Session Management)**
- Medium: #273, #274, #275, #279
- (Lower priority as it's further out)

**v0.9.0 (Multi-Assistant)**
- Medium: #212, #213, #259
- Low: #214, #262

**v0.10.0 (Stable)**
- Medium: #255, #258
- Low: #256, #281

---

## Epic Structure

### What is an Epic?
Large features that span multiple issues and require coordination.

### Epic Label Creation
Create label: `epic` (color: #5319e7, description: "Large feature spanning multiple issues")

### Current Epics

1. **Epic #286**: File Registry & Deprecated File Detection System
   - Sub-tasks: #287-#296 (10 issues)
   - Milestone: v0.6.0
   - Owner: Core team
   - Status: Ready to implement

2. **Epic #271**: Advanced Session Management
   - Sub-tasks: #273-#275, #279 (4 issues)
   - Milestone: v0.8.0
   - Owner: TBD
   - Status: Design phase

3. **Epic #257**: GitHub Projects v2 Integration
   - Sub-tasks: #282-#284 (3 issues)
   - Milestone: v0.7.0
   - Owner: TBD
   - Status: Needs design

### Future Epics (Create Later)
- Multi-Assistant Coordination (v0.9.0)
- Knowledge Graph Enhancement
- Test Automation System

---

## GitHub Project Board Structure

### Recommended Structure

#### Option 1: Single Unified Board
**Project Name**: "IdlerGear Development Roadmap"

**Columns**:
- 📋 Backlog (no milestone or v1.0+)
- 🎯 Current Sprint (v0.6.0 high priority)
- 🚧 In Progress
- 👀 In Review
- ✅ Done (last 2 weeks)

**Views**:
- By Milestone (grouped)
- By Epic (filtered)
- By Priority (sorted)
- Current Sprint (v0.6.0 only)

#### Option 2: Per-Release Boards
- v0.6.0 - File Registry & Quality
- v0.7.0 - GitHub Integration
- v0.8.0 - Session Management Advanced
- v0.9.0 - Multi-Assistant & Collaboration
- v0.10.0 - Stable Release

**Recommendation**: Option 1 (single board) for better overview

---

## Implementation Steps

### Phase 1: Cleanup (Today)
1. ✅ Close completed milestones (v0.4.0, v0.5.0, v0.6.0, v0.7.0)
2. ✅ Create epic label
3. ✅ Tag epic issues (#286, #271, #257)

### Phase 2: Milestone Restructure (Today)
1. ✅ Create/update v0.6.0 milestone with target date March 1, 2026
2. ✅ Create/update v0.7.0 milestone with target date June 1, 2026
3. ✅ Update v0.8.0 milestone with target date September 1, 2026
4. ✅ Update v0.9.0 milestone with target date December 1, 2026
5. ✅ Update v0.10.0 milestone with target date March 1, 2027

### Phase 3: Issue Organization (Today)
1. ✅ Assign all File Registry issues (#286-296) to v0.6.0
2. ✅ Assign #285 to v0.6.0
3. ✅ Assign GitHub Projects issues (#257, #282-284) to v0.7.0
4. ✅ Keep session management (#271, #273-275, #279) in v0.8.0
5. ✅ Keep Gemini/multi-assistant (#212-214, #259, #262) in v0.9.0
6. ✅ Keep polish features (#255, #256, #258, #281) in v0.10.0

### Phase 4: Priority Update (Today)
1. ✅ Update all v0.6.0 issues with priority labels
2. ✅ Add "blocks: #XXX" comments for dependencies
3. ✅ Update epic issues with task lists

### Phase 5: Project Board (Today)
1. ✅ Create new unified project board
2. ✅ Add all open issues to board
3. ✅ Configure views (milestone, epic, priority)
4. ✅ Archive old project boards

### Phase 6: Documentation (Today)
1. ✅ Create ROADMAP.md in repo
2. ✅ Update README.md with roadmap link
3. ✅ Post announcement issue with roadmap

---

## Success Metrics

### Short-term (v0.6.0)
- File Registry fully implemented and tested
- No critical bugs in v0.6.0 release
- Documentation complete
- Release on time (March 1, 2026)

### Medium-term (v0.7-0.9)
- Each release delivers on schedule (±1 week)
- No major rewrites needed
- Community feedback incorporated
- Test coverage stays above 80%

### Long-term (v0.10.0)
- Production deployments successful
- API stable for 6+ months
- Active community contributions
- Clear upgrade path from pre-1.0

---

## Communication Plan

### Release Announcements
- GitHub Releases with changelog
- Update README.md with latest version
- Post to discussions/social media
- Email active users (if list exists)

### Breaking Changes
- Documented in CHANGELOG.md
- Migration guide provided
- Deprecated features warned for 1 release
- Clear upgrade instructions

### Feedback Channels
- GitHub Issues for bugs/features
- GitHub Discussions for questions
- Direct communication with early adopters

---

## Risks & Mitigation

### Risk 1: Scope Creep
**Mitigation**: Strict milestone scope, move non-critical to next release

### Risk 2: Delayed Dependencies
**Mitigation**: Parallel work where possible, fallback plans

### Risk 3: Breaking Changes
**Mitigation**: Semantic versioning, deprecation warnings, migration guides

### Risk 4: Quality vs Speed
**Mitigation**: Automated testing, code review, beta releases before stable

---

## Next Actions

1. **Execute cleanup** (Steps above)
2. **Start v0.6.0 work** (Task #287)
3. **Weekly milestone review** (Track progress)
4. **Monthly roadmap update** (Adjust based on velocity)

---

## Progress Summary (v0.5.19)

### Completed in v0.5.x Series
- ✅ **File Registry Core** (#287-289, #294): Data model, CLI, MCP tools, documentation
- ✅ **AI Assistant Integrations** (#298-300): Cursor, Aider, Copilot, Gemini, Goose, AGENTS.md
- ✅ **Plugin System** (v0.5.11-13): CLI commands, MCP tools, Mem0 integration
- 🔄 **v0.6.0 Status**: ~60% complete (core done, MCP interception & testing remain)

### Next Priorities
1. #290: MCP tool interception (CRITICAL for File Registry)
2. #296: End-to-end integration testing
3. #285: Fix pipx installation support (HIGH priority bug)
4. #291: Daemon integration for registry broadcasts

---

**Last Updated**: January 21, 2026
**Next Review**: February 1, 2026
