#!/bin/bash
# IdlerGear pre-commit hook
# Features:
#   1. Auto-version: Increments patch version on each commit
#   2. Watch check: Creates tasks from TODO/FIXME/HACK in staged changes
#   3. Test failure check: Blocks commit if tests failing (when enabled)
#   4. Test staleness warning: Warns if committing code without recent tests (when enabled)
#
# Skip auto-bump: SKIP_VERSION=1 git commit -m "..."
# Skip watch:     SKIP_WATCH=1 git commit -m "..."
# Skip all:       git commit --no-verify -m "..."
#
# Manual major/minor bumps are detected and respected.
#
# Configuration:
#   test.block_on_failure: true/false - Block commits when tests are failing
#   test.warn_stale_on_commit: true/false - Warn when tests are stale
#   test.stale_threshold_seconds: number - Seconds before tests considered stale (default: 3600)
#   watch.enabled: true/false - Enable watch check for TODO/FIXME/HACK

set -e

# --- IdlerGear Watch Check ---
# Only runs if watch.enabled is true in config
if [ -z "$SKIP_WATCH" ] && command -v idlergear &> /dev/null; then
    # Check if watch is enabled
    watch_enabled=$(idlergear config get watch.enabled 2>/dev/null || echo "false")
    if [ "$watch_enabled" = "true" ]; then
        # Run watch check with --act to auto-create tasks
        # Use --staged to only check staged changes (not implemented yet, so check all)
        echo "[IdlerGear] Running watch check..."
        idlergear watch check --act 2>/dev/null || true
    fi
fi

# --- IdlerGear Test Failure Check ---
# Block commits if tests are failing (when enabled)
if command -v idlergear &> /dev/null; then
    block_on_failure=$(idlergear config get test.block_on_failure 2>/dev/null || echo "false")

    if [ "$block_on_failure" = "true" ] || [ "$block_on_failure" = "True" ]; then
        # Get test status
        if command -v jq &> /dev/null; then
            result=$(idlergear test status --json 2>/dev/null || echo "{}")
            failed=$(echo "$result" | jq -r '.failed // 0' 2>/dev/null || echo "0")

            if [ "$failed" -gt 0 ]; then
                echo ""
                echo "❌ Cannot commit: $failed test(s) failing"
                echo "   Run 'idlergear test run' to see failures"
                echo "   Fix tests or use 'git commit --no-verify' to bypass"
                exit 1
            fi
        else
            # jq not available, warn but don't block
            echo "⚠️  Warning: jq not found, skipping test failure check"
        fi
    fi
fi

# --- IdlerGear Test Staleness Warning ---
# Warn if committing source files without recent test runs (when enabled)
if command -v idlergear &> /dev/null && command -v jq &> /dev/null; then
    warn_stale=$(idlergear config get test.warn_stale_on_commit 2>/dev/null | grep -oE '(true|True|false|False)$' || echo "false")

    if [ "$warn_stale" = "true" ] || [ "$warn_stale" = "True" ]; then
        # Check if source files are being committed (excluding test files)
        source_files=$(git diff --cached --name-only | grep -E '\.(py|rs|go|js|ts|jsx|tsx|java|rb|php)$' | grep -vE '(test|spec)' || true)

        if [ -n "$source_files" ]; then
            # Get test staleness
            staleness=$(idlergear test staleness --json 2>/dev/null || echo "{}")
            seconds_ago=$(echo "$staleness" | jq -r '.seconds_ago // 999999' 2>/dev/null || echo "999999")

            # Get threshold from config (default 1 hour = 3600 seconds)
            threshold=$(idlergear config get test.stale_threshold_seconds 2>/dev/null | grep -oE '[0-9]+$' || echo "3600")

            # Validate threshold is a number
            if ! [[ "$threshold" =~ ^[0-9]+$ ]]; then
                threshold=3600
            fi

            # Warn if tests are older than threshold
            if [ "$seconds_ago" != "null" ] && [ "$seconds_ago" -gt "$threshold" ]; then
                echo ""
                if [ "$seconds_ago" -lt 3600 ]; then
                    mins=$((seconds_ago / 60))
                    echo "⚠️  Warning: Tests last run ${mins} minute(s) ago"
                elif [ "$seconds_ago" -lt 86400 ]; then
                    hours=$((seconds_ago / 3600))
                    echo "⚠️  Warning: Tests last run ${hours} hour(s) ago"
                else
                    days=$((seconds_ago / 86400))
                    echo "⚠️  Warning: Tests last run ${days} day(s) ago"
                fi
                echo "   Consider running: idlergear test run"
                echo "   Or disable: idlergear config set test.warn_stale_on_commit false"
                echo ""
            fi
        fi
    fi
fi

PYPROJECT="pyproject.toml"

# Check if pyproject.toml exists
if [ ! -f "$PYPROJECT" ]; then
    exit 0
fi

# Check for SKIP_VERSION environment variable
if [ -n "$SKIP_VERSION" ]; then
    exit 0
fi

# Get current version from working tree
current_version=$(grep '^version = ' "$PYPROJECT" | sed 's/version = "\(.*\)"/\1/')

if [ -z "$current_version" ]; then
    # No version found, skip
    exit 0
fi

# Check if pyproject.toml is staged with changes
if git diff --cached --name-only | grep -q "pyproject.toml"; then
    # Get the staged version
    staged_version=$(git show :pyproject.toml 2>/dev/null | grep '^version = ' | sed 's/version = "\(.*\)"/\1/' || echo "")

    # Get the HEAD version (what's committed)
    head_version=$(git show HEAD:pyproject.toml 2>/dev/null | grep '^version = ' | sed 's/version = "\(.*\)"/\1/' || echo "")

    if [ -n "$staged_version" ] && [ "$staged_version" != "$head_version" ]; then
        # Version was manually changed in this commit, don't auto-bump
        exit 0
    fi
fi

# Parse version (major.minor.patch)
IFS='.' read -r major minor patch <<< "$current_version"

# Validate we have numbers
if ! [[ "$major" =~ ^[0-9]+$ ]] || ! [[ "$minor" =~ ^[0-9]+$ ]] || ! [[ "$patch" =~ ^[0-9]+$ ]]; then
    echo "Warning: Could not parse version '$current_version', skipping auto-bump"
    exit 0
fi

# Increment patch
new_patch=$((patch + 1))
new_version="$major.$minor.$new_patch"

# Update pyproject.toml
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS sed requires empty string for -i
    sed -i '' "s/^version = \"$current_version\"/version = \"$new_version\"/" "$PYPROJECT"
else
    # Linux sed
    sed -i "s/^version = \"$current_version\"/version = \"$new_version\"/" "$PYPROJECT"
fi

# Stage the change
git add "$PYPROJECT"

echo "Auto-bumped version: $current_version -> $new_version"
