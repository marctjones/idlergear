# Planning Guide: Plans vs Milestones vs Projects vs Epics

**Understanding IdlerGear's five planning tools and when to use each one.**

---

## Quick Decision Matrix

| I want to... | Use This | Command | Where It Lives |
|--------------|----------|---------|----------------|
| Organize work for a release version | **Milestone** | `gh api` or future `idlergear milestone` | GitHub Milestones |
| Track strategic multi-month initiative | **Plan** | `idlergear plan` | `.idlergear/plans/` + GitHub Projects |
| Visualize work on Kanban board | **Project** | `gh project` or future sync | GitHub Projects v2 |
| Group related tasks as an epic | **Meta-Issue** | `gh issue create` with checklist | GitHub Issue |
| Track a single piece of work | **Task** | `idlergear task` | `.idlergear/tasks/` + GitHub Issues |
| Group related tasks (large feature) | **Epic** | `gh issue create --label epic` | GitHub Issue with task list |

---

## The Five Planning Tools

### 1. Milestones - Release Versions 🎯

**Purpose:** Group issues by release version or time-boxed goal

**Best For:**
- Release planning (v0.4.0, v0.5.0)
- Sprint/iteration boundaries
- Time-boxed deliverables

**Characteristics:**
- GitHub-native feature
- Shows completion percentage automatically
- Filters issues by version
- Due dates supported
- Team-visible on GitHub

**Current Commands:**
```bash
# Via gh CLI (GitHub native)
gh api repos/owner/repo/milestones -f title="v0.4.0" -f description="..."
gh issue edit 123 --milestone "v0.4.0"
gh api repos/owner/repo/milestones --jq '.[] | "\(.title): \(.open_issues)/\(.closed_issues + .open_issues)"'

# Planned IdlerGear wrappers (Phase 2 of #260)
idlergear milestone create "v0.4.0" --description "Test & Run Awareness"
idlergear milestone list
idlergear milestone show v0.4.0
idlergear task create "Feature X" --milestone v0.4.0
idlergear task list --milestone v0.4.0
```

**Example Workflow:**
```bash
# Planning v0.4.0 release
gh api repos/marctjones/idlergear/milestones -f title="v0.4.0" -f description="Test & Run Awareness"

# Assign issues to milestone
gh issue edit 163 --milestone "v0.4.0"
gh issue edit 164 --milestone "v0.4.0"

# Check progress
gh api repos/marctjones/idlergear/milestones --jq '.[] | select(.title == "v0.4.0") | "Progress: \(.closed_issues)/\(.open_issues + .closed_issues) complete"'
```

**When to Use:**
- ✅ Organizing issues for a specific release version
- ✅ Tracking progress toward a time-boxed goal
- ✅ Filtering issues by version in GitHub UI
- ✅ Team needs to see release progress

**When NOT to Use:**
- ❌ Strategic initiatives spanning multiple releases (use **Plan**)
- ❌ Visual Kanban workflow (use **Project**)
- ❌ Grouping related features as epic (use **Meta-Issue**)

---

### 2. Plans - Strategic Initiatives 📋

**Purpose:** Multi-month strategic initiatives that may span releases

**Best For:**
- Strategic goals ("Improve test coverage")
- Cross-cutting initiatives ("Refactor authentication")
- Multi-release themes
- Team alignment on direction

**Characteristics:**
- IdlerGear-native feature
- Stored locally in `.idlergear/plans/*.md`
- Can sync to GitHub Projects v2 (optional)
- Supports states: active, completed
- Markdown body for documentation

**Current Commands:**
```bash
# Create plan
idlergear plan create "test-coverage" --title "Improve Test Coverage"

# Switch active plan
idlergear plan switch test-coverage

# View plan
idlergear plan show test-coverage

# List all plans
idlergear plan list

# Mark complete
idlergear plan complete test-coverage

# Edit plan
idlergear plan edit test-coverage --body "Updated strategy..."
```

**Example Plan File** (`.idlergear/plans/test-coverage.md`):
```markdown
---
title: Improve Test Coverage
state: active
created_at: 2026-01-17T12:00:00Z
github_project: 14  # Optional: link to GitHub Project #14
---

# Improve Test Coverage

## Goal
Achieve 85%+ test coverage across all modules by Q2 2026.

## Strategy
1. Add test framework integration (v0.4.0)
2. Track coverage in CI/CD
3. Enforce minimum coverage in hooks
4. Backfill tests for legacy code

## Milestones
- v0.4.0: Test framework integration
- v0.5.0: Coverage tracking
- v0.6.0: Enforcement

## Progress
- [x] Basic test detection (#142)
- [ ] Task integration (#144)
- [ ] Hook enforcement (#145)
```

**When to Use:**
- ✅ Strategic multi-month initiatives
- ✅ Themes spanning multiple releases
- ✅ High-level direction documentation
- ✅ Team alignment on goals

**When NOT to Use:**
- ❌ Single release version tracking (use **Milestone**)
- ❌ Daily task management (use **Task**)
- ❌ Immediate action items (use **Task**)
- ❌ Large feature grouping (use **Epic**)

---

### 3. Projects - Visual Kanban Boards 📊

**Purpose:** Visual workflow management with columns

**Best For:**
- Kanban workflow (Backlog → In Progress → Done)
- Visual team collaboration
- Tracking work across columns
- Sprint boards

**Characteristics:**
- GitHub Projects v2 (cloud-hosted)
- Kanban columns (customizable)
- Drag-and-drop interface
- Custom fields (priority, effort, status)
- Roadmap views, table views

**Current Commands:**
```bash
# Via gh CLI (GitHub native)
gh project create --owner marctjones --title "v0.4.0 Roadmap"
gh project list --owner marctjones
gh project item-add 17 --owner marctjones --url "https://github.com/owner/repo/issues/123"

# Planned IdlerGear integration (#257 - v0.7.0)
idlergear project create "v0.4.0 Roadmap" --columns "Backlog,In Progress,Review,Done"
idlergear project sync  # Bidirectional sync with GitHub
idlergear project board  # ASCII Kanban view in CLI
idlergear project add-task 123
```

**Example Workflow:**
```bash
# Create project for v0.4.0 release
gh project create --owner marctjones --title "v0.4.0 - Test & Run Awareness"

# Add issues to project
gh project item-add 17 --owner marctjones --url "https://github.com/marctjones/idlergear/issues/163"
gh project item-add 17 --owner marctjones --url "https://github.com/marctjones/idlergear/issues/164"

# Team moves cards across columns in GitHub UI
# (Backlog → In Progress → Review → Done)
```

**When to Use:**
- ✅ Visual workflow management
- ✅ Team collaboration on shared board
- ✅ Sprint planning with columns
- ✅ Tracking work-in-progress limits

**When NOT to Use:**
- ❌ CLI-only workflow (though CLI view planned in #257)
- ❌ Offline work (requires GitHub)
- ❌ Simple task lists (use **Task** + **Milestone**)
- ❌ Tracking epics (use **Epic** issue)

---

### 4. Epics - Feature Decomposition 🌳

**Purpose:** Group related tasks as a parent-child hierarchy

**Best For:**
- Large features decomposed into tasks (1-3 weeks of work)
- Feature roadmaps within a milestone
- Tracking related work as a unit
- Breaking down complex features

**Characteristics:**
- GitHub issue with `epic` label
- Task list in body (markdown checkboxes)
- Title prefixed with "Epic:" by convention
- Manual progress tracking (for now)
- Parent-child relationship via task list references

**Current Commands:**
```bash
# Create manually (no special commands yet)
gh issue create --title "Epic: Multi-Assistant Support" --label epic --body "$(cat <<'EOF'
## Goal
Universal AI assistant support across Claude, Gemini, Goose, Aider, Cursor.

## Tasks
- [ ] #262 - Survey AI assistant tools
- [ ] #259 - Implement AGENTS.md support
- [ ] #213 - Enhanced Gemini context
- [ ] #212 - Gemini slash commands

## Acceptance Criteria
- Works with 5+ AI assistants
- Single AGENTS.md generates tool-specific files
- 90% token savings vs manual context
EOF
)"

# Planned IdlerGear helpers (Phase 4 of #260)
idlergear epic create "Multi-Assistant Support" --tasks "#262,#259,#213,#212"
idlergear epic show 264
idlergear epic progress 264  # Shows completion percentage
```

**Example Epic:**

**Issue #264: Epic: Token-efficient structured information access system**

```markdown
## Overview
Provide token-efficient access to structured information (API docs, priorities, references).

## Tasks
- [ ] #267 - NetworkX POC
- [ ] Create document parser (Phase 1)
- [ ] Implement info command (Phase 2)
- [ ] Add MCP tools (Phase 3)
- [ ] Graph integration if POC succeeds (Phase 4)

## Acceptance Criteria
- 70-90% token savings for queries
- Query priorities, API docs, references
- Cacheable, mode-based queries
```

**When to Use:**
- ✅ Large features with multiple sub-tasks
- ✅ Epic/story/task hierarchy
- ✅ Feature decomposition
- ✅ Tracking related work

**When NOT to Use:**
- ❌ Simple single tasks (use **Task**)
- ❌ Release version grouping (use **Milestone**)
- ❌ Strategic initiatives (use **Plan**)

---

## How They Work Together

### Example: v0.4.0 Release Planning

```
Plan: "Test Coverage Initiative"
  └─ Strategic goal across v0.4, v0.5, v0.6

      Milestone: "v0.4.0 - Test & Run Awareness"
        └─ Release version grouping

            Project: "v0.4.0 Roadmap"
              └─ Kanban board for v0.4.0 work

                  Epic #264: "Test Framework Integration"
                    ├─ Task #163 - Add --needs-tests flag
                    ├─ Task #164 - Track test file changes
                    ├─ Task #165 - Warn on close without tests
                    └─ Task #166 - Test staleness warning

                  Epic #270: "Run Management"
                    ├─ Task #154 - Add run history
                    └─ Task #141 - Run documentation

                  Task #162 - Detect uncovered files (standalone)
```

**Workflow:**
1. **Strategic planning** → Create Plan ("Test Coverage Initiative")
2. **Release planning** → Create Milestone ("v0.4.0")
3. **Visual tracking** → Create Project ("v0.4.0 Roadmap")
4. **Feature decomposition** → Create Epic (#264) for large features
5. **Implementation** → Create Tasks (#163-166) assigned to milestone, added to project
6. **Execution** → Move tasks across project columns as work progresses
7. **Completion** → Close milestone when all tasks done, update plan progress

---

## Current State vs Future State

### Current Implementation (v0.3.72)

| Tool | IdlerGear Support | GitHub Support | Status |
|------|-------------------|----------------|--------|
| **Tasks** | ✅ Full CLI + MCP | ✅ GitHub Issues backend | Complete |
| **Plans** | ✅ CLI commands | 🔨 Partial (manual linking) | Implemented, needs sync |
| **Milestones** | ❌ None | ✅ GitHub native | CLI wrapper planned (#260) |
| **Projects** | ❌ None | ✅ GitHub native | Integration planned (#257) |
| **Epics** | ❌ None | 🔨 Manual (label + markdown) | Helper commands planned (#260) |

### Future Implementation

**v0.5.0 - Planning & Foundation (#260 Phase 1-2):**
- ✅ Documentation (this file!)
- ✅ Milestone CLI wrappers
- ✅ Show milestone in task output
- ✅ Filter tasks by milestone

**v0.7.0 - Multi-Assistant & Collaboration (#257):**
- ✅ GitHub Projects v2 sync
- ✅ CLI Kanban view
- ✅ Bidirectional sync
- ✅ Plans auto-sync to projects

**v0.8.0 - Developer Experience & Polish (#260 Phase 4):**
- ✅ Epic CLI commands
- ✅ Parent-child task relationships
- ✅ Progress tracking for epics

---

## Workflows and Best Practices

### Workflow 1: Small Solo Project

**Recommended:** Tasks + Milestones

```bash
# Create milestone for v1.0
gh api repos/owner/repo/milestones -f title="v1.0" -f description="First release"

# Create tasks assigned to milestone
idlergear task create "Feature X" --label feature
gh issue edit $(idlergear task show 1 --format json | jq -r .github_issue) --milestone "v1.0"

# Track progress
gh api repos/owner/repo/milestones --jq '.[] | "\(.title): \(.closed_issues)/\(.open_issues + .closed_issues)"'
```

**Skip:** Plans (overkill), Projects (visual overhead), Epics (too few tasks)

### Workflow 2: Medium Team Project

**Recommended:** Tasks + Milestones + Projects

```bash
# Create milestone
gh api repos/owner/repo/milestones -f title="v2.0"

# Create project
gh project create --owner marctjones --title "v2.0 Sprint"

# Add tasks to both
idlergear task create "Feature Y" --label feature
gh issue edit ISSUE_NUM --milestone "v2.0"
gh project item-add PROJECT_NUM --url ISSUE_URL

# Team uses GitHub UI for Kanban workflow
```

**Skip:** Plans (unless multi-release), Meta-Issues (unless complex features)

### Workflow 3: Large Enterprise Project

**Recommended:** All tools

```bash
# Create strategic plan
idlergear plan create auth-refactor --title "Authentication Refactor"

# Create milestones for each release
gh api repos/owner/repo/milestones -f title="v3.0 - Auth Phase 1"
gh api repos/owner/repo/milestones -f title="v3.1 - Auth Phase 2"

# Create project linked to plan
gh project create --title "Auth Refactor Roadmap"
idlergear plan edit auth-refactor --github-project PROJECT_NUM

# Create epics for features
idlergear epic create "OAuth Integration" --tasks "#100,#101,#102"
idlergear epic create "JWT Migration" --tasks "#110,#111,#112"

# Assign tasks to milestones
gh issue edit 100 --milestone "v3.0 - Auth Phase 1"

# Track at all levels
idlergear plan show auth-refactor  # Strategic view
idlergear milestone show v3.0       # Release view
idlergear project board             # Kanban view
idlergear epic progress 150         # Feature view
```

---

## Migration Guide

### From Manual GitHub Management → IdlerGear

**Current manual workflow:**
1. Create milestone via `gh api`
2. Create issues via `gh issue create`
3. Assign to milestone via `gh issue edit`
4. Create project via `gh project create`
5. Add issues to project via `gh project item-add`
6. Manually track progress

**Improved workflow (v0.5.0+):**
1. Create milestone via `idlergear milestone create` (wrapper)
2. Create tasks via `idlergear task create --milestone` (one command)
3. Project sync automatic (v0.7.0)
4. Progress tracked automatically

**Future workflow (v0.7.0+):**
```bash
# One command creates everything
idlergear milestone create v0.4.0 \
    --description "Test & Run Awareness" \
    --project "v0.4.0 Roadmap" \
    --columns "Backlog,In Progress,Done"

# Tasks auto-assigned and synced
idlergear task create "Feature X" --milestone v0.4.0  # Auto-added to project

# Progress visible everywhere
idlergear milestone show v0.4.0    # Shows completion %
idlergear project board            # Shows Kanban
```

---

## FAQs

### Q: Should I use a Plan or a Milestone for my release?

**Use Milestone** if:
- Single release version (v0.4.0, v1.0)
- Time-boxed (ship in 2-3 weeks)
- All work fits in one GitHub milestone

**Use Plan** if:
- Multi-release initiative (test coverage across v0.4, v0.5, v0.6)
- Strategic goal with evolving scope
- Spans months with multiple milestones

**Use Both** if:
- Plan = multi-release strategy
- Milestones = individual release versions within the plan

### Q: Do I need a GitHub Project for every Milestone?

**Not required**, but recommended for:
- Team collaboration (visual boards)
- Complex milestones with 10+ issues
- Multiple contributors
- Work-in-progress limits

**Skip if:**
- Solo developer
- Simple milestone (< 5 issues)
- CLI-only workflow

### Q: When should I create an Epic?

**Create when:**
- Feature has 3+ related sub-tasks
- Need to track feature-level progress
- Want parent-child hierarchy
- Complex acceptance criteria
- Large feature within a milestone (1-3 weeks of work)

**Skip when:**
- Single task implementation
- Simple features (1-2 tasks)
- Already using milestones for grouping
- Strategic multi-month initiatives (use **Plan** instead)

### Q: Can I link a Plan to a Milestone?

**Not currently**, but planned improvements:

```bash
# Future (v0.7.0+)
idlergear plan create test-coverage \
    --milestones "v0.4.0,v0.5.0,v0.6.0" \
    --github-project "Test Coverage Roadmap"

idlergear plan show test-coverage
# Shows:
# Plan: Test Coverage Initiative
# Milestones: v0.4.0 (50% complete), v0.5.0 (0% complete), v0.6.0 (0% complete)
# Overall: 16% complete
```

### Q: What if I work offline?

**Offline support:**
- ✅ **Tasks** - Full offline support (local backend)
- ✅ **Plans** - Full offline support
- ❌ **Milestones** - Requires GitHub
- ❌ **Projects** - Requires GitHub
- ❌ **Meta-Issues** - Requires GitHub

**Recommendation:** Use Tasks + Plans for offline work, sync to GitHub when online.

---

## Related Issues

- **#260** - This issue (clarify planning concepts)
- **#257** - GitHub Projects v2 Integration (v0.7.0)
- **#263** - Priorities Registry (v0.5.0)
- **#265** - GitHub GraphQL API (v0.5.0, enables #257)

---

## Next Steps

1. **Read this guide** to understand the distinctions
2. **Choose the right tools** for your project size
3. **Try the workflows** in the examples section
4. **Give feedback** on what's confusing or missing
5. **Watch for enhancements** in v0.5.0 (milestones), v0.7.0 (projects), v0.8.0 (epics)

---

**Last Updated:** 2026-01-18 (v0.3.72)
**Related Documentation:** [ROADMAP.md](ROADMAP.md), [DESIGN.md](../DESIGN.md)
