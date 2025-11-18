#!/bin/bash
set -e

# --- IdlerGear Branch Cleanup Script ---
# This script deletes all branches except main, both locally and remotely.
# Use this after merging feature branches to keep your repository clean.

echo "=== IdlerGear Branch Cleanup ==="
echo ""

# 1. Fetch latest from remote
echo "Fetching latest from remote..."
git fetch --all --prune

# 2. Switch to main branch
echo "Switching to main branch..."
git checkout main

# 3. Pull latest main
echo "Pulling latest main..."
git pull origin main

# 4. Delete local branches (except main)
echo ""
echo "Deleting local branches (except main)..."
LOCAL_BRANCHES=$(git branch | grep -v "^\* main$" | grep -v "^  main$" || true)
if [ -n "$LOCAL_BRANCHES" ]; then
    echo "$LOCAL_BRANCHES" | xargs -r git branch -D
    echo "Deleted local branches"
else
    echo "No local branches to delete"
fi

# 5. Delete remote branches (except main)
echo ""
echo "Deleting remote branches (except main)..."
REMOTE_BRANCHES=$(git branch -r | grep -v "origin/main" | grep -v "origin/HEAD" | sed 's/origin\///' || true)
if [ -n "$REMOTE_BRANCHES" ]; then
    for branch in $REMOTE_BRANCHES; do
        echo "  Deleting origin/$branch..."
        git push origin --delete "$branch" 2>/dev/null || echo "    Warning: Could not delete $branch"
    done
    echo "Deleted remote branches"
else
    echo "No remote branches to delete"
fi

# 6. Clean up stale tracking references
echo ""
echo "Cleaning up stale references..."
git remote prune origin

# 7. Summary
echo ""
echo "=== Cleanup Complete ==="
echo ""
echo "Remaining branches:"
git branch -a
echo ""
echo "Your repository is now clean with only the main branch."
