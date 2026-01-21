---
id: 23
title: Smart commit timing detection and automated documentation sync checks
state: open
created: '2026-01-03T06:11:16.698010Z'
labels:
- enhancement
- 'effort: medium'
- 'component: watch'
- core-v1
priority: high
---
## Summary

Monitor development activity and intelligently suggest when to commit to git. On commit, automatically check if README, wiki, and issues need updates to stay synchronized with code changes.

## Problem

**Commit Timing:**
- Developers (and AI) commit at arbitrary times, not logical boundaries
- Too-small commits (every file) clutter history
- Too-large commits (days of work) lose granularity
- No guidance on "when is it time to commit?"

**Documentation Drift:**
- Code changes but README/wiki aren't updated
- Issues become stale (fixed but not closed, scope changed but not updated)
- Documentation lags behind implementation

## Proposed Solution: Two-Part System

### Part 1: Smart Commit Timing Detection

**Watch for commit-worthy boundaries:**

```python
class CommitTimingDetector:
    def should_suggest_commit(self) -> tuple[bool, str]:
        """Detect if it's time to commit."""
        
        reasons = []
        
        # 1. Logical completion
        if self.recent_test_run_passed():
            reasons.append("Tests passing (logical checkpoint)")
        
        # 2. Volume threshold
        modified = git_status()
        if len(modified) >= 5:
            reasons.append(f"{len(modified)} files modified")
        
        # 3. Time threshold
        last_commit = git_last_commit_time()
        if (now() - last_commit) > 30_minutes:
            reasons.append("30+ minutes since last commit")
        
        # 4. Task completion
        if self.task_marked_complete():
            reasons.append("Task marked complete")
        
        # 5. Feature boundary
        if self.detected_feature_complete():
            reasons.append("Feature appears complete (impl + tests)")
        
        return len(reasons) > 0, ", ".join(reasons)
```

**Heuristics:**

| Trigger | Description | Confidence |
|---------|-------------|------------|
| **Tests pass** | Test suite just passed | High |
| **N files modified** | 5+ files changed | Medium |
| **Time elapsed** | 30+ minutes since last commit | Low |
| **Task complete** | User marked task as done | High |
| **Feature boundary** | Implementation + tests both present | High |
| **Before large refactor** | About to make breaking changes | Medium |
| **End of session** | Claude session ending | Medium |

**Integration Points:**

#### Hook: PostToolUse (Bash - test command)
```bash
# Detect test pass
if [[ "$TOOL_NAME" == "Bash" ]] && echo "$TOOL_RESPONSE" | grep -q "passed"; then
    # Tests passed - check if time to commit
    SHOULD_COMMIT=$(idlergear watch check-commit-timing)
    if [ "$SHOULD_COMMIT" = "true" ]; then
        cat <<EOF
{
  "additionalContext": "✓ Tests passed. Consider committing:
  - $N files modified
  - Tests passing
  - Good checkpoint
  
Commit now with: git add . && git commit -m '...'"
}
EOF
    fi
fi
```

#### Hook: Stop (Session end)
```bash
# Check uncommitted changes
UNCOMMITTED=$(git status --short | wc -l)
if [ "$UNCOMMITTED" -gt 0 ]; then
    cat <<EOF
{
  "decision": "block",
  "reason": "You have $UNCOMMITTED uncommitted changes. Commit before ending session?"
}
EOF
fi
```

#### Hook: UserPromptSubmit (Detect large refactors)
```bash
if echo "$PROMPT" | grep -qiE "(refactor|rewrite|restructure)"; then
    cat <<EOF
{
  "additionalContext": "⚠️ LARGE REFACTOR DETECTED

Consider committing current work first:
  git add . && git commit -m 'Pre-refactor checkpoint'

This creates a safety point before making large changes."
}
EOF
fi
```

### Part 2: Pre-Commit Documentation Sync Checks

**On `git commit`, automatically verify:**

```python
class PreCommitDocCheck:
    def check_documentation_sync(self, staged_files) -> list[Warning]:
        """Check if docs need updates based on code changes."""
        
        warnings = []
        
        # 1. Code changed but README didn't
        if self.code_files_changed(staged_files) and not self.readme_changed(staged_files):
            if self.readme_might_need_update(staged_files):
                warnings.append(
                    "Code changed but README.md not updated. "
                    "Does the README need updates for: {features_added}?"
                )
        
        # 2. Public API changed but wiki didn't
        if self.public_api_changed(staged_files) and not self.wiki_changed():
            warnings.append(
                "Public API modified. Consider updating wiki documentation."
            )
        
        # 3. Tests added/modified but no issue reference
        if self.tests_changed(staged_files):
            commit_msg = get_commit_message()
            if not self.has_issue_ref(commit_msg):  # No "Fix #42"
                warnings.append(
                    "Tests modified but no issue reference in commit message. "
                    "Related to an issue?"
                )
        
        # 4. Bug fix but issue not closed
        if "fix" in commit_msg.lower():
            issue_ids = extract_issue_refs(commit_msg)
            for issue_id in issue_ids:
                issue = get_issue(issue_id)
                if issue['state'] == 'open':
                    warnings.append(
                        f"Commit says 'fix' but issue #{issue_id} still open. "
                        f"Close it with: idlergear task close {issue_id}"
                    )
        
        # 5. Feature complete but no documentation
        if self.feature_complete(staged_files):
            if not self.has_docs(staged_files):
                warnings.append(
                    "Feature appears complete (impl + tests) but no docs added. "
                    "Add to wiki or README?"
                )
        
        return warnings
```

**Implementation via Git Hook:**

```bash
#!/bin/bash
# .git/hooks/pre-commit (or .idlergear/hooks/pre-commit)

# Get staged files
STAGED=$(git diff --cached --name-only)

# Run IdlerGear doc check
WARNINGS=$(idlergear watch check-docs --staged "$STAGED")

if [ -n "$WARNINGS" ]; then
    echo "⚠️  Documentation Sync Warnings:"
    echo "$WARNINGS"
    echo ""
    echo "Proceed anyway? (y/N)"
    read -r RESPONSE
    
    if [[ ! "$RESPONSE" =~ ^[Yy]$ ]]; then
        echo "Commit aborted. Update docs and try again."
        exit 1
    fi
fi

exit 0
```

## Heuristics for Documentation Needs

### README.md Update Needed When:

| Code Change | README Indicator | Confidence |
|-------------|------------------|------------|
| New CLI command added | `README.md` has "Usage" section | High |
| New feature in main API | `README.md` has "Features" list | High |
| Installation changed (deps) | `README.md` has "Installation" | High |
| Configuration options added | `README.md` has "Configuration" | Medium |

**Detection:**
```python
def readme_might_need_update(staged_files):
    # New CLI command?
    if any(f.startswith('src/cli') for f in staged_files):
        # Does README have CLI docs?
        readme = read_file('README.md')
        if '## Usage' in readme or '## Commands' in readme:
            return True
    
    # New feature?
    if 'CHANGELOG.md' in staged_files:
        # Changelog updated but README not
        return True
    
    return False
```

### Wiki Update Needed When:

| Code Change | Wiki Indicator | Confidence |
|-------------|----------------|------------|
| Public API modified | Wiki has API reference | High |
| Architecture changed | Wiki has architecture docs | High |
| New integration added | Wiki has integration guide | Medium |

### Issue Update Needed When:

| Commit Pattern | Action | Confidence |
|----------------|--------|------------|
| "Fix #42" in message | Close issue #42 | High |
| "Partially addresses #42" | Add comment to #42 | High |
| Tests for feature X added | Find issue about feature X | Medium |

## Configuration

```toml
# .idlergear/config.toml
[watch.commit_timing]
enabled = true

# Triggers for commit suggestion
suggest_on = [
    "tests_pass",
    "files_threshold",
    "time_threshold",
    "task_complete",
    "feature_complete"
]

# Thresholds
files_threshold = 5           # Suggest commit after N files
time_threshold_minutes = 30   # Suggest after N minutes
lines_threshold = 200         # Suggest after N lines changed

[watch.doc_sync]
enabled = true

# Checks to perform
check_readme = true
check_wiki = true
check_issues = true

# Strictness
block_commit_if_warnings = false  # Just warn, don't block
require_issue_ref_in_tests = true
require_docs_for_features = true

# Auto-actions
auto_close_issues = false  # If true, "Fix #42" auto-closes
auto_update_wiki = false   # If true, push docs to wiki
```

## User Experience

### Scenario 1: Good Checkpoint Reached

```
User: (runs tests)
pytest tests/ -v
======================== 15 passed in 3.2s ========================

Claude Code Hook:
✓ Tests passed (15/15)
📝 5 files modified since last commit
⏱️  25 minutes since last commit

This looks like a good commit point. Create commit?

Suggested message: "Add user authentication with JWT"
  git add . && git commit -m "Add user authentication with JWT"
```

### Scenario 2: Pre-Commit Check

```
User: git commit -m "Fix login bug"

IdlerGear Pre-Commit Hook:
⚠️  Documentation Sync Warnings:

  1. src/auth.py modified but README.md not updated
     → README has "Authentication" section that might need updates
  
  2. Commit message says "Fix" but no issue reference
     → Related to an issue? Add "Fix #42" to link it
  
  3. Issue #42 is still open
     → Close with: idlergear task close 42

Proceed anyway? (y/N) _
```

### Scenario 3: End of Session

```
User: (tries to close Claude Code)

Stop Hook:
⚠️ Uncommitted Changes

You have 3 modified files:
  - src/auth.py
  - tests/test_auth.py
  - README.md

Commit before ending session? (y/N) _
```

## Implementation Plan

### Phase 1: Commit Timing Detection
- [ ] Implement `idlergear watch check-commit-timing`
- [ ] Detect: tests pass, file count, time elapsed
- [ ] Add PostToolUse hook for test pass detection
- [ ] Add Stop hook for uncommitted changes warning
- [ ] Add UserPromptSubmit hook for large refactor warning
- [ ] Configuration: thresholds for suggestions

### Phase 2: Pre-Commit Doc Checks
- [ ] Implement `idlergear watch check-docs`
- [ ] Check README sync (code changed, README didn't)
- [ ] Check wiki sync (public API changed)
- [ ] Check issue refs (commit message extraction)
- [ ] Check issue state (fix but still open)
- [ ] Git hook integration (`.git/hooks/pre-commit`)

### Phase 3: Auto-Actions
- [ ] Auto-close issues on "Fix #42" (if enabled)
- [ ] Auto-suggest commit messages based on changes
- [ ] Auto-detect feature boundaries (impl + tests)
- [ ] Auto-push wiki updates (if enabled)

### Phase 4: Smart Analysis
- [ ] Use AI to analyze if docs need updates (Level 3 autonomous)
- [ ] Detect semantic changes (not just file changes)
- [ ] Suggest doc updates with specific sections to modify
- [ ] Learn from user feedback (approve/reject suggestions)

## Examples

### Example 1: Feature Complete Detection

```python
def detected_feature_complete(staged_files):
    """Detect if a feature is complete (impl + tests)."""
    
    # Find implementation files
    impl_files = [f for f in staged_files if f.startswith('src/')]
    
    # Find test files
    test_files = [f for f in staged_files if f.startswith('tests/')]
    
    # Both present?
    if impl_files and test_files:
        # Check if test file corresponds to impl file
        for impl in impl_files:
            impl_name = Path(impl).stem
            for test in test_files:
                if impl_name in test:
                    return True  # Found matching impl + test
    
    return False
```

### Example 2: README Update Detection

```python
def readme_needs_update(staged_files):
    """Check if README might need updates."""
    
    # Code changed?
    code_changed = any(
        f.endswith(('.py', '.js', '.rs', '.go'))
        for f in staged_files
    )
    
    if not code_changed:
        return False
    
    # README also changed?
    readme_changed = 'README.md' in staged_files
    
    if readme_changed:
        return False  # Already updated
    
    # Check if README has sections that might need updates
    readme = read_file('README.md')
    
    # New CLI command added?
    if any('cli' in f for f in staged_files):
        if '## Usage' in readme or '## Commands' in readme:
            return True, "New CLI command added, README has Usage section"
    
    # New dependency added?
    if any('requirements.txt' in f or 'package.json' in f for f in staged_files):
        if '## Installation' in readme:
            return True, "Dependencies changed, README has Installation section"
    
    return False, None
```

### Example 3: Issue Close Detection

```python
def check_issue_closure(commit_message):
    """Check if issues should be closed."""
    
    # Extract issue references
    issue_refs = re.findall(r'#(\d+)', commit_message)
    
    # Check keywords
    fix_keywords = ['fix', 'fixes', 'fixed', 'close', 'closes', 'resolve']
    has_fix_keyword = any(kw in commit_message.lower() for kw in fix_keywords)
    
    warnings = []
    
    for issue_id in issue_refs:
        issue = get_issue(issue_id)
        
        if has_fix_keyword and issue['state'] == 'open':
            warnings.append(
                f"Commit says '{fix_keyword}' but issue #{issue_id} is still open. "
                f"Auto-close with: idlergear task close {issue_id}"
            )
        
        elif not has_fix_keyword and issue['state'] == 'open':
            # Just a reference, add comment
            warnings.append(
                f"Mentioned #{issue_id}. Add progress comment? "
                f"idlergear task update {issue_id} --comment 'Partial work in {commit_hash}'"
            )
    
    return warnings
```

## Benefits

1. ✅ **Better commit hygiene** - Commits at logical boundaries, not arbitrary times
2. ✅ **Up-to-date documentation** - Catches doc drift before it happens
3. ✅ **Issue tracking** - Ensures commits link to issues, issues stay current
4. ✅ **Reduced context loss** - Commits capture complete units of work
5. ✅ **AI guidance** - Claude gets clear signals on when to commit
6. ✅ **Safety net** - Catches forgotten docs before code review

## Related Issues

- #112 - Watch mode (provides file monitoring)
- #116 - Wiki sync (auto-push to GitHub wiki)
- #22 - Autonomous issue management (auto-close issues)
- #21 - Long-running processes (commit before large operations)

## Acceptance Criteria

**Commit Timing:**
- [ ] Detects when tests pass and suggests commit
- [ ] Suggests commit after N files modified (configurable)
- [ ] Warns about uncommitted changes at session end
- [ ] Detects large refactors and suggests pre-commit
- [ ] Hook integration works (PostToolUse, Stop, UserPromptSubmit)

**Doc Sync Checks:**
- [ ] Pre-commit hook detects README needs update
- [ ] Pre-commit hook detects wiki needs update
- [ ] Pre-commit hook detects missing issue references
- [ ] Pre-commit hook detects issues that should be closed
- [ ] Warnings shown but commit not blocked (configurable)

**User Experience:**
- [ ] Clear, actionable warnings
- [ ] Suggested commit messages based on changes
- [ ] Easy to accept/reject suggestions
- [ ] Configuration for strictness levels
