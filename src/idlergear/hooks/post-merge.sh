#!/bin/bash
# IdlerGear post-merge hook
# Auto-updates knowledge graph after git merge/pull
#
# Skip graph update: SKIP_GRAPH_UPDATE=1 git merge/pull ...
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

echo "[IdlerGear] Updating knowledge graph after merge..."

# Run incremental populate in background
# Merges may bring in many new commits, so this is more important
(
    python3 -c "
from idlergear.graph import populate_all
import sys
try:
    # Incremental mode - processes new commits from merge
    populate_all(max_commits=200, incremental=True, verbose=False)
except Exception as e:
    # Don't block merges on graph update failures
    print(f'Graph update failed: {e}', file=sys.stderr)
" &> /dev/null
) &

# Notify daemon if running (non-blocking)
if command -v idlergear &> /dev/null; then
    idlergear daemon send "Knowledge graph updated after merge" &> /dev/null || true
fi

exit 0
