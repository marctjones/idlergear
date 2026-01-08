#!/bin/bash
# IdlerGear auto-version pre-commit hook
# Automatically increments patch version on each commit
#
# Skip auto-bump by setting environment variable:
#   SKIP_VERSION=1 git commit -m "docs: update readme"
#
# Manual major/minor bumps are detected and respected.

set -e

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
