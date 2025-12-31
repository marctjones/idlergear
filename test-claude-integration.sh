#!/bin/bash
# Run IdlerGear + Claude Code integration tests
#
# These tests verify that Claude Code properly reads CLAUDE.md and follows
# IdlerGear instructions. Each test spawns a fresh Claude instance.
#
# Usage:
#   ./test-claude-integration.sh          # Run all Claude integration tests
#   ./test-claude-integration.sh -v       # Verbose output
#   ./test-claude-integration.sh -k name  # Run specific test by name

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Activate virtual environment
source venv/bin/activate

# Run the Claude integration tests
# -m claude_integration: only tests marked with this marker
# Tests are automatically skipped if claude CLI is not available
python -m pytest tests/integration/test_claude_code_integration.py \
    -v \
    --tb=short \
    "$@"
