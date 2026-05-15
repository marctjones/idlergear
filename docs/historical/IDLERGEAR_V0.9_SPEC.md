# IdlerGear v0.9 Feature Specification

**Status:** Proposed
**Date:** 2026-05-14
**Supersedes:** UX_REDESIGN_PLAN.md, REDESIGN_IMPLEMENTATION_ORDER.md

## Framing

v0.9 retires the "comprehensive AI dev platform" positioning. The product is scoped to three jobs:

1. Make Claude Code fluent in the GitHub Issues workflow
2. Track long-running work across sessions
3. Protect work that lives outside git

Spec Kit handles the spec → plan → tasks → implement workflow for new features. Claude Code handles in-session tasks, memory, and execution. IdlerGear is the persistence and integration layer that connects them to GitHub Issues and project state.

v0.9 ships 9 features. v0.10 picks up deferred items (stale issue detection, configurable graph populators).

## Target end-state

| Surface | v0.9 count |
|---|---|
| MCP Tools | ~10 |
| MCP Resources | ~7 |
| MCP Prompts | ~5 |
| Hooks (scripts shipped) | ~4 |
| Subagents | 1-2 |
| LOC estimate | 3,000-4,500 |

Everything else from current IdlerGear is deleted, delegated to OSS, or moved to v0.10+.

## Cross-cutting concerns

**Data store.** `.idlergear/db.sqlite` (single file) for tasks, issue cache, job state, critical-file declarations, and graph metadata. Graph data continues in Kuzu at `.idlergear/graph.db`.

**GitHub API.** Use the existing `gh` CLI as the transport (no native HTTP client). Falls back to anonymous read-only if no auth. Mirror state into the local SQLite cache; sync on a schedule and on demand.

**MCP primitives.** Read-only data → Resources. Workflow templates → Prompts. State-modifying actions → Tools. Confirmation flows → Elicitation. AI-generated content (annotations, briefs, drafts) → Sampling. Project boundaries → Roots.

**Hooks.** Ship as scripts in `src/idlergear/hooks/`, installed to `.claude/hooks/` via `idlergear install`. Each hook is a thin shell wrapper that calls `idlergear <internal-command>`.

---

## Feature 1: Issue-aware session start + `#N` context injection

**Priority:** P0
**MCP primitives:** Resources, Hooks, Prompt

### Problem

Every llmfp session opens with "where did we leave off" followed by 15-20 tool calls to reconstruct state. Across the analyzed sessions, 242 unique issue numbers were referenced — but no context was injected when issues were mentioned. Claude rediscovers issue context from scratch each time.

### Solution

`SessionStart` hook injects a compact project state. A `UserPromptSubmit` hook detects `#N` references and pre-loads matching issue context as a Resource. The `/start` Prompt produces a ranked "what to work on" list.

### User stories

- As a developer, when I open Claude Code, I see the active branch, current focused issue, last 3 commits, and any active long-running jobs without asking.
- When I type `#277` in a prompt, Claude already has the issue title, body, labels, linked PRs, and assignee — no `gh issue view` call needed.
- When I ask "what should I work on?", I get a ranked shortlist with one-line context per item.

### API surface

- **Resource** `idlergear://project/context` — branch, focused issue, recent commits, active jobs (~500 tokens).
- **Resource** `idlergear://issue/{n}` — single issue with body, comments, labels, assignees.
- **Resource** `idlergear://issue/{n}/context` — issue + linked PRs + recent commits referencing it + related issues.
- **Resource** `idlergear://issues/recommended` — ranked open issues for current user.
- **Prompt** `/start` — invokes the recommended-issues flow.
- **Hook** `SessionStart` → emits context resource into the session.
- **Hook** `UserPromptSubmit` → scans for `#\d+`, fetches issues into cache, attaches as additional context.

### Behavior

- Ranking weights (configurable): `assignee=me` × 3, `recently-updated` × 2, priority labels × 2, `blocking-others` × 1.5, `milestone-near-due` × 1.5.
- Issue cache refreshes every 5 minutes or on focus change.
- Falls back gracefully if `gh` isn't installed or no GitHub remote — emits a minimal context with just branch and commits.

### Out of scope

- Multi-account GitHub (use the user's `gh auth` state).
- Linear/Jira/other trackers (v1.x).

### Dependencies

- `gh` CLI available and authenticated.
- Feature 2 (task ↔ issue sync) for "focused issue" detection.

### Acceptance criteria

- [ ] Opening a new session injects context without an explicit user request.
- [ ] `#N` in user prompt triggers context fetch within 1s (cached) / 3s (cold).
- [ ] `/start` returns ranked issues with ≤80 tokens per item.
- [ ] Works offline against cached issue state (read-only).

---

## Feature 2: Bidirectional task ↔ issue sync

**Priority:** P0
**MCP primitives:** Tools, Resources, Hooks

### Problem

172 commit messages reference issue numbers; zero IdlerGear tasks are linked to issues. Marc closes issues in commit messages (`Closes #277`) but tasks remain open, breaking traceability. Current IdlerGear has bidirectional GitHub Projects v2 sync but doesn't extend to plain Issues with checklist items.

### Solution

IdlerGear tasks become a local mirror of GitHub Issues plus session-scoped subtasks. Issue checklist items (`- [ ] foo` in issue body) become subtasks. Claude Code's `TaskCreate` items can be promoted to subtasks of the focused issue.

### User stories

- I can mark an issue checklist item complete in Claude Code; the box ticks on GitHub within 30s.
- I can create a session task with `TaskCreate`; on close it offers to promote to a persistent IdlerGear subtask of the focused issue.
- I can pull issue changes from GitHub on demand or every N minutes.

### API surface

- **Tool** `idlergear_capture(content, kind?, parent_issue?)` — unified capture; detects intent (bug/decision/tech-debt) and creates issue, task, or subtask.
- **Tool** `idlergear_sync(direction="push"|"pull"|"both", scope="issue"|"project"|"all")`.
- **Resource** `idlergear://tasks/open` — all open tasks with issue linkage.
- **Resource** `idlergear://sync/status` — last sync times, divergence count, conflicts.
- **Hook** `TaskCompleted` (Claude Code) → Elicitation: "Promote session task to subtask of #N?" if heuristic matches (>5 tool calls, >2 files touched).
- **Hook** `PostToolUse[Bash]` matching `git commit` → if commit message has `#N`, queue task update.

### Behavior

- Conflict resolution: GitHub wins on field-level conflicts (last-write-by-timestamp), surface conflict count in `idlergear://sync/status`.
- Sync runs every 5 minutes by default (configurable), and on demand via tool call.
- Promotion heuristic for session tasks → persistent: configurable thresholds; default `≥5 tool calls AND ≥2 files touched`.
- Subtask deletion in IdlerGear preserves issue checklist (don't silently mutate human-edited issue bodies); use a stable markup to round-trip.

### Out of scope

- Conflict-resolution UI beyond surfacing counts.
- Custom field mapping for non-Projects-v2 issues (use Projects sync for that).
- Issue creation by template inference (deferred to v0.10).

### Dependencies

- Feature 1 (session start) for "focused issue" notion.
- Existing Projects v2 sync code from current IdlerGear (port forward).

### Acceptance criteria

- [ ] Issue checklist toggle propagates IG → GitHub in ≤30s.
- [ ] Commit with `Closes #N` triggers task close within 30s of push.
- [ ] Two-way sync survives 100 mixed mutations on both sides without data loss.
- [ ] Subtask round-trip preserves issue body formatting.

---

## Feature 3: Long-running job lifecycle

**Priority:** P0
**MCP primitives:** Tools, Resources, Hooks

### Problem

One llmfp session had 2072 Monitor calls and 364 ScheduleWakeup calls — Claude babysitting batch fingerprint jobs that run for hours. Sessions end with `.partial.tmp` checkpoints on disk and no record of what job was running. Next session has no idea a job is in flight.

### Solution

When Claude Code's `Monitor` watches a process, IdlerGear shadow-records the job: command, PID, started-at, output path, linked issue/task. On session end, persists active jobs. On session start, surfaces them and offers resume.

### User stories

- I start `llmfp batch fingerprint ...` via `run_in_background`; IdlerGear automatically tracks it as a job linked to my focused issue.
- My session ends with the job still running. Next session opens with: "Job `batch-qwen-30b` is 47% complete, 2h ETA. Resume monitoring?"
- I try to delete a checkpoint file for an active job; Elicitation: "This is a checkpoint for active job X. Continue?"

### API surface

- **Tool** `idlergear_job_list(state="active"|"completed"|"all")`.
- **Tool** `idlergear_job_show(id)`.
- **Tool** `idlergear_job_attach(id)` — re-attach a Monitor stream to a known job.
- **Resource** `idlergear://jobs/active` — currently-running jobs with progress hints.
- **Resource** `idlergear://job/{id}` — full job state, output tail, linked task/issue.
- **Hook** `PostToolUse[Bash]` matching `run_in_background:true` → register job with timestamp + linked issue.
- **Hook** `Stop` → snapshot active jobs to SQLite.
- **Hook** `SessionStart` → check for active jobs, surface in context resource.
- **Hook** `PreToolUse[Edit|Write|Bash]` → if target path is a known checkpoint for an active job, Elicit.

### Behavior

- Job detection heuristic: any backgrounded process running >60s. Configurable threshold.
- Progress parsing is pluggable: regex patterns in `.idlergear/config.toml` per command pattern (`llmfp batch.*` → `(\d+)% complete`).
- Job state persists in SQLite; output paths are referenced, not copied.
- Job-checkpoint mapping is declared explicitly or inferred from output path prefix.

### Out of scope

- Process supervision / restart (use systemd/overmind).
- Distributed job tracking across machines.
- GPU/resource monitoring (out of scope; user can pipe metrics if needed).

### Dependencies

- Claude Code's `Bash run_in_background` + `Monitor` (already native).
- Feature 4 (critical files) for the checkpoint-guardrail behavior.

### Acceptance criteria

- [ ] A backgrounded job >60s gets registered automatically with no explicit tool call.
- [ ] Session-end snapshot persists job state to SQLite.
- [ ] Next session start surfaces active jobs in the context resource.
- [ ] Attempting `rm` on a known checkpoint triggers Elicitation.

---

## Feature 4: Critical file declarations + guardrails

**Priority:** P0
**MCP primitives:** Tools, Resources, Hooks

### Problem

llmfp has explicit CLAUDE.md warnings against deleting `.partial` fingerprints because the canonical store is a HuggingFace dataset, not git. Most real projects have similar non-git critical state (databases, configs, generated artifacts, downloaded models). IdlerGear has no concept of "this file is dangerous to lose."

### Solution

Projects declare critical files in `.idlergear/config.toml`. Each declaration has a path glob, an optional canonical source (URL/command), and an optional divergence-check command. Pre-operation hooks block destructive operations unless explicitly confirmed.

### User stories

- I declare `fingerprints/*.json` as critical with canonical source `hf:marcjon/llmfp-fingerprints`. Attempts to `rm` or overwrite trigger Elicitation.
- I run `idlergear doctor`; it shows which critical files have diverged from canonical source.
- Before editing a critical file, IdlerGear creates a `.idlergear/backups/{path}.{timestamp}` snapshot.

### API surface

- **Tool** `idlergear_file_critical(action="declare"|"undeclare"|"check", path, canonical?, check_cmd?)`.
- **Tool** `idlergear_doctor(scope="critical"|"all")` — surfaces divergence and missing backups.
- **Resource** `idlergear://files/critical` — list of declarations with status.
- **Resource** `idlergear://files/critical/{path}/status` — current state vs canonical.
- **Hook** `PreToolUse[Edit|Write|Bash]` → if path matches critical glob and operation is destructive, Elicit.

### Behavior

- Config format:
  ```toml
  [[critical_files]]
  path = "fingerprints/*.json"
  canonical = "hf:marcjon/llmfp-fingerprints"
  check_cmd = "python scripts/hf_library_sync.py --check"
  auto_backup = true
  ```
- Destructive ops detected: `rm`, `mv` (when overwriting), `Write` (when target exists), `Edit` (default off — too noisy).
- Backups capped at 10 versions per path; oldest pruned.
- `gh:`, `hf:`, `s3://`, `https://` canonical-source prefixes supported in v0.9; pluggable for v0.10.

### Out of scope

- Real-time sync to canonical source (one-way protection only).
- Encryption / secrets management (use `.env` and gitignore).
- Multi-machine consistency (per-checkout state only).

### Dependencies

- None internal. External: tools for canonical source checks (`gh`, `huggingface-cli`, `aws`).

### Acceptance criteria

- [ ] `rm` on a declared critical file triggers Elicitation with backup offer.
- [ ] `idlergear doctor` reports divergence count for each declaration.
- [ ] Backups created in `.idlergear/backups/` before destructive ops succeed.
- [ ] Zero performance impact when no critical files are declared.

---

## Feature 5: Pre-work brief (via Sampling)

**Priority:** P1
**MCP primitives:** Tools, Prompt, Sampling

### Problem

Sessions spend the first ~10 tool calls reconstructing what an issue is about. Claude often dives into code before confirming its interpretation of the issue, and Marc has to redirect.

### Solution

When focusing an issue, IdlerGear uses MCP Sampling to ask the model to produce a 1-paragraph "here's what I think this issue is and how I'd approach it" *before* writing code. User confirms or redirects.

### User stories

- I type `/work-on 277`. Before any code is read, Claude responds: "Issue #277 asks for X. I think the right approach is Y. Files likely involved: A, B. Tests to update: C. Should I proceed?"

### API surface

- **Prompt** `/work-on {issue_number}` — focuses an issue and triggers the brief.
- **Tool** `idlergear_focus(issue_number)` — non-prompt entry point.
- Internally uses **MCP Sampling** to generate the brief from the issue resource + graph query.

### Behavior

- Brief includes: 1-sentence issue interpretation, 2-3 sentence approach, predicted-files list (from graph), predicted-tests list (from graph), open questions if the spec is ambiguous.
- If Sampling is unavailable (older client), falls back to a templated brief without LLM generation.
- Brief is cached per (issue, last-modified-timestamp); re-generated only on issue update.

### Out of scope

- Auto-execution of the proposed approach (user must confirm).
- Multi-issue planning (use Spec Kit `/speckit.plan`).

### Dependencies

- Feature 1 (issue context resource).
- Feature 7 (graph queries for predicted-files/tests).

### Acceptance criteria

- [ ] Brief generated within 5s of `/work-on`.
- [ ] Brief includes file and test predictions when graph is populated.
- [ ] Brief is cached and invalidated correctly on issue updates.

---

## Feature 6: Semantic search across closed issues

**Priority:** P1
**MCP primitives:** Tools, Resources

### Problem

Marc references 242 unique issue numbers (open + closed) in a single session. He's using issues as a queryable knowledge base: "what did we decide about X" → search closed issues. Current `gh issue list` is text-based, not semantic.

### Solution

Local SQLite full-text + lightweight semantic index over issue bodies and comments. Closed issues are first-class search targets.

### User stories

- "Has anyone hit this before?" → IdlerGear returns 3 closed issues with similar symptoms.
- Before working on an issue, I can see related closed issues that touched the same files.

### API surface

- **Tool** `idlergear_search(query, scope="issues"|"all", include_closed=true, limit=10)`.
- **Resource** `idlergear://issues/related/{n}` — issues related to issue N by text + file overlap.

### Behavior

- Index built incrementally on issue sync; rebuilt on `idlergear doctor --reindex`.
- Ranking: FTS5 BM25 score + graph-overlap bonus (shared files in commits) + recency penalty (older issues weighted slightly lower).
- Semantic layer is optional and opt-in via `[search] semantic = true` in config — uses sqlite-vss + a small embedding model to avoid the OOM issues from the prior vector path.

### Out of scope

- Cross-repo search (v1.x).
- Semantic search across code (out of scope — LSP + grep suffice).

### Dependencies

- Issue cache from Feature 2.

### Acceptance criteria

- [ ] FTS5 search returns results in <100ms for a 5k-issue repo.
- [ ] Related-issues surfaces ≥80% of human-identified duplicates in a small evaluation set.
- [ ] Semantic mode is opt-in and doesn't load embedding models when disabled.

---

## Feature 7: "Similar fixes elsewhere" graph query

**Priority:** P1
**MCP primitives:** Tools, Resources

### Problem

llmfp sessions show test-failure → fix → similar failure elsewhere (265 pytest runs in one session). When Claude fixes a bug pattern in one file, the same pattern often exists elsewhere — and is missed.

### Solution

Pre-close graph query: given a recent commit's diff (or set of edited files + symbols), find files with structurally similar code that wasn't touched. Surface as Resource at close-issue time.

### User stories

- About to close issue #277. IdlerGear: "You fixed a null-check bug in `auth.py:42`. The same pattern exists in `admin.py:88` and `api/login.py:103`. Apply fix there too?"

### API surface

- **Tool** `idlergear_graph_query(target="similar_patterns", source_file, source_lines)` — returns ranked similar locations.
- **Resource** `idlergear://issue/{n}/close_checklist` — quality gates including similar-fixes results.
- Surfaced automatically when Feature 2's task-close flow runs.

### Behavior

- Similarity uses tree-sitter AST comparison (not pure text). The graph stores normalized AST signatures per function/method node.
- Threshold: 80% AST similarity OR exact-match identifier patterns near the edit site.
- Results capped at 5 matches; ranked by similarity × recency-of-touch.
- False-positive tolerance: prefer high precision; user must confirm each suggestion.

### Out of scope

- Cross-repo pattern detection (v1.x).
- Automatic fix application (always Elicit; user confirms).

### Dependencies

- Knowledge graph populated with AST signatures (extension of existing code populator).

### Acceptance criteria

- [ ] Query returns results in <500ms for a graph with 10k symbols.
- [ ] On a curated 10-bug benchmark, surfaces ≥70% of human-confirmed similar locations.
- [ ] Zero false positives that survive user review on a 10-bug eval set.

---

## Feature 8: `/handoff` and `/standup` prompts

**Priority:** P1
**MCP primitives:** Prompts, Sampling, Tools

### Problem

Sessions end without explicit handoff state. Marc starts the next session asking "where did we leave off." Weekly status reporting is manual.

### Solution

Two Prompts produce structured artifacts at the right moments. `/handoff` produces an issue-comment-ready summary for the current focused issue. `/standup` produces a one-paragraph weekly digest.

### User stories

- End of session: `/handoff`. Output: "Worked on #277 this session. Implemented X. Open question: Y. Next step: Z. Files touched: A, B." User reviews, posts as comment on the issue.
- Monday morning: `/standup`. Output: "Last week: closed 4 issues (#A, #B, #C, #D), opened 2 (#E, #F), in progress on #G. Blocked on H."

### API surface

- **Prompt** `/handoff [issue_number?]` — produces handoff for current or specified issue. Uses Sampling.
- **Prompt** `/standup [days=7]` — produces weekly digest. Templated, no Sampling.
- **Tool** `idlergear_standup(days=7)` — non-prompt entry point.

### Behavior

- `/handoff` aggregates: commits this session linked to issue, files touched, session-task list, uncommitted changes, time spent (from session start).
- Output is markdown formatted as a GitHub comment. User posts via `gh issue comment` (suggested but not auto-run).
- `/standup` aggregates from sync cache; no LLM call needed.

### Out of scope

- Auto-posting to issues (always user-mediated).
- Slack/email digest output (could be a v1.x add-on).

### Dependencies

- Feature 2 for task/commit/issue linkage.

### Acceptance criteria

- [ ] `/handoff` produces a comment-ready summary in <3s.
- [ ] `/standup` produces an accurate week-over-week digest from local cache.
- [ ] Both work offline.

---

## Feature 9: Auto-link commits → issues on push

**Priority:** P1
**MCP primitives:** Hooks

### Problem

172 commits in llmfp reference issue numbers, but the issues aren't always updated. Marc has to manually `gh issue comment` or rely on GitHub's keyword detection (which only fires on default branch).

### Solution

`PostToolUse[Bash]` hook detects git commits and pushes. For each commit referencing an issue, post a structured status comment to the issue (or update an existing IdlerGear-managed rolling comment).

### User stories

- I commit `fix(auth): null check #277`. After pushing, the issue gets a comment: "Linked commit `abc123` in branch `fix/auth-null`. Status: in progress."
- The same issue gets one rolling IdlerGear-managed comment (edited in place), not 20 separate comments.

### API surface

- **Hook** `PostToolUse[Bash]` matching `git push` → parse pushed commits, extract issue refs, update rolling comment.
- **Tool** `idlergear_link_commit(sha, issue_number)` — manual linkage.
- Configurable in `.idlergear/config.toml`:
  ```toml
  [commits]
  auto_comment = true              # default false in v0.9
  comment_style = "rolling"|"per_commit"
  ```

### Behavior

- Rolling comment is identified by a hidden marker `<!-- idlergear:rolling -->`. Edited via GitHub API.
- Default off in v0.9 to avoid surprising users; opt-in via config.
- Detects refs via `(closes|fixes|refs|#)\s*#(\d+)` patterns.

### Out of scope

- Cross-repo references (`org/repo#N`).
- PR creation (handled by user's existing flow or Spec Kit `/speckit.implement`).

### Dependencies

- Feature 2 (sync infrastructure).

### Acceptance criteria

- [ ] Pushing a commit with `#N` updates the issue within 30s when enabled.
- [ ] Rolling comment is edited in place, not duplicated.
- [ ] Feature is off by default; opt-in via config.

---

## Cross-feature dependency graph

```
F1 (session start) ─┬─> F5 (pre-work brief)
                    └─> F8 (handoff/standup)

F2 (task↔issue sync) ─┬─> F1
                      ├─> F8
                      ├─> F9 (auto-link commits)
                      └─> F6 (search)

F3 (job lifecycle) ──> F4 (critical files)

F4 (critical files) ── standalone

F7 (similar fixes) ──> graph populator (preexisting)
```

**Build order:** F4 → F3 → F2 → F1 → F6 → F7 → F5 → F8 → F9.

## Deferred to v0.10

- **Stale issue detection.** Read-only Resource listing issues with no activity in N days. Low cost but not critical for v0.9.
- **Configurable graph populators.** Plugin API for project-specific structured data (YAML schemas, ML configs). Strong evidence from llmfp but generalizes poorly without a real plugin design — defer until 2-3 projects request it.
- **Triage automation.** Auto-label suggestion, priority inference. Surface in `/triage` prompt.
- **Multi-repo workspace.** Cross-repo issue graph. Defer until a user has multiple linked repos.
- **PR drafting from issue context.** Compose with v0.9 sync; not blocking.

## What's deleted in v0.9

Tools removed from current IdlerGear:

- All `idlergear_fs_*` (11) — Claude Code has Read/Edit/Write/Glob/Grep.
- Most `idlergear_git_*` (16 of 18) — keep only `git_sync_tasks`, `git_commit_task` (or fold into F9).
- All `idlergear_pm_*` (11) — replaced by F3.
- All `idlergear_tmux_*` (5) — use `tmux` via Bash.
- All `idlergear_container_*` (6) — use `docker`/`podman` via Bash.
- All `idlergear_ai_report_*` (4) — parse transcript or use OTel.
- `idlergear_code_search`, `idlergear_find_similar_code` (2) — LSP + grep.
- `idlergear_get_script_template`, `_list_script_templates`, `_generate_dev_script` (3) — Skills.
- Bulk `idlergear_test_*` (8) — use `pytest` via Bash.
- Bulk `idlergear_docs_*` (4) — delegate to mkdocs/sphinx.
- Bulk `idlergear_session_*` (6) — replaced by hooks.
- All daemon multi-agent (8) — drop the cross-AI-tool framing.
- `idlergear_plan_*`, `idlergear_vision_*`, `idlergear_explore_*` — delegate to Spec Kit.
- `idlergear_otel_*` — keep one query tool, drop the rest.

Approximate count: **~120 tools removed**, ~230 → ~10.

## Implementation plan

| Week | Work |
|---|---|
| 1 | F4 (critical files) — smallest, standalone, builds confidence. |
| 2 | F3 (job lifecycle) — depends on F4 for guardrails. |
| 3-4 | F2 (task↔issue sync) — core integration work. |
| 5 | F1 (session start) — depends on F2. |
| 6 | F6 (search) + F9 (commit linking) — both small, parallel. |
| 7 | F7 (similar fixes) — graph populator extension. |
| 8 | F5 (pre-work brief) + F8 (handoff/standup) — prompts and Sampling. |
| 9 | Tool deletions, deprecation shims, migration guide. |

**v0.9 target: ~9 weeks.**

## Acceptance for v0.9 release

- [ ] All 9 features ship with their per-feature acceptance criteria met.
- [ ] Tool count ≤15 (10 v0.9 features + 5 supporting).
- [ ] Resource count ≤8.
- [ ] Prompt count ≤6.
- [ ] LOC under 5,000 including tests.
- [ ] Migration guide for users on current IdlerGear.
- [ ] Documentation: README, single CLAUDE.md section <100 lines, one architecture doc.
- [ ] Dogfooding: every v0.9 feature used in the development of v0.9 itself for 1 week before tagging.

## Open questions

1. **Spec Kit detection:** if `.specify/` exists, should IdlerGear's `/start` defer to `/speckit.constitution` summary? Or stay separate? Recommend: surface both, don't merge.
2. **Issue cache invalidation:** webhook vs polling vs both? Polling is simpler; webhook requires server. Recommend: polling-only in v0.9; webhook as v1.0 if it becomes a bottleneck.
3. **Sampling availability:** F5 and F8 use Sampling. What's the fallback on clients without it? Recommend: templated outputs for both, with Sampling as enhancement.
4. **Backward compatibility:** how long do deprecated tools keep working? Recommend: emit warnings in v0.9; remove in v1.0.

## What this spec does NOT cover

- Detailed MCP server implementation (separate technical doc).
- GitHub API rate limits and pagination (engineering detail).
- Database schema (separate doc when implementing F2/F3).
- Test strategy (separate doc).
- Migration tooling from current IdlerGear (Week 9 deliverable).
