#!/bin/bash
# IdlerGear post-commit hook
# Auto-updates knowledge graph after each commit
#
# Skip graph update: SKIP_GRAPH_UPDATE=1 git commit -m "..."
# Or use: git commit --no-verify -m "..."
#
# Configuration:
#   graph.auto_update: true/false - Enable automatic graph updates

set -e

# Check for skip flag
if [ -n "$SKIP_GRAPH_UPDATE" ]; then
    exit 0
fi

# Check if idlergear is available
if ! command -v idlergear &> /dev/null; then
    exit 0
fi

# Check if graph auto-update is enabled
graph_auto_update=$(idlergear config get graph.auto_update 2>/dev/null || echo "false")
if [ "$graph_auto_update" != "true" ]; then
    exit 0
fi

echo "[IdlerGear] Updating knowledge graph..."

# Run incremental populate in background to avoid slowing down commits
# Suppress output to keep commit clean
(
    python3 -c "
from idlergear.graph import populate_all
import sys
try:
    # Incremental mode - only updates changed data
    populate_all(max_commits=100, incremental=True, verbose=False)
except Exception as e:
    # Don't block commits on graph update failures
    # Log error but continue
    print(f'Graph update failed: {e}', file=sys.stderr)
" &> /dev/null
) &

# Notify daemon if running (non-blocking)
if command -v idlergear &> /dev/null; then
    idlergear daemon send "Knowledge graph updated after commit" &> /dev/null || true
fi

exit 0
